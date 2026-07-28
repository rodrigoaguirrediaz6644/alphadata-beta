from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
CUOTA_URL = "https://raw.githubusercontent.com/collabmarket/data_afp/master/data/VC-CUPRUM.csv"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQCOM,VIXCLS"
START = pd.Timestamp("2012-08-01")
TEST_START = pd.Timestamp("2021-01-01")
REPORT_START = "<!-- CUPRUM_AE_START -->"
REPORT_END = "<!-- CUPRUM_AE_END -->"


def _download(url: str) -> str:
    request = Request(url, headers={"User-Agent": "AlphaData/2.0"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def fetch_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    cuotas = pd.read_csv(StringIO(_download(CUOTA_URL)), sep=";", decimal=",")
    cuotas = cuotas.rename(columns={"Fecha": "date", "A": "a", "E": "e"})
    cuotas["date"] = pd.to_datetime(cuotas["date"])
    cuotas = cuotas[["date", "a", "e"]].dropna().sort_values("date")
    external = pd.read_csv(StringIO(_download(FRED_URL)))
    external = external.rename(columns={"observation_date": "date", "NASDAQCOM": "nasdaq", "VIXCLS": "vix"})
    external["date"] = pd.to_datetime(external["date"])
    for column in ["nasdaq", "vix"]:
        external[column] = pd.to_numeric(external[column], errors="coerce")
    return cuotas, external


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
        "Cuprum A/E": returns,
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
    signals.to_csv(DATA / "cuprum_ae_signals.csv", index=False)
    trades.to_csv(DATA / "cuprum_ae_trades.csv", index=False)
    summary.to_csv(DATA / "cuprum_ae_backtest_summary.csv", index=False)
    pd.DataFrame(annual_rows).to_csv(DATA / "cuprum_ae_annual.csv", index=False)
    cuotas.to_csv(DATA / "cuprum_ae_quotes.csv", index=False)
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
    (DATA / "cuprum_ae_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"summary": summary, "annual": pd.DataFrame(annual_rows), "state": state, "trades": trades}


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
        f"<tr><td>{r.strategy}</td><td>{r.cagr:.2%}</td><td>{r.cumulative_return:.2%}</td>"
        f"<td>{r.annualized_volatility:.2%}</td><td>{r.max_drawdown:.2%}</td></tr>"
        for r in oos.itertuples()
    )
    section = f"""{REPORT_START}<section><h2>Cuprum A/E</h2>
    <p><strong>Fondo vigente:</strong> Fondo {state['current_fund']} ·
    <strong>última señal:</strong> Fondo {state['recommendation']} ({state['score']}/5) ·
    <strong>fecha de señal:</strong> {state['signal_date']} ·
    <strong>datos Cuprum al:</strong> {state['as_of']}.</p>
    <table><thead><tr><th>Estrategia</th><th>CAGR</th><th>Acumulado</th><th>Volatilidad</th><th>Máximo retroceso</th></tr></thead>
    <tbody>{rows}</tbody></table>
    <p class="muted">Prueba fuera de muestra desde 2021. Evaluación mensual; Fondo A con al menos 2 de 5 señales;
    ejecución al cuarto valor cuota hábil posterior. Datos de fondos exclusivamente AFP Cuprum.</p></section>{REPORT_END}"""
    html_path = REPORTS / "latest_report.html"
    html_path.write_text(_replace_section(html_path.read_text(encoding="utf-8"), section), encoding="utf-8")
    md_path = REPORTS / "latest_report.md"
    md_section = (
        f"\n{REPORT_START}\n## Cuprum A/E\n\n"
        f"- Fondo vigente: **Fondo {state['current_fund']}**.\n"
        f"- Última señal: Fondo {state['recommendation']} ({state['score']}/5), fecha {state['signal_date']}.\n"
        f"- Datos Cuprum actualizados al {state['as_of']}.\n"
        f"- Backtest y tablas: `data/cuprum_ae_backtest_summary.csv`, `data/cuprum_ae_annual.csv`, "
        f"`data/cuprum_ae_trades.csv` y `data/cuprum_ae_signals.csv`.\n{REPORT_END}\n"
    )
    md_path.write_text(_replace_section(md_path.read_text(encoding="utf-8"), md_section), encoding="utf-8")


def main() -> None:
    cuotas, external = fetch_inputs()
    features = monthly_features(cuotas, external)
    returns, trades = backtest(cuotas, features)
    outputs = build_outputs(cuotas, features, returns, trades)
    update_report(outputs)
    print(f"Cuprum A/E actualizada al {outputs['state']['as_of']}; fondo vigente {outputs['state']['current_fund']}")


if __name__ == "__main__":
    main()
