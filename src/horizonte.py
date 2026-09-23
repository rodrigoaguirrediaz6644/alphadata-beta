"""Estrategia Horizonte — **retirada del informe el 23-09-2026.**

El codigo queda y no se borra: **borrarlo borraria la auditoria que la retiro**,
y esa auditoria es lo unico que explica la decision dentro de un anio. Sigue
siendo ejecutable a mano con `python -m src.horizonte`.

**Por que salio.** La reemplazo Ahorro Generacional, que contesta exactamente la
misma pregunta: en que fondo esta parada la plata previsional. Dos estrategias
contestando lo mismo es un valor con mas de una casa, y el dia que discrepen
-y van a discrepar- no hay regla que diga cual manda; el informe estaria
publicando dos respuestas contradictorias en el mismo correo.

**Y lo que la auditoria encontro, que es por que perdio ella y no la otra:**

- La ventana publicada arrancaba en **2012** sin razon escrita, y eso dejaba
  fuera la crisis de 2008, que es el episodio que mas decide en esta linea.
- El registro hacia adelante estaba **vacio**: once publicaciones sin un solo
  cambio de fondo.
- El backtest la dejaba **3,6 anios quieta en Fondo A**, o sea que lo que
  mostraba era el Fondo A con otro nombre.

Ahorro Generacional no arregla ninguna de las tres por ser mejor regla: las
arregla porque **registra hacia adelante con los parametros congelados antes de
mirar**, que es lo unico que ninguno de los dos backtests podia hacer.

Ver `registro/README.md` y `research/horizonte_auditoria/`.
"""
from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
CUOTA_URL = "https://raw.githubusercontent.com/collabmarket/data_afp/master/data/VC-CUPRUM.csv"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQCOM,VIXCLS"
EXTERNAL_CACHE = DATA / "horizonte_external.csv"
START = pd.Timestamp("2012-08-01")
TEST_START = pd.Timestamp("2021-01-01")
REPORT_START = "<!-- HORIZONTE_START -->"
REPORT_END = "<!-- HORIZONTE_END -->"


def _download(url: str, attempts: int = 3, timeout: int = 30) -> str:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "AlphaData/2.0"})
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except Exception as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"No fue posible descargar {url} después de {attempts} intentos") from last_error


def _parse_external(csv_text: str) -> pd.DataFrame:
    external = pd.read_csv(StringIO(csv_text))
    external = external.rename(columns={"observation_date": "date", "NASDAQCOM": "nasdaq", "VIXCLS": "vix"})
    external["date"] = pd.to_datetime(external["date"])
    for column in ["nasdaq", "vix"]:
        external[column] = pd.to_numeric(external[column], errors="coerce")
    external = external[["date", "nasdaq", "vix"]].sort_values("date")
    if external[["nasdaq", "vix"]].notna().sum().min() == 0:
        raise ValueError("FRED no entregó datos válidos de NASDAQ y VIX")
    return external


def _fetch_external_secondary() -> pd.DataFrame:
    import yfinance as yf

    series = {}
    for symbol, column in [("^IXIC", "nasdaq"), ("^VIX", "vix")]:
        history = yf.Ticker(symbol).history(start="2012-01-01", auto_adjust=False)
        if history.empty or "Close" not in history:
            raise RuntimeError(f"Fuente secundaria sin datos para {symbol}")
        values = history["Close"].rename(column)
        values.index = pd.to_datetime(values.index).tz_localize(None)
        series[column] = values
    external = pd.concat(series.values(), axis=1).reset_index()
    external = external.rename(columns={external.columns[0]: "date"})
    return external[["date", "nasdaq", "vix"]].sort_values("date")


def _fetch_external() -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        external = _parse_external(_download(FRED_URL))
        source = "FRED"
    except Exception as fred_error:
        print(f"Advertencia: FRED no respondió ({fred_error}); usando fuente secundaria.")
        try:
            external = _fetch_external_secondary()
            source = "Yahoo Finance"
        except Exception as secondary_error:
            if not EXTERNAL_CACHE.exists():
                raise RuntimeError(
                    "No fue posible obtener NASDAQ/VIX y no existe un respaldo local válido"
                ) from secondary_error
            external = pd.read_csv(EXTERNAL_CACHE, parse_dates=["date"])
            source = "respaldo local"
    external.to_csv(EXTERNAL_CACHE, index=False)
    print(f"NASDAQ/VIX obtenidos desde {source}; {len(external)} observaciones.")
    return external


def fetch_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    cuotas = pd.read_csv(StringIO(_download(CUOTA_URL)), sep=";", decimal=",")
    cuotas = cuotas.rename(columns={"Fecha": "date", "A": "a", "E": "e"})
    cuotas["date"] = pd.to_datetime(cuotas["date"])
    cuotas = cuotas[["date", "a", "e"]].dropna().sort_values("date")
    return cuotas, _fetch_external()

# Rezago tolerado de las cuotas de Cuprum. La AFP publica con unos dias de
# atraso y hay fines de semana de por medio; mas de dos semanas es que el
# proveedor dejo de responder.
REZAGO_MAXIMO_CUOTAS = 14


def verificar_completitud(cuotas: pd.DataFrame, external: pd.DataFrame,
                          ahora: pd.Timestamp | None = None) -> list[str]:
    """Que lo que se bajo este completo, como el informe de cobertura para los precios.

    Hacia falta: una corrida anterior tenia huecos en 2012 --332 datos donde el
    recalculo encontro 366-- y nadie se entero. Que el resumen publicado no se
    moviera con eso fue suerte, no control. El valor cuota se publica **todos
    los dias calendario**, asi que un dia ausente en el rango es un hueco, no
    un feriado.
    """
    problemas = []
    if cuotas.empty:
        return ["las cuotas de Cuprum vinieron vacias"]
    fechas = pd.DatetimeIndex(cuotas["date"])
    faltan = pd.date_range(fechas.min(), fechas.max(), freq="D").difference(fechas)
    if len(faltan):
        muestra = ", ".join(f"{f:%d-%m-%Y}" for f in faltan[:5])
        problemas.append(f"faltan {len(faltan)} dias calendario en las cuotas de Cuprum ({muestra}...)")
    nulos = int(cuotas[["a", "e"]].isna().sum().sum())
    if nulos:
        problemas.append(f"{nulos} valores cuota nulos")
    rezago = (pd.Timestamp(ahora or pd.Timestamp.now()).normalize() - fechas.max().normalize()).days
    if rezago > REZAGO_MAXIMO_CUOTAS:
        problemas.append(f"las cuotas de Cuprum llevan {rezago} dias sin actualizarse")
    if external.empty:
        problemas.append("las series externas vinieron vacias")
    else:
        habiles = pd.DatetimeIndex(external["date"])
        huecos = pd.bdate_range(habiles.min(), habiles.max()).difference(habiles)
        if len(huecos):
            problemas.append(f"faltan {len(huecos)} dias habiles en las series de FRED")
    return problemas


def monthly_features(cuotas: pd.DataFrame, external: pd.DataFrame) -> pd.DataFrame:
    q = cuotas.set_index("date").resample("ME").last().dropna()
    latest = cuotas["date"].max()
    q = q[q.index.to_period("M") < latest.to_period("M")]
    ext = external.set_index("date").resample("ME").last()
    x = q.join(ext, how="left")
    a_return = x["a"].pct_change(12, fill_method=None)
    e_return = x["e"].pct_change(12, fill_method=None)
    x["relative_momentum"] = a_return > e_return
    x["absolute_momentum"] = a_return > 0
    x["cuprum_a_trend"] = x["a"] > x["a"].rolling(6).mean()
    x["nasdaq_trend"] = x["nasdaq"] > x["nasdaq"].rolling(6).mean()
    x["vix_below_30"] = x["vix"] < 30
    signals = ["relative_momentum", "absolute_momentum", "cuprum_a_trend", "nasdaq_trend", "vix_below_30"]
    valid = x[["a", "e", "nasdaq", "vix"]].notna().all(axis=1) & a_return.notna() & e_return.notna()
    x["score"] = x[signals].astype(int).sum(axis=1)
    x["recommendation"] = pd.NA
    x.loc[valid, "recommendation"] = np.where(x.loc[valid, "score"] >= 2, "A", "E")
    return x


def backtest(cuotas: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    daily = cuotas.set_index("date").sort_index()
    returns = daily[["a", "e"]].pct_change().fillna(0)
    targets: dict[pd.Timestamp, str] = {}
    trades: list[dict[str, object]] = []
    current: str | None = None
    for signal_date, row in features.dropna(subset=["recommendation"]).iterrows():
        target = str(row["recommendation"])
        if target == current:
            continue
        position = daily.index.searchsorted(signal_date, side="right") + 3
        if position >= len(daily):
            continue
        execution = daily.index[position]
        targets[execution] = target
        trades.append(
            {
                "signal_date": signal_date.date().isoformat(),
                "execution_date": execution.date().isoformat(),
                "from_fund": current or "NONE",
                "to_fund": target,
                "is_switch": current is not None,
            }
        )
        current = target
    events = pd.Series(targets, dtype="object").sort_index()
    holdings = events.reindex(daily.index).ffill().dropna()
    selected = pd.Series(
        np.where(holdings.eq("A"), returns.loc[holdings.index, "a"], returns.loc[holdings.index, "e"]),
        index=holdings.index,
    )
    return selected, pd.DataFrame(trades)


def metrics(returns: pd.Series, start: pd.Timestamp, end: pd.Timestamp | None = None) -> dict[str, float]:
    values = returns[returns.index >= start]
    if end is not None:
        values = values[values.index < end]
    nav = (1 + values).cumprod()
    years = max((nav.index[-1] - nav.index[0]).days / 365.25, 1 / 365.25)
    return {
        "cumulative_return": float(nav.iloc[-1] - 1),
        "cagr": float(nav.iloc[-1] ** (1 / years) - 1),
        "annualized_volatility": float(values.std() * np.sqrt(252)),
        "max_drawdown": float((nav / nav.cummax() - 1).min()),
        "observations": int(len(values)),
    }


def build_outputs(cuotas: pd.DataFrame, features: pd.DataFrame, returns: pd.Series, trades: pd.DataFrame) -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    daily = cuotas.set_index("date")
    alternatives = {
        "Estrategia Horizonte": returns,
        "Fondo A Cuprum": daily["a"].pct_change().fillna(0),
        "Fondo E Cuprum": daily["e"].pct_change().fillna(0),
        "Cuprum 50/50": daily[["a", "e"]].pct_change().mean(axis=1).fillna(0),
    }
    rows = []
    periods = [("completo_desde_2012", START, None), ("fuera_muestra_2021+", TEST_START, None)]
    for name, series in alternatives.items():
        for period, start, end in periods:
            row = metrics(series, start, end)
            row.update({"strategy": name, "period": period, "afp": "CUPRUM"})
            rows.append(row)
    summary = pd.DataFrame(rows)
    annual_rows = []
    for year in range(2012, cuotas["date"].max().year + 1):
        for name, series in alternatives.items():
            subset = series[(series.index >= pd.Timestamp(f"{year}-01-01")) & (series.index < pd.Timestamp(f"{year+1}-01-01"))]
            if len(subset) > 1:
                row = metrics(subset, subset.index.min())
                row.update({"strategy": name, "year": year, "afp": "CUPRUM"})
                annual_rows.append(row)
    signal_columns = [
        "relative_momentum", "absolute_momentum", "cuprum_a_trend",
        "nasdaq_trend", "vix_below_30", "score", "recommendation",
    ]
    signals = features[signal_columns].dropna(subset=["recommendation"]).reset_index()
    signals.to_csv(DATA / "horizonte_signals.csv", index=False)
    trades.to_csv(DATA / "horizonte_trades.csv", index=False)
    summary.to_csv(DATA / "horizonte_backtest_summary.csv", index=False)
    pd.DataFrame(annual_rows).to_csv(DATA / "horizonte_annual.csv", index=False)
    cuotas.to_csv(DATA / "horizonte_quotes.csv", index=False)
    latest = signals.iloc[-1]
    executed = trades[pd.to_datetime(trades["execution_date"]) <= cuotas["date"].max()]
    current_fund = executed.iloc[-1]["to_fund"] if len(executed) else latest["recommendation"]
    state = {
        "as_of": cuotas["date"].max().date().isoformat(),
        "signal_date": pd.Timestamp(latest["date"]).date().isoformat(),
        "recommendation": latest["recommendation"],
        "score": int(latest["score"]),
        "current_fund": current_fund,
        "next_execution_date": None if executed.index.max() == trades.index.max() else trades.iloc[-1]["execution_date"],
        "source": "Superintendencia de Pensiones, distribución CSV de collabmarket/data_afp",
    }
    (DATA / "horizonte_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"summary": summary, "annual": pd.DataFrame(annual_rows), "state": state, "trades": trades}


def _pct(valor: float) -> str:
    return f"{valor:.1%}".replace(".", ",")


def _pesos(retorno: float) -> str:
    """Lo que habría pasado con un millón, que es lo que se entiende.

    El acumulado en porcentaje obliga a hacer la cuenta de cabeza y nadie la
    hace. El resto del informe está escrito en pesos y esta sección era la
    única que seguía en CAGR y volatilidad.
    """
    return f"$ {1_000_000 * (1 + retorno):,.0f}".replace(",", ".")


def _ventaja_en_palabras(ventaja: float | None) -> str:
    """Lo que la regla le sumó o le restó a quedarse quieto en el Fondo A."""
    if ventaja is None:
        return "Todavía no hay con qué comparar."
    plata = 1_000_000 * abs(ventaja)
    cuanto = f"$ {plata:,.0f}".replace(",", ".")
    if abs(ventaja) < .005:
        return ("Moverse entre fondos dio prácticamente lo mismo que quedarse quieto en el "
                "Fondo A: la diferencia sobre un millón es menor a $5.000.")
    verbo = "más" if ventaja > 0 else "menos"
    return (f"Sobre un millón, moverse entre fondos dejó **{cuanto} {verbo}** que quedarse "
            f"quieto en el Fondo A durante todo el período.")


def _replace_section(text: str, section: str) -> str:
    if REPORT_START in text and REPORT_END in text:
        before, rest = text.split(REPORT_START, 1)
        _, after = rest.split(REPORT_END, 1)
        return before + section + after
    marker = "</main>"
    return text.replace(marker, section + marker) if marker in text else text + "\n" + section


def update_report(outputs: dict) -> None:
    state = outputs["state"]
    oos = outputs["summary"][outputs["summary"]["period"] == "fuera_muestra_2021+"].copy()
    rows = "".join(
        f"<tr><td>{r.strategy}</td><td>{_pct(r.cagr)}</td><td>{_pct(r.cumulative_return)}</td>"
        f"<td>{_pesos(r.cumulative_return)}</td><td>{_pct(r.max_drawdown)}</td></tr>"
        for r in oos.itertuples()
    )
    propia = oos[oos.strategy == "Estrategia Horizonte"]
    quieto = oos[oos.strategy == "Fondo A Cuprum"]
    ventaja = (float(propia.cumulative_return.iloc[0]) - float(quieto.cumulative_return.iloc[0])
               if len(propia) and len(quieto) else None)
    section = f"""{REPORT_START}<section><h2>Estrategia Horizonte</h2>
    <p><strong>Fondo vigente:</strong> Fondo {state['current_fund']} ·
    <strong>última señal:</strong> Fondo {state['recommendation']} ({state['score']}/5) ·
    <strong>fecha de señal:</strong> {state['signal_date']} ·
    <strong>datos Cuprum al:</strong> {state['as_of']}.</p>
    <p>Horizonte decide todos los meses entre el Fondo A y el Fondo E de la AFP. No compra
    acciones: mueve el ahorro previsional de un fondo al otro.</p>
    <table><thead><tr><th>Qué se hizo con la plata</th><th>Por año</th><th>En total desde 2021</th>
    <th>Un millón habría quedado en</th><th>Peor caída</th></tr></thead>
    <tbody>{rows}</tbody></table>
    <p>{_ventaja_en_palabras(ventaja)}</p>
    <p class="muted">Medido desde 2021 sobre datos que la regla no vio cuando se escribió. Se revisa una vez
    al mes: va al Fondo A si al menos 2 de 5 señales lo piden, y el cambio se ejecuta al cuarto valor cuota
    hábil siguiente. Los valores cuota son de AFP Cuprum y de nadie más.</p></section>{REPORT_END}"""
    html_path = REPORTS / "latest_report.html"
    html_path.write_text(_replace_section(html_path.read_text(encoding="utf-8"), section), encoding="utf-8")
    md_path = REPORTS / "latest_report.md"
    md_section = (
        f"\n{REPORT_START}\n## Estrategia Horizonte\n\n"
        "Horizonte decide todos los meses entre el Fondo A y el Fondo E de la AFP. "
        "No compra acciones: mueve el ahorro previsional de un fondo al otro.\n\n"
        f"- Hoy está en el **Fondo {state['current_fund']}**.\n"
        f"- La última revisión, del {state['signal_date']}, pidió el Fondo "
        f"{state['recommendation']} con {state['score']} de 5 señales a favor.\n"
        f"- Los valores cuota de Cuprum están al {state['as_of']}.\n"
        f"- {_ventaja_en_palabras(ventaja)}\n"
        f"- El detalle está en `data/horizonte_backtest_summary.csv`, `data/horizonte_annual.csv`, "
        f"`data/horizonte_trades.csv` y `data/horizonte_signals.csv`.\n{REPORT_END}\n"
    )
    md_path.write_text(_replace_section(md_path.read_text(encoding="utf-8"), md_section), encoding="utf-8")


def main() -> None:
    cuotas, external = fetch_inputs()
    problemas = verificar_completitud(cuotas, external)
    if problemas:
        raise RuntimeError("Horizonte: los insumos no estan completos. " + "; ".join(problemas)
                           + ". Ver CENSO_DE_SERIES.md: un backtest sobre una serie con huecos "
                             "publica cifras que nadie puede reproducir.")
    features = monthly_features(cuotas, external)
    returns, trades = backtest(cuotas, features)
    outputs = build_outputs(cuotas, features, returns, trades)
    update_report(outputs)
    print(f"Estrategia Horizonte actualizada al {outputs['state']['as_of']}; fondo vigente {outputs['state']['current_fund']}")


if __name__ == "__main__":
    main()
