"""Backtest exploratorio: Beta-Insider (compras netas de insiders + filtro SMA200).

Este script es investigación paralela, NO parte de la metodología oficial
(Sigma-6 / Delta-12). No lee ni escribe nada bajo `data/`, `reports/` ni
`strategy_state.json`; todos sus artefactos quedan en `research/insider_backtest/`.

Metodología de referencia: propuesta "Beta-Insider" (borrador 0.1) compartida
con el usuario. Resumen de reglas:

- Universo: acciones de EE.UU. en `config/universe_us_insider.csv`.
- Señal: compra neta de insiders (Form 4, transacciones de mercado abierto,
  código P=compra / S=venta) en los últimos 90 días corridos.
- Filtro técnico: precio ajustado > SMA200.
- Revisión mensual (fin de mes), ejecución en la sesión siguiente.
- Selección: hasta 8 acciones, ordenadas por señal descendente.
- Tamaño: pro-rata con tope 15% por posición (misma función que Delta-12).
- Costo: 0,1% por lado (comisión Trii para acciones de EE.UU., confirmada
  por el usuario), aplicado con la misma fórmula de turnover que ya usa
  el proyecto para Delta-12.

Fuente de datos:
- Precios: Yahoo Finance vía yfinance (igual que el resto del proyecto).
- Transacciones de insiders: "SEC Insider Transactions Data Sets"
  (https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets),
  archivos ZIP trimestrales, gratuitos, sin API key. La lista de URLs de
  descarga se descubre en tiempo de ejecución (no se hardcodea un patrón de
  URL) porque la ruta de esos archivos ha cambiado antes.
- Mapeo ticker -> CIK: `https://www.sec.gov/files/company_tickers.json`
  (oficial, gratuito).

Limitación conocida y documentada: el dataset trimestral tiene rezago (se
publica después del cierre de cada trimestre), así que este backtest mide
el poder predictivo de la señal asumiendo que se pudo actuar sobre ella
con ese rezago -- no reproduce una operación en tiempo real. Ver el
apartado 2 de la propuesta de metodología para la alternativa de baja
latencia (consulta por filing individual), que queda fuera de este script.

v0.2 (tras analizar la primera corrida): la señal absoluta "neto > 0" casi
nunca se activó en mega-caps (0,72 posiciones promedio, 65/123 meses en
caja) y los datos crudos de la SEC traían errores groseros (precios de
millones de USD por acción, ejercicios de warrants de 10% owners marcados
como compras, filas duplicadas). Esta versión agrega:

- Limpieza de transacciones (`clean_transactions`): dedupe, consistencia
  P<->A / S<->D, exclusión de 10% owners, sanidad de precio contra el cierre
  del día y tope de valor por transacción.
- Variante A "relativa": ranking del universo por sentimiento insider
  (compras vs. ventas en USD, ventana de 180 días), siempre invertida en el
  top-8 con filtro SMA200.
- Variante B "veto": réplica de la lógica Delta-12 (momentum 12-1, SMA200,
  RSI14<=65) sobre el universo US, excluyendo tickers con venta neta masiva
  de insiders; se reporta junto a su control sin veto para aislar el efecto.
- Se mantiene la v0.1 (ahora sobre datos limpios) y el benchmark buy & hold.
"""
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "results"
SEC_CACHE = Path(__file__).resolve().parent / ".sec_cache"
UNIVERSE_PATH = ROOT / "config" / "universe_us_insider.csv"

SEC_INDEX_URL = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_HEADERS = {"User-Agent": "AlphaData research contact@alphadata.local"}

START_QUARTER = "2016q1"  # ajustable; correr de nuevo tras editar re-dispara el workflow
COST_RATE = 0.001  # 0,1% por lado (Trii, acciones EE.UU.)
SIGNAL_WINDOW_DAYS = 90  # v0.1 (señal absoluta)
SENTIMENT_WINDOW_DAYS = 180  # v0.2 variante A/B (la actividad de compra es escasa en mega-caps)
MIN_HISTORY_SESSIONS = 252
MAX_POSITIONS = 8
POSITION_CAP = 0.15

# Limpieza v0.2
PRICE_SANITY_RATIO_RAW = 2.0  # precio SEC / cierre SIN ajustar por splits (close_raw) debe estar en [1/2, 2]
PRICE_SANITY_RATIO_ADJ = 60.0  # fallback si no hay close_raw: contra cierre ajustado, tolera splits acumulados (NVDA 40:1)
MAX_TXN_VALUE_USD = 5e9  # ninguna operación de mercado abierto de un ejecutivo supera esto; sí los errores y ejercicios de warrants
VETO_NET_USD = -100e6  # variante B: se veta un ticker si la venta neta de insiders en la ventana supera 100 M USD y no hubo compras


# --------------------------------------------------------------------------
# Descubrimiento y descarga de datos SEC (funciones puras + I/O separado)
# --------------------------------------------------------------------------

def _http_get(url: str, attempts: int = 4, timeout: int = 60) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers=SEC_HEADERS)
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001 - queremos reintentar cualquier falla de red
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"No fue posible descargar {url} tras {attempts} intentos") from last_error


def discover_quarterly_zip_urls(html_text: str, start_quarter: str, base_url: str = "https://www.sec.gov") -> dict[str, str]:
    """Extrae {trimestre: url_absoluta} de los links *_form345.zip en la página índice.

    No asume una ruta fija (`/structureddata/` vs otras) porque la SEC ha
    reorganizado esas rutas antes; en cambio busca cualquier href que matchee
    el patrón del nombre de archivo.
    """
    found = re.findall(r'href="([^"]+?(\d{4}q[1-4])_form345\.zip)"', html_text, flags=re.IGNORECASE)
    urls: dict[str, str] = {}
    for href, quarter in found:
        url = href if href.startswith("http") else base_url + href
        urls[quarter.lower()] = url
    if not urls:
        raise RuntimeError(
            "No se encontraron links *_form345.zip en la página índice de la SEC; "
            "puede que la estructura de la página haya cambiado. Revisar "
            f"{SEC_INDEX_URL} manualmente."
        )
    return {q: u for q, u in sorted(urls.items()) if q >= start_quarter}


def resolve_cik_map(company_tickers: dict, tickers: list[str]) -> dict[str, str]:
    """Mapea ticker -> CIK (como string, sin ceros a la izquierda) usando el
    archivo oficial company_tickers.json de la SEC."""
    wanted = {t.upper() for t in tickers}
    result: dict[str, str] = {}
    for entry in company_tickers.values():
        ticker = str(entry.get("ticker", "")).upper()
        if ticker in wanted:
            result[ticker] = str(entry["cik_str"])
    missing = wanted - set(result)
    if missing:
        raise RuntimeError(
            "No se pudo resolver el CIK de la SEC para estos tickers: "
            + ", ".join(sorted(missing))
            + ". Puede que el ticker esté mal escrito o que la empresa no reporte ante la SEC."
        )
    return result


TRANSACTION_COLUMNS = ["accession", "cik", "trans_date", "trans_code", "acquired_disposed", "shares", "price_per_share", "value", "ten_pct_owner"]
_REQUIRED_SUBMISSION_COLS = {"ACCESSION_NUMBER", "ISSUERCIK", "PERIOD_OF_REPORT"}
_REQUIRED_TRANS_COLS = {
    "ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES",
    "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD",
}


def _read_tsv_from_zip(archive: zipfile.ZipFile, name_candidates: list[str]) -> pd.DataFrame:
    names = {n.upper(): n for n in archive.namelist()}
    for candidate in name_candidates:
        if candidate.upper() in names:
            with archive.open(names[candidate.upper()]) as handle:
                return pd.read_csv(handle, sep="\t", dtype=str, low_memory=False, on_bad_lines="skip")
    raise RuntimeError(
        f"No se encontró ninguno de {name_candidates} dentro del ZIP. "
        f"Archivos disponibles: {archive.namelist()}. "
        "Revisar el schema en https://www.sec.gov/files/insider_transactions_readme.pdf "
        "porque puede haber cambiado el nombre de las tablas."
    )


def _normalize_cik(value: object) -> str:
    """Normaliza un CIK a su forma entera sin ceros a la izquierda.

    Los datasets de la SEC no son consistentes: algunos archivos traen el
    CIK con ceros a la izquierda (p. ej. "0000320193") y otros sin ellos
    ("320193"). Sin esta normalización, un `isin()` directo entre ambas
    formas nunca hace match y el filtro queda vacío en silencio.
    """
    try:
        return str(int(str(value).strip()))
    except (TypeError, ValueError):
        return ""


def parse_quarter_zip(zip_bytes: bytes, cik_set: set[str]) -> pd.DataFrame:
    """Extrae transacciones no-derivadas de mercado abierto (P/S) para el
    conjunto de CIK dado, desde un ZIP trimestral de la SEC.

    Devuelve columnas: cik, trans_date, trans_code, acquired_disposed, shares,
    price_per_share, value.
    """
    cik_set = {_normalize_cik(c) for c in cik_set}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        submissions = _read_tsv_from_zip(archive, ["SUBMISSION.tsv", "SUBMISSION"])
        missing_sub = _REQUIRED_SUBMISSION_COLS.difference(submissions.columns)
        if missing_sub:
            raise RuntimeError(f"SUBMISSION.tsv no tiene las columnas esperadas: {sorted(missing_sub)}")
        submissions = submissions.copy()
        submissions["ISSUERCIK"] = submissions["ISSUERCIK"].map(_normalize_cik)
        submissions = submissions[submissions["ISSUERCIK"].isin(cik_set)]
        if submissions.empty:
            return pd.DataFrame(columns=TRANSACTION_COLUMNS)

        trans = _read_tsv_from_zip(archive, ["NONDERIV_TRANS.tsv", "NONDERIV_TRANS"])
        missing_trans = _REQUIRED_TRANS_COLS.difference(trans.columns)
        if missing_trans:
            raise RuntimeError(f"NONDERIV_TRANS.tsv no tiene las columnas esperadas: {sorted(missing_trans)}")

        # v0.2: marcar filings presentados por 10% owners (Berkshire, fideicomisos
        # familiares, etc.). Se lee de forma defensiva: si la tabla o la columna
        # no existen en este trimestre, la bandera queda en False y se sigue.
        ten_pct = _ten_percent_owner_flags(archive)

    merged = trans.merge(submissions[["ACCESSION_NUMBER", "ISSUERCIK"]], on="ACCESSION_NUMBER", how="inner")
    merged = merged[merged["TRANS_CODE"].isin(["P", "S"])].copy()
    merged["shares"] = pd.to_numeric(merged["TRANS_SHARES"], errors="coerce")
    merged["price_per_share"] = pd.to_numeric(merged["TRANS_PRICEPERSHARE"], errors="coerce")
    merged["trans_date"] = pd.to_datetime(merged["TRANS_DATE"], errors="coerce")
    merged = merged.dropna(subset=["shares", "price_per_share", "trans_date"])
    merged["value"] = merged["shares"] * merged["price_per_share"]
    sign = np.where(merged["TRANS_ACQUIRED_DISP_CD"].eq("A"), 1.0, np.where(merged["TRANS_ACQUIRED_DISP_CD"].eq("D"), -1.0, np.nan))
    merged["value"] = merged["value"] * sign
    merged = merged.dropna(subset=["value"])
    merged["ten_pct_owner"] = merged["ACCESSION_NUMBER"].map(lambda a: bool(ten_pct.get(a, False)))
    return merged.rename(columns={"ACCESSION_NUMBER": "accession", "ISSUERCIK": "cik", "TRANS_CODE": "trans_code", "TRANS_ACQUIRED_DISP_CD": "acquired_disposed"})[
        TRANSACTION_COLUMNS
    ]



def _ten_percent_owner_flags(archive: zipfile.ZipFile) -> pd.Series:
    """Devuelve Series accession -> True si algún reporting owner del filing
    está marcado como 10% owner. Vacía si la tabla/columna no está disponible."""
    try:
        owners = _read_tsv_from_zip(archive, ["REPORTINGOWNER.tsv", "REPORTINGOWNER"])
    except RuntimeError:
        return pd.Series(dtype=bool)
    rel_cols = [c for c in owners.columns if "RELATIONSHIP" in c.upper()]
    if "ACCESSION_NUMBER" not in owners.columns or not rel_cols:
        return pd.Series(dtype=bool)
    flag = owners[rel_cols[0]].astype(str).str.contains("10%", regex=False)
    return flag.groupby(owners["ACCESSION_NUMBER"]).any()


# --------------------------------------------------------------------------
# Señal, selección de cartera y backtest (funciones puras, testeables)
# --------------------------------------------------------------------------

def insider_signal(transactions: pd.DataFrame, cik_to_ticker: dict[str, str], as_of: pd.Timestamp, window_days: int = SIGNAL_WINDOW_DAYS) -> pd.Series:
    """Compra neta de insiders (USD) por ticker, en los `window_days` previos a `as_of`.

    Solo usa transacciones con trans_date <= as_of, para no incurrir en look-ahead.
    """
    if transactions.empty:
        return pd.Series(dtype=float)
    cutoff = as_of - pd.Timedelta(days=window_days)
    window = transactions[(transactions.trans_date <= as_of) & (transactions.trans_date > cutoff)]
    if window.empty:
        return pd.Series(dtype=float)
    by_cik = window.groupby("cik")["value"].sum()
    return by_cik.rename(index=cik_to_ticker)


def capped_pro_rata(scores: pd.Series, cap: float) -> pd.Series:
    """Misma lógica que src/strategy_engine.py::capped_pro_rata (duplicada aquí
    a propósito para que este script de investigación no dependa en tiempo de
    ejecución de detalles internos de la metodología oficial; ambas deben
    mantenerse en sync si se cambia la fórmula)."""
    scores = pd.to_numeric(scores, errors="coerce").fillna(0).clip(lower=0)
    result = pd.Series(0.0, index=scores.index)
    active = scores[scores > 0].copy()
    remaining = 1.0
    while len(active) and remaining > 1e-12:
        proposal = remaining * active / active.sum()
        hit = proposal >= cap - 1e-12
        if not hit.any():
            result.loc[proposal.index] += proposal
            break
        result.loc[proposal[hit].index] = cap
        remaining = 1 - result.sum()
        active = active[~hit]
    return result


def select_portfolio(scores: pd.Series, trend_ok: pd.Series, max_positions: int = MAX_POSITIONS, cap: float = POSITION_CAP) -> pd.Series:
    """Selecciona hasta `max_positions` tickers con señal positiva y tendencia
    positiva, y devuelve pesos objetivo (capped pro-rata)."""
    eligible = scores[(scores > 0) & scores.index.isin(trend_ok[trend_ok].index)]
    top = eligible.sort_values(ascending=False).head(max_positions)
    if top.empty:
        return pd.Series(dtype=float)
    return capped_pro_rata(pd.Series(1.0, index=top.index), cap)


# --------------------------------------------------------------------------
# v0.2: limpieza de datos
# --------------------------------------------------------------------------

def clean_transactions(transactions: pd.DataFrame, prices: pd.DataFrame, cik_to_ticker: dict[str, str]) -> tuple[pd.DataFrame, dict[str, object]]:
    """Limpia las transacciones crudas de la SEC. Devuelve (limpias, reporte).

    Reglas (en este orden; el reporte cuenta cuántas filas descarta cada una):
    1. duplicados exactos (mismo filing repetido por cada reporting owner);
    2. inconsistencia de códigos: P debe ser A (adquisición) y S debe ser D;
    3. filings de 10% owners (no son ejecutivos/directores; ej. ejercicio de
       warrants de Berkshire en BAC 2016);
    4. sanidad de precio: precio SEC / cierre del día (o el anterior). Si
       `prices` trae `close_raw` (cierre sin ajustar por splits, reconstruido
       con los splits de Yahoo) se exige ratio en [1/2, 2]; si no, se usa el
       cierre ajustado con tolerancia amplia (PRICE_SANITY_RATIO_ADJ) para no
       descartar operaciones anteriores a splits grandes. Precio <= 0 se descarta;
    5. tope de valor absoluto por transacción (MAX_TXN_VALUE_USD).

    Las columnas opcionales (accession, ten_pct_owner) se toleran ausentes
    para poder correr la limpieza sobre resultados de la v0.1.
    """
    report: dict[str, object] = {"input": int(len(transactions))}
    if transactions.empty:
        report.update({"dup": 0, "inconsistent": 0, "ten_pct_owner": 0, "price_sanity": 0, "value_cap": 0, "output": 0})
        return transactions.copy(), report
    t = transactions.copy()
    t["trans_date"] = pd.to_datetime(t["trans_date"])
    t["cik"] = t["cik"].map(_normalize_cik)

    key_cols = [c for c in ["accession", "cik", "trans_date", "trans_code", "acquired_disposed", "shares", "price_per_share"] if c in t.columns]
    before = len(t)
    t = t.drop_duplicates(subset=key_cols)
    report["dup"] = before - len(t)

    before = len(t)
    consistent = ((t["trans_code"] == "P") & (t["acquired_disposed"] == "A")) | ((t["trans_code"] == "S") & (t["acquired_disposed"] == "D"))
    t = t[consistent]
    report["inconsistent"] = before - len(t)

    before = len(t)
    if "ten_pct_owner" in t.columns:
        t = t[~t["ten_pct_owner"].astype(bool)]
    report["ten_pct_owner"] = before - len(t)

    before = len(t)
    t["ticker"] = t["cik"].map(cik_to_ticker)
    has_raw = "close_raw" in prices.columns and prices["close_raw"].notna().any()
    ref_col, bound = ("close_raw", PRICE_SANITY_RATIO_RAW) if has_raw else ("adjusted_close", PRICE_SANITY_RATIO_ADJ)
    px = prices[["date", "ticker", ref_col]].copy()
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values("date")
    t = t.sort_values("trans_date")
    t = pd.merge_asof(t, px.rename(columns={"date": "trans_date", ref_col: "close_ref"}), on="trans_date", by="ticker", direction="backward")
    ratio = t["price_per_share"] / t["close_ref"]
    sane = (t["price_per_share"] > 0) & ratio.between(1 / bound, bound)
    report["price_sanity_reference"] = ref_col
    sane = sane | t["close_ref"].isna()  # sin precio de referencia no se puede juzgar; se conserva
    t = t[sane]
    report["price_sanity"] = before - len(t)

    before = len(t)
    t = t[t["value"].abs() <= MAX_TXN_VALUE_USD]
    report["value_cap"] = before - len(t)

    report["output"] = int(len(t))
    return t.drop(columns=["close_ref"]).reset_index(drop=True), report


# --------------------------------------------------------------------------
# v0.2: sentimiento insider relativo y réplica Delta-12 con veto
# --------------------------------------------------------------------------

def insider_activity(transactions: pd.DataFrame, cik_to_ticker: dict[str, str], as_of: pd.Timestamp, window_days: int = SENTIMENT_WINDOW_DAYS) -> pd.DataFrame:
    """Por ticker, en los `window_days` previos a `as_of` (sin look-ahead):
    buy_usd, sell_usd (ambos >= 0), n_buys, n_sells, net_usd y `score` en
    [-1, 1] = (buy - sell) / (buy + sell). Sin actividad => score 0."""
    columns = ["buy_usd", "sell_usd", "n_buys", "n_sells", "net_usd", "score"]
    if transactions.empty:
        return pd.DataFrame(columns=columns)
    cutoff = as_of - pd.Timedelta(days=window_days)
    w = transactions[(transactions.trans_date <= as_of) & (transactions.trans_date > cutoff)].copy()
    if w.empty:
        return pd.DataFrame(columns=columns)
    w["ticker"] = w["cik"].map(cik_to_ticker)
    w = w.dropna(subset=["ticker"])
    grouped = w.groupby("ticker")
    out = pd.DataFrame({
        "buy_usd": grouped["value"].apply(lambda v: v[v > 0].sum()),
        "sell_usd": grouped["value"].apply(lambda v: -v[v < 0].sum()),
        "n_buys": grouped["value"].apply(lambda v: int((v > 0).sum())),
        "n_sells": grouped["value"].apply(lambda v: int((v < 0).sum())),
    })
    out["net_usd"] = out["buy_usd"] - out["sell_usd"]
    gross = out["buy_usd"] + out["sell_usd"]
    out["score"] = np.where(gross > 0, out["net_usd"] / gross.replace(0, np.nan), 0.0)
    return out[columns]


def select_relative(activity: pd.DataFrame, trend_ok: pd.Series, max_positions: int = MAX_POSITIONS, cap: float = POSITION_CAP) -> pd.Series:
    """Variante A: entre los tickers con tendencia positiva, rankea por score
    de sentimiento insider (sin actividad = 0, neutral) y se queda con los
    `max_positions` mejores. Siempre invertida mientras haya elegibles.
    Desempate: net_usd, luego ticker (determinista)."""
    eligible = trend_ok[trend_ok].index
    if len(eligible) == 0:
        return pd.Series(dtype=float)
    frame = pd.DataFrame({"ticker": list(eligible)})
    frame["score"] = activity["score"].reindex(eligible).fillna(0.0).to_numpy() if not activity.empty else 0.0
    frame["net_usd"] = activity["net_usd"].reindex(eligible).fillna(0.0).to_numpy() if not activity.empty else 0.0
    top = frame.sort_values(["score", "net_usd", "ticker"], ascending=[False, False, True]).head(max_positions)
    return capped_pro_rata(pd.Series(1.0, index=top["ticker"].tolist()), cap)


def delta12_like_audit(panel: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Réplica de las reglas técnicas de Delta-12 (src/strategy_engine.py::delta12)
    sobre un panel de precios ajustados (index=date, columns=ticker), duplicada
    a propósito para no acoplar la investigación al código oficial.

    Omite el filtro de liquidez (percentil de turnover) porque este script no
    descarga volumen y las 30 mega-caps del universo no tienen ese problema.
    """
    close = panel.loc[:as_of]
    if len(close) < 252:
        return pd.DataFrame(columns=["momentum_12_1", "above_sma200", "rsi14", "history_ok", "eligible"])
    momentum = close.shift(21).iloc[-1] / close.shift(252).iloc[-1] - 1
    sma = close.rolling(200, min_periods=200).mean().iloc[-1]
    last = close.iloc[-1]
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi14 = (100 - (100 / (1 + rs))).fillna(100).iloc[-1]
    audit = pd.DataFrame({
        "momentum_12_1": momentum,
        "above_sma200": last > sma,
        "rsi14": rsi14,
        "history_ok": close.notna().sum() >= MIN_HISTORY_SESSIONS,
    })
    audit["eligible"] = (audit.momentum_12_1 > 0) & audit.above_sma200 & (audit.rsi14 <= 65) & audit.history_ok
    return audit


def insider_veto(activity: pd.DataFrame, net_usd_threshold: float = VETO_NET_USD) -> pd.Index:
    """Variante B: tickers vetados = venta neta de insiders <= umbral y cero compras."""
    if activity.empty:
        return pd.Index([])
    vetoed = activity[(activity["net_usd"] <= net_usd_threshold) & (activity["n_buys"] == 0)]
    return vetoed.index


def select_delta12_like(audit: pd.DataFrame, vetoed: pd.Index | None = None, max_positions: int = MAX_POSITIONS, cap: float = POSITION_CAP) -> pd.Series:
    """Top `max_positions` por momentum 12-1 entre elegibles (menos los vetados),
    igual-ponderado con tope `cap` (misma regla que Delta-12)."""
    if audit.empty:
        return pd.Series(dtype=float)
    eligible = audit[audit["eligible"]]
    if vetoed is not None and len(vetoed):
        eligible = eligible[~eligible.index.isin(vetoed)]
    top = eligible.nlargest(max_positions, "momentum_12_1")
    if top.empty:
        return pd.Series(dtype=float)
    return capped_pro_rata(pd.Series(1.0, index=top.index), cap)


# --------------------------------------------------------------------------
# Motor de backtest (genérico: recibe una función de selección por revisión)
# --------------------------------------------------------------------------

def run_backtest(prices: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, selector, cost_rate: float = COST_RATE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backtest mensual histórico genérico. Devuelve (nav_diaria, señales_por_revisión).

    `selector(panel, sma200, review) -> (weights: Series, n_eligible: int)` decide
    la cartera objetivo en cada revisión de fin de mes; la ejecución ocurre en la
    sesión siguiente y el costo se aplica sobre el turnover (misma fórmula que
    el proyecto usa para Delta-12).
    """
    panel = prices.pivot(index="date", columns="ticker", values="adjusted_close").sort_index()
    panel = panel.loc[panel.index <= end]
    sma200 = panel.rolling(200, min_periods=200).mean()
    sessions = panel.index[panel.index >= start]
    if len(sessions) == 0:
        raise RuntimeError("No hay sesiones de precio en el rango pedido; revisar la descarga de precios.")

    weights: dict[str, float] = {}
    nav = 100.0
    rows = []
    signal_rows = []
    previous_date = None
    current_month = None
    for session in sessions:
        if previous_date is None:
            rows.append({"date": session, "nav": nav})
            previous_date = session
            current_month = session.to_period("M")
            continue
        day_return = 0.0
        for ticker, weight in weights.items():
            if ticker in panel and pd.notna(panel.at[previous_date, ticker]) and pd.notna(panel.at[session, ticker]) and panel.at[previous_date, ticker] > 0:
                day_return += weight * (panel.at[session, ticker] / panel.at[previous_date, ticker] - 1)
        nav *= 1 + day_return
        month = session.to_period("M")
        if month != current_month:
            review_dates = panel.index[panel.index < session]
            if len(review_dates):
                review = pd.Timestamp(review_dates[-1])
                new_weights_series, n_eligible = selector(panel, sma200, review)
                new_weights = {k: float(v) for k, v in new_weights_series.to_dict().items() if v > 0}
                risky = sum(abs(new_weights.get(t, 0) - weights.get(t, 0)) for t in set(weights) | set(new_weights))
                cash = abs((1 - sum(new_weights.values())) - (1 - sum(weights.values())))
                nav *= 1 - 0.5 * (risky + cash) * cost_rate
                weights = new_weights
                signal_rows.append({
                    "review_date": review.date().isoformat(),
                    "n_eligible": int(n_eligible),
                    "n_selected": len(new_weights),
                    "tickers_selected": ",".join(sorted(new_weights)),
                })
            current_month = month
        rows.append({"date": session, "nav": nav})
        previous_date = session
    return pd.DataFrame(rows), pd.DataFrame(signal_rows)


def _trend_ok(panel: pd.DataFrame, sma200: pd.DataFrame, review: pd.Timestamp) -> pd.Series:
    history_ok = panel.loc[:review].notna().sum() >= MIN_HISTORY_SESSIONS
    return (panel.loc[review] > sma200.loc[review]) & history_ok


def ticker_aliases(cik_map: dict[str, str]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Dos tickers pueden compartir CIK (GOOGL/GOOG: misma empresa, dos clases).
    Devuelve (cik -> ticker principal, ticker principal -> [alias]) para que la
    actividad de insiders se copie a todas las clases de la misma empresa."""
    cik_to_ticker: dict[str, str] = {}
    aliases: dict[str, list[str]] = {}
    for ticker, cik in sorted(cik_map.items()):
        if cik in cik_to_ticker:
            aliases.setdefault(cik_to_ticker[cik], []).append(ticker)
        else:
            cik_to_ticker[cik] = ticker
    return cik_to_ticker, aliases


def _expand_aliases(frame: pd.DataFrame | pd.Series, aliases: dict[str, list[str]] | None):
    if not aliases or frame.empty:
        return frame
    extra = [frame.loc[[main]].rename(index={main: alias}) for main, alist in aliases.items() if main in frame.index for alias in alist]
    return pd.concat([frame, *extra]) if extra else frame


def make_selector_v01(transactions: pd.DataFrame, cik_to_ticker: dict[str, str], aliases: dict[str, list[str]] | None = None):
    """v0.1: neto insider (USD, 90 días) > 0 y precio > SMA200."""
    def selector(panel, sma200, review):
        scores = _expand_aliases(insider_signal(transactions, cik_to_ticker, review), aliases)
        weights = select_portfolio(scores, _trend_ok(panel, sma200, review))
        return weights, int((scores > 0).sum())
    return selector


def make_selector_relative(transactions: pd.DataFrame, cik_to_ticker: dict[str, str], aliases: dict[str, list[str]] | None = None):
    """Variante A: ranking relativo por sentimiento insider, siempre invertida."""
    def selector(panel, sma200, review):
        activity = _expand_aliases(insider_activity(transactions, cik_to_ticker, review), aliases)
        trend_ok = _trend_ok(panel, sma200, review)
        return select_relative(activity, trend_ok), int(trend_ok.sum())
    return selector


def make_selector_delta12_like(transactions: pd.DataFrame | None, cik_to_ticker: dict[str, str], aliases: dict[str, list[str]] | None = None):
    """Réplica Delta-12 sobre el universo US. Con `transactions=None` es el
    control sin veto; con transacciones, Variante B (veto por venta masiva)."""
    def selector(panel, sma200, review):
        audit = delta12_like_audit(panel, review)
        vetoed = insider_veto(_expand_aliases(insider_activity(transactions, cik_to_ticker, review), aliases)) if transactions is not None else None
        weights = select_delta12_like(audit, vetoed)
        n_eligible = int(audit["eligible"].sum()) if not audit.empty else 0
        return weights, n_eligible
    return selector


def backtest(transactions: pd.DataFrame, prices: pd.DataFrame, cik_to_ticker: dict[str, str], start: pd.Timestamp, end: pd.Timestamp, cost_rate: float = COST_RATE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compatibilidad v0.1: backtest de la señal absoluta original."""
    return run_backtest(prices, start, end, make_selector_v01(transactions, cik_to_ticker), cost_rate)


def buy_and_hold_benchmark(prices: pd.DataFrame, tickers: list[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Benchmark simple: mismo universo, igual-ponderado, comprado una vez y mantenido."""
    panel = prices.pivot(index="date", columns="ticker", values="adjusted_close").sort_index()
    panel = panel.loc[(panel.index >= start) & (panel.index <= end), [t for t in tickers if t in panel.columns]]
    normalized = panel / panel.bfill().iloc[0]
    nav = normalized.mean(axis=1) * 100
    return pd.DataFrame({"date": nav.index, "nav": nav.values})


def performance_metrics(nav: pd.Series, dates: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(nav, errors="coerce")
    keep = values.notna()
    values, dates = values[keep], pd.to_datetime(dates[keep])
    if len(values) < 2 or values.iloc[0] <= 0:
        return {"return": None, "cagr": None, "vol": None, "mdd": None, "sharpe": None}
    returns = values.pct_change().dropna()
    years = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1 / 365.25)
    vol = returns.std() * np.sqrt(252) if len(returns) > 2 else None
    cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1 if years >= 0.25 else None
    drawdown = values / values.cummax() - 1
    return {
        "return": float(values.iloc[-1] / values.iloc[0] - 1),
        "cagr": float(cagr) if cagr is not None else None,
        "vol": float(vol) if vol is not None else None,
        "mdd": float(drawdown.min()),
        "sharpe": float(cagr / vol) if (cagr is not None and vol not in (None, 0)) else None,
    }


# --------------------------------------------------------------------------
# Orquestación (I/O real; no se testea unitariamente)
# --------------------------------------------------------------------------

def reconstruct_raw_close(close_split_adjusted: pd.Series, splits: pd.Series | None) -> pd.Series:
    """Reconstruye el cierre SIN ajustar por splits a partir del cierre ajustado
    por splits de Yahoo y su columna "Stock Splits" (ratio del split en la fecha
    en que ocurre, 0 el resto de los días): close_raw(t) = close(t) * prod(splits
    posteriores a t). Los precios de la SEC son los de la fecha de la operación,
    así que se comparan contra esta serie, no contra el cierre ajustado.
    Sin información de splits devuelve NaN (la limpieza usa entonces el fallback)."""
    if splits is None:
        return pd.Series(np.nan, index=close_split_adjusted.index)
    ratios = pd.to_numeric(splits, errors="coerce").fillna(0.0)
    ratios = ratios.where(ratios > 0, 1.0)
    # factor(t) = producto de splits estrictamente posteriores a t
    future_factor = ratios[::-1].cumprod()[::-1] / ratios
    return close_split_adjusted * future_factor


def _download_prices(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(tickers=tickers, start=start, interval="1d", auto_adjust=False, actions=True, group_by="column", threads=True, progress=False, timeout=30)
    frames = []
    for ticker in tickers:
        if isinstance(raw.columns, pd.MultiIndex):
            if ticker not in raw.columns.get_level_values(-1):
                print(f"ADVERTENCIA: sin precios para {ticker}")
                continue
            sub = raw.xs(ticker, axis=1, level=-1, drop_level=True)
        else:
            sub = raw
        if "Close" not in sub:
            continue
        adjusted = sub["Adj Close"] if "Adj Close" in sub else sub["Close"]
        frame = pd.DataFrame({
            "date": pd.to_datetime(sub.index).tz_localize(None),
            "ticker": ticker,
            "adjusted_close": pd.to_numeric(adjusted, errors="coerce"),
            "close_raw": reconstruct_raw_close(pd.to_numeric(sub["Close"], errors="coerce"), sub["Stock Splits"] if "Stock Splits" in sub else None).to_numpy(),
        }).dropna(subset=["date", "adjusted_close"])
        frames.append(frame)
    if not frames:
        raise RuntimeError("No se pudo descargar precios para ningún ticker del universo.")
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    universe = pd.read_csv(UNIVERSE_PATH, dtype=str).fillna("")
    tickers = universe["yahoo_ticker"].tolist()

    print("Descargando mapeo ticker -> CIK de la SEC...")
    company_tickers = json.loads(_http_get(SEC_TICKERS_URL))
    cik_map = resolve_cik_map(company_tickers, tickers)  # ticker -> cik
    cik_to_ticker, aliases = ticker_aliases(cik_map)
    if aliases:
        print(f"Tickers que comparten CIK (misma empresa): {aliases}")
    cik_set = set(cik_map.values())

    print("Descubriendo archivos trimestrales de transacciones de insiders...")
    index_html = _http_get(SEC_INDEX_URL).decode("utf-8", errors="ignore")
    quarter_urls = discover_quarterly_zip_urls(index_html, START_QUARTER)
    print(f"{len(quarter_urls)} trimestres a procesar desde {START_QUARTER}.")

    SEC_CACHE.mkdir(parents=True, exist_ok=True)
    all_transactions = []
    for quarter, url in quarter_urls.items():
        cached_path = SEC_CACHE / f"{quarter}.zip"
        try:
            if cached_path.exists():
                print(f"  {quarter}: usando ZIP en caché ({cached_path})")
                zip_bytes = cached_path.read_bytes()
            else:
                print(f"  {quarter}: {url}")
                zip_bytes = _http_get(url)
                cached_path.write_bytes(zip_bytes)
            parsed = parse_quarter_zip(zip_bytes, cik_set)
        except Exception as error:  # noqa: BLE001
            print(f"  ADVERTENCIA: {quarter} falló y se omite: {error}")
            continue
        if not parsed.empty:
            all_transactions.append(parsed)
    if not all_transactions:
        raise SystemExit("No se pudo extraer ninguna transacción de insiders; abortando sin generar resultados falsos.")
    transactions = pd.concat(all_transactions, ignore_index=True)
    transactions.to_csv(OUT / "insider_transactions_filtered.csv", index=False)
    print(f"{len(transactions)} transacciones de mercado abierto (P/S) retenidas para el universo.")

    print("Descargando precios...")
    prices = _download_prices(tickers, start="2013-01-01")  # margen extra para SMA200 antes del inicio real del backtest
    prices.to_csv(OUT / "prices_daily.csv", index=False)

    backtest_start = pd.Timestamp("2016-06-01")  # deja margen de SMA200 tras el START_QUARTER de señales
    backtest_end = pd.Timestamp(prices.date.max())

    print("Limpiando transacciones (v0.2)...")
    clean, cleaning_report = clean_transactions(transactions, prices, cik_to_ticker)
    clean.to_csv(OUT / "insider_transactions_clean.csv", index=False)
    with (OUT / "cleaning_report.json").open("w", encoding="utf-8") as handle:
        json.dump(cleaning_report, handle, ensure_ascii=False, indent=2)
    print(f"  {cleaning_report}")

    results = run_all_variants(clean, prices, cik_to_ticker, backtest_start, backtest_end, aliases)
    write_results(results, cleaning_report, backtest_start, backtest_end, n_universe=len(tickers))


VARIANTS = [
    # (clave de archivo, nombre para el reporte, constructor del selector)
    ("v01_absoluta", "Beta-Insider v0.1 (neto > 0, SMA200; datos limpios)", lambda tx, m, a: make_selector_v01(tx, m, a)),
    ("varA_relativa", "Variante A: ranking relativo insider + SMA200 (siempre invertida)", lambda tx, m, a: make_selector_relative(tx, m, a)),
    ("delta12_us_control", "Control: réplica Delta-12 sobre universo US (sin veto)", lambda tx, m, a: make_selector_delta12_like(None, m, a)),
    ("varB_veto", "Variante B: réplica Delta-12 + veto por venta masiva de insiders", lambda tx, m, a: make_selector_delta12_like(tx, m, a)),
]


def run_all_variants(clean: pd.DataFrame, prices: pd.DataFrame, cik_to_ticker: dict[str, str], start: pd.Timestamp, end: pd.Timestamp, aliases: dict[str, list[str]] | None = None) -> dict[str, dict]:
    """Corre todas las variantes + benchmark. Devuelve {clave: {name, nav, signals, metrics}}."""
    results: dict[str, dict] = {}
    for key, name, build in VARIANTS:
        print(f"Backtest: {name}")
        nav_df, signals_df = run_backtest(prices, start, end, build(clean, cik_to_ticker, aliases))
        results[key] = {"name": name, "nav": nav_df, "signals": signals_df, "metrics": performance_metrics(nav_df["nav"], nav_df["date"])}
    tickers = sorted(prices["ticker"].unique())
    bench = buy_and_hold_benchmark(prices, tickers, start, end)
    results["benchmark"] = {"name": "Benchmark igual-ponderado (buy & hold)", "nav": bench, "signals": pd.DataFrame(), "metrics": performance_metrics(bench["nav"], bench["date"])}
    return results


def write_results(results: dict[str, dict], cleaning_report: dict[str, object], start: pd.Timestamp, end: pd.Timestamp, n_universe: int) -> None:
    for key, r in results.items():
        r["nav"].to_csv(OUT / f"nav_{key}.csv", index=False)
        if not r["signals"].empty:
            r["signals"].to_csv(OUT / f"signals_{key}.csv", index=False)
    # Compatibilidad con los nombres de la v0.1
    results["v01_absoluta"]["nav"].to_csv(OUT / "nav_beta_insider.csv", index=False)
    results["v01_absoluta"]["signals"].to_csv(OUT / "signals_by_review.csv", index=False)
    results["benchmark"]["nav"].to_csv(OUT / "nav_benchmark_equal_weight.csv", index=False)

    metrics = {r["name"]: r["metrics"] for r in results.values()}
    with (OUT / "summary_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2, default=str)

    fmt = lambda v: f"{v:.1%}" if v is not None else "—"
    fmt2 = lambda v: f"{v:.2f}" if v is not None else "—"
    lines = [
        "# Resultado del backtest exploratorio Beta-Insider (v0.2)", "",
        f"Generado automáticamente. Periodo: {start.date()} a {end.date()}. Universo: {n_universe} acciones US. Costo: {COST_RATE:.1%} por lado.", "",
        "| Serie | Retorno acumulado | CAGR | Volatilidad anual | Máximo retroceso | Sharpe (CAGR/vol) | Posiciones promedio | Meses en caja |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in results.values():
        m = r["metrics"]
        sig = r["signals"]
        avg_pos = f"{sig['n_selected'].mean():.2f}" if len(sig) else "—"
        empty = f"{int((sig['n_selected'] == 0).sum())}/{len(sig)}" if len(sig) else "—"
        lines.append(f"| {r['name']} | {fmt(m['return'])} | {fmt(m['cagr'])} | {fmt(m['vol'])} | {fmt(m['mdd'])} | {fmt2(m['sharpe'])} | {avg_pos} | {empty} |")
    lines += [
        "", "## Limpieza de transacciones", "",
        f"Entrada: {cleaning_report.get('input', 0)} filas. Descartadas por: duplicados {cleaning_report.get('dup', 0)}, "
        f"códigos inconsistentes {cleaning_report.get('inconsistent', 0)}, 10% owners {cleaning_report.get('ten_pct_owner', 0)}, "
        f"precio fuera de rango {cleaning_report.get('price_sanity', 0)}, valor > {MAX_TXN_VALUE_USD:,.0f} USD {cleaning_report.get('value_cap', 0)}. "
        f"Salida: {cleaning_report.get('output', 0)} filas (`insider_transactions_clean.csv`).",
        "", "## Cómo leer la comparación", "",
        "- La v0.1 y la Variante A usan solo información de insiders + SMA200. La Variante A siempre está invertida, así que su exposición es comparable al benchmark.",
        "- La Variante B solo se puede juzgar contra su control (réplica Delta-12 sin veto): la diferencia entre ambas es el efecto marginal del dato de insiders.",
        f"- Ventanas: v0.1 {SIGNAL_WINDOW_DAYS} días; A/B {SENTIMENT_WINDOW_DAYS} días. Veto B: venta neta <= {VETO_NET_USD:,.0f} USD sin compras.",
        "- La réplica Delta-12 omite el filtro de liquidez (no se descarga volumen; irrelevante en mega-caps).",
        "", "Ver `signals_<variante>.csv` para qué tickers entraron en cada revisión mensual.",
        "", "**Nota:** dataset trimestral de la SEC (rezago de publicación) y universo fijo de mega-caps; ver limitaciones en la propuesta de metodología.",
    ]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
