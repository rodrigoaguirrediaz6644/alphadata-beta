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
SIGNAL_WINDOW_DAYS = 90
MIN_HISTORY_SESSIONS = 252
MAX_POSITIONS = 8
POSITION_CAP = 0.15


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


def parse_quarter_zip(zip_bytes: bytes, cik_set: set[str]) -> pd.DataFrame:
    """Extrae transacciones no-derivadas de mercado abierto (P/S) para el
    conjunto de CIK dado, desde un ZIP trimestral de la SEC.

    Devuelve columnas: cik, trans_date, trans_code, acquired_disposed, shares,
    price_per_share, value.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        submissions = _read_tsv_from_zip(archive, ["SUBMISSION.tsv", "SUBMISSION"])
        missing_sub = _REQUIRED_SUBMISSION_COLS.difference(submissions.columns)
        if missing_sub:
            raise RuntimeError(f"SUBMISSION.tsv no tiene las columnas esperadas: {sorted(missing_sub)}")
        submissions = submissions[submissions["ISSUERCIK"].isin(cik_set)]
        if submissions.empty:
            return pd.DataFrame(columns=["cik", "trans_date", "trans_code", "acquired_disposed", "shares", "price_per_share", "value"])

        trans = _read_tsv_from_zip(archive, ["NONDERIV_TRANS.tsv", "NONDERIV_TRANS"])
        missing_trans = _REQUIRED_TRANS_COLS.difference(trans.columns)
        if missing_trans:
            raise RuntimeError(f"NONDERIV_TRANS.tsv no tiene las columnas esperadas: {sorted(missing_trans)}")

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
    return merged.rename(columns={"ISSUERCIK": "cik", "TRANS_CODE": "trans_code", "TRANS_ACQUIRED_DISP_CD": "acquired_disposed"})[
        ["cik", "trans_date", "trans_code", "acquired_disposed", "shares", "price_per_share", "value"]
    ]


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


def backtest(
    transactions: pd.DataFrame,
    prices: pd.DataFrame,
    cik_to_ticker: dict[str, str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    cost_rate: float = COST_RATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backtest mensual histórico. Devuelve (nav_diaria, señales_por_revisión).

    `prices` debe tener columnas date, ticker, adjusted_close, y suficiente
    historia previa a `start` para calcular SMA200.
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
                review = review_dates[-1]
                scores = insider_signal(transactions, cik_to_ticker, pd.Timestamp(review))
                history_ok = panel.loc[:review].notna().sum() >= MIN_HISTORY_SESSIONS
                trend_ok = (panel.loc[review] > sma200.loc[review]) & history_ok
                new_weights_series = select_portfolio(scores, trend_ok)
                new_weights = new_weights_series.to_dict()
                risky = sum(abs(new_weights.get(t, 0) - weights.get(t, 0)) for t in set(weights) | set(new_weights))
                cash = abs((1 - sum(new_weights.values())) - (1 - sum(weights.values())))
                nav *= 1 - 0.5 * (risky + cash) * cost_rate
                weights = new_weights
                signal_rows.append({
                    "review_date": review.date().isoformat(),
                    "n_eligible": int((scores > 0).sum()),
                    "n_selected": len(new_weights),
                    "tickers_selected": ",".join(sorted(new_weights)),
                })
            current_month = month
        rows.append({"date": session, "nav": nav})
        previous_date = session
    return pd.DataFrame(rows), pd.DataFrame(signal_rows)


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

def _download_prices(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(tickers=tickers, start=start, interval="1d", auto_adjust=False, actions=False, group_by="column", threads=True, progress=False, timeout=30)
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
        }).dropna()
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
    cik_to_ticker = {cik: ticker for ticker, cik in cik_map.items()}
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

    nav_df, signals_df = backtest(transactions, prices, cik_to_ticker, backtest_start, backtest_end)
    benchmark_df = buy_and_hold_benchmark(prices, tickers, backtest_start, backtest_end)

    nav_df.to_csv(OUT / "nav_beta_insider.csv", index=False)
    signals_df.to_csv(OUT / "signals_by_review.csv", index=False)
    benchmark_df.to_csv(OUT / "nav_benchmark_equal_weight.csv", index=False)

    metrics = {
        "Beta-Insider": performance_metrics(nav_df["nav"], nav_df["date"]),
        "Benchmark igual-ponderado (buy & hold)": performance_metrics(benchmark_df["nav"], benchmark_df["date"]),
    }
    with (OUT / "summary_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2, default=str)

    lines = ["# Resultado del backtest exploratorio Beta-Insider", "", f"Generado automáticamente. Periodo: {backtest_start.date()} a {backtest_end.date()}.", "", "| Serie | Retorno acumulado | CAGR | Volatilidad anual | Máximo retroceso |", "| --- | ---: | ---: | ---: | ---: |"]
    for name, m in metrics.items():
        fmt = lambda v: f"{v:.1%}" if v is not None else "—"
        lines.append(f"| {name} | {fmt(m['return'])} | {fmt(m['cagr'])} | {fmt(m['vol'])} | {fmt(m['mdd'])} |")
    lines += ["", f"Revisiones mensuales con señal: {len(signals_df)}. Ver `signals_by_review.csv` para el detalle de qué tickers entraron cada mes.", "", "**Nota:** este backtest usa el dataset trimestral de la SEC (con el rezago de publicación que eso implica) y un universo fijo de 31 mega-caps; ver limitaciones en la propuesta de metodología compartida por separado."]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
