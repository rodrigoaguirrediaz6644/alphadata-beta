"""Gamma-6 US: momentum compuesto (3/6/12 meses, pesos 2/1/1) sobre mega-caps de EE.UU.

Investigación paralela, NO metodología oficial. No toca `data/`, `reports/`,
`strategy_state.json` ni las estrategias Sigma-6 / Delta-12. Todo queda en
`research/momentum_us/`.

Metodología: ver `METODOLOGIA_GAMMA6_US.md` en esta carpeta. Resumen:

- Universo: `config/universe_us.csv` (30 acciones US vía Trii CDV).
- Señal (fin de mes, solo con datos hasta la fecha de revisión):
    r3   = P_t / P_{t-63} - 1                (3 meses, sin saltar el último mes)
    r6   = P_{t-21} / P_{t-126} - 1          (6-1 meses)
    r12  = P_{t-21} / P_{t-252} - 1          (12-1 meses)
    score = promedio ponderado (2/1/1) de los z-scores cross-sectionales de r3, r6, r12.
- Selección: las 6 con mayor score entre las que tienen >= 252 sesiones y
  cotizan sobre su SMA200 (filtro de tendencia por acción).
- Tamaño: igual ponderado, 16,7% cada una. Sin filtro de índice, sin RSI.
- Variantes reportadas: Gamma-8 base (top 8, pesos 1/1/1) y Gamma-8 ajustada
  por volatilidad, como referencia de la versión menos concentrada.
- Benchmarks: igual-ponderada rebalanceada mensual (la vara justa), EW con
  tendencia por acción (candidata simple) y buy & hold sin rebalancear
  (referencia; dominada por NVDA).
- Costo: 0,1% por lado (Trii, acciones US); sensibilidad a 0,3%.

Además del backtest histórico, cada corrida registra la cartera objetivo
vigente y el seguimiento fuera de muestra desde LAUNCH_DATE, para juzgar la
estrategia con datos que no se usaron para diseñarla.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from research.common.engine import (
    download_prices,
    equal_weights,
    performance_metrics,
    run_backtest,
    to_panel,
    turnover_per_review,
    yearly_returns,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "results"
UNIVERSE_PATH = ROOT / "config" / "universe_us.csv"

N_POSITIONS = 6
MIN_HISTORY_SESSIONS = 252
COST_RATE = 0.001
COST_RATE_STRESS = 0.003
VOL_WINDOW = 126
BACKTEST_START = pd.Timestamp("2014-06-02")
PRICES_START = "2013-01-01"  # margen para 252 sesiones + SMA200 antes de BACKTEST_START
SPLIT_DATE = pd.Timestamp("2020-01-02")  # corte para las dos mitades de robustez
LAUNCH_DATE = pd.Timestamp("2026-10-01")  # inicio del seguimiento fuera de muestra
DOMINANT_TICKER = "NVDA"  # se reporta también sin él, porque explica gran parte del periodo


# --------------------------------------------------------------------------
# Señal (funciones puras)
# --------------------------------------------------------------------------

def momentum_components(panel: pd.DataFrame, review: pd.Timestamp) -> pd.DataFrame:
    """Componentes de la señal por ticker con datos hasta `review` inclusive."""
    close = panel.loc[:review]
    last = close.iloc[-1]
    lag = lambda n: close.shift(n).iloc[-1]  # noqa: E731
    out = pd.DataFrame({
        "close": last,
        "r3": last / lag(63) - 1,
        "r6": lag(21) / lag(126) - 1,
        "r12": lag(21) / lag(252) - 1,
        "vol": close.pct_change().iloc[-VOL_WINDOW:].std(),
        "sma200": close.rolling(200, min_periods=200).mean().iloc[-1],
        "history": close.notna().sum(),
    })
    out["history_ok"] = out["history"] >= MIN_HISTORY_SESSIONS
    out["above_sma200"] = out["close"] > out["sma200"]
    return out


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std()
    if not std or pd.isna(std):
        return series * 0.0
    return (series - series.mean()) / std


HORIZON_WEIGHTS = (2.0, 1.0, 1.0)  # pesos de r3, r6, r12 en la señal oficial de Gamma-6 (más peso al horizonte de 3 meses)
HORIZON_WEIGHTS_BASE = (1.0, 1.0, 1.0)  # referencia: la Gamma-8 base original


def composite_score(components: pd.DataFrame, vol_adjust: bool = False, weights: tuple[float, float, float] = HORIZON_WEIGHTS) -> pd.Series:
    """Promedio ponderado de z-scores de r3, r6, r12 (solo entre tickers con
    historia suficiente); opcionalmente dividido por la volatilidad de 6 meses."""
    valid = components[components["history_ok"]].dropna(subset=["r3", "r6", "r12"])
    if valid.empty:
        return pd.Series(dtype=float)
    w3, w6, w12 = weights
    score = (w3 * _zscore(valid["r3"]) + w6 * _zscore(valid["r6"]) + w12 * _zscore(valid["r12"])) / (w3 + w6 + w12)
    if vol_adjust:
        score = score / valid["vol"].replace(0, pd.NA)
    return score.dropna().astype(float)


def select_gamma8(components: pd.DataFrame, n_positions: int = N_POSITIONS, trend_filter: bool = False, vol_adjust: bool = False, weights: tuple[float, float, float] = HORIZON_WEIGHTS) -> tuple[pd.Series, int]:
    """Top-N por score compuesto, igual ponderado. Devuelve (pesos, n_elegibles)."""
    score = composite_score(components, vol_adjust=vol_adjust, weights=weights)
    if trend_filter:
        score = score[components.loc[score.index, "above_sma200"]]
    if score.empty:
        return pd.Series(dtype=float), 0
    top = score.sort_values(ascending=False).head(n_positions)
    return equal_weights(top.index), int(len(score))


def make_gamma8_selector(trend_filter: bool = False, vol_adjust: bool = False, n_positions: int = N_POSITIONS, weights: tuple[float, float, float] = HORIZON_WEIGHTS):
    def selector(panel: pd.DataFrame, review: pd.Timestamp):
        return select_gamma8(momentum_components(panel, review), n_positions, trend_filter, vol_adjust, weights)
    return selector


def selector_ew_rebalanced(panel: pd.DataFrame, review: pd.Timestamp):
    """Benchmark justo: todas las acciones con historia suficiente, igual ponderadas, rebalanceo mensual."""
    comp = momentum_components(panel, review)
    ok = comp.index[comp["history_ok"]]
    return equal_weights(ok), int(len(ok))


def selector_ew_trend(panel: pd.DataFrame, review: pd.Timestamp):
    """Candidata simple: igual ponderada SOLO entre las acciones que están sobre su
    SMA200, siempre 100% invertida (el peso de las que salen se reparte entre las
    que quedan). La versión que manda ese peso a caja rinde ~11% con MDD -13%:
    otro perfil de riesgo, no otra señal."""
    comp = momentum_components(panel, review)
    held = comp.index[comp["history_ok"] & comp["above_sma200"]]
    return equal_weights(held), int(len(held))


def buy_and_hold(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Referencia: igual ponderada comprada una vez y nunca rebalanceada."""
    window = panel.loc[(panel.index >= start) & (panel.index <= end)]
    normalized = window / window.bfill().iloc[0]
    nav = normalized.mean(axis=1) * 100
    return pd.DataFrame({"date": nav.index, "nav": nav.values})


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------

STRATEGIES = [
    ("gamma6", "Gamma-6 US (top 6, pesos 2/1/1, > SMA200)", make_gamma8_selector(trend_filter=True)),
    ("gamma8_base", "Referencia: Gamma-8 base (top 8, pesos 1/1/1, > SMA200)", make_gamma8_selector(trend_filter=True, n_positions=8, weights=HORIZON_WEIGHTS_BASE)),
    ("gamma8_vol", "Referencia: Gamma-8 ajustada por volatilidad (top 8, 1/1/1)", make_gamma8_selector(vol_adjust=True, n_positions=8, weights=HORIZON_WEIGHTS_BASE)),
    ("ew_rebalanced", "Benchmark: EW rebalanceada mensual", selector_ew_rebalanced),
    ("ew_trend", "Candidata simple: EW con tendencia por acción", selector_ew_trend),
]


def run_suite(panel: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cost_rate: float = COST_RATE) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for key, name, selector in STRATEGIES:
        nav, signals = run_backtest(panel, start, end, selector, cost_rate)
        results[key] = {"name": name, "nav": nav, "signals": signals, "metrics": performance_metrics(nav["nav"], nav["date"]), "turnover": turnover_per_review(signals)}
    bh = buy_and_hold(panel, start, end)
    results["buy_hold"] = {"name": "Referencia: buy & hold sin rebalancear", "nav": bh, "signals": pd.DataFrame(columns=["review_date", "n_eligible", "n_selected", "tickers_selected"]), "metrics": performance_metrics(bh["nav"], bh["date"]), "turnover": 0.0}
    return results


def current_target_portfolio(panel: pd.DataFrame) -> pd.DataFrame:
    """Cartera objetivo con el último cierre disponible (lo que se compraría en la próxima revisión)."""
    review = panel.index.max()
    comp = momentum_components(panel, review)
    score = composite_score(comp)
    weights, _ = select_gamma8(comp, trend_filter=True)
    table = pd.DataFrame({"score": score}).join(comp[["r3", "r6", "r12", "above_sma200"]])
    table["target_weight"] = weights.reindex(table.index).fillna(0.0)
    table = table.sort_values("score", ascending=False).reset_index().rename(columns={"index": "ticker"})
    table.insert(0, "review_date", review.date().isoformat())
    return table


def _fmt(value, pct=True):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.1%}" if pct else f"{value:.2f}"


def _metrics_table(results: dict[str, dict], title: str) -> list[str]:
    lines = [f"### {title}", "", "| Serie | CAGR | Vol anual | Máx. retroceso | Sharpe | Posiciones prom. | Entradas/mes |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in results.values():
        m, sig = r["metrics"], r["signals"]
        pos = f"{sig['n_selected'].mean():.1f}" if len(sig) else "—"
        lines.append(f"| {r['name']} | {_fmt(m['cagr'])} | {_fmt(m['vol'])} | {_fmt(m['mdd'])} | {_fmt(m['sharpe'], False)} | {pos} | {r['turnover']:.1f} |")
    return lines + [""]


def write_results(panel: pd.DataFrame, end: pd.Timestamp) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    full = run_suite(panel, BACKTEST_START, end)
    first_half = run_suite(panel, BACKTEST_START, SPLIT_DATE - pd.Timedelta(days=1))
    second_half = run_suite(panel, SPLIT_DATE, end)
    stress = run_suite(panel, BACKTEST_START, end, cost_rate=COST_RATE_STRESS)
    ex_dominant = run_suite(panel.drop(columns=[DOMINANT_TICKER], errors="ignore"), BACKTEST_START, end)

    for key, r in full.items():
        r["nav"].to_csv(OUT / f"nav_{key}.csv", index=False)
        if len(r["signals"]):
            r["signals"].to_csv(OUT / f"signals_{key}.csv", index=False)
    summary = {label: {r["name"]: r["metrics"] for r in res.values()} for label, res in [("completo", full), ("2014-2019", first_half), ("2020-hoy", second_half), (f"costo {COST_RATE_STRESS:.1%}", stress), (f"sin {DOMINANT_TICKER}", ex_dominant)]}
    (OUT / "summary_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    yearly = pd.DataFrame({r["name"]: yearly_returns(r["nav"]) for r in full.values()})
    yearly.to_csv(OUT / "yearly_returns.csv")

    target = current_target_portfolio(panel)
    target.to_csv(OUT / "current_target_portfolio.csv", index=False)

    # Seguimiento fuera de muestra: mismas reglas, desde LAUNCH_DATE, solo si ya hay datos posteriores.
    oos_lines: list[str] = []
    if end > LAUNCH_DATE:
        oos = run_suite(panel, LAUNCH_DATE, end)
        for key, r in oos.items():
            r["nav"].to_csv(OUT / f"oos_nav_{key}.csv", index=False)
        oos_lines = _metrics_table(oos, f"Seguimiento fuera de muestra desde {LAUNCH_DATE.date()} (criterio de éxito: Sharpe de Gamma-6 > EW rebalanceada tras 12 meses)")

    # Bitácora de carteras objetivo (una fila por corrida; sirve como registro de paper trading).
    log_path = OUT / "paper_trading_log.csv"
    log_row = pd.DataFrame([{"run_date": date.today().isoformat(), "review_date": target["review_date"].iloc[0], "tickers": ",".join(sorted(target.loc[target.target_weight > 0, "ticker"]))}])
    if log_path.exists():
        previous = pd.read_csv(log_path, dtype=str)
        if not (previous["review_date"] == log_row["review_date"].iloc[0]).any():
            log_row = pd.concat([previous, log_row], ignore_index=True)
        else:
            log_row = previous
    log_row.to_csv(log_path, index=False)

    lines = ["# Gamma-6 US — resultados del backtest exploratorio", "", f"Generado automáticamente. Periodo completo: {BACKTEST_START.date()} a {end.date()}. Universo: {panel.shape[1]} acciones US. Costo base: {COST_RATE:.1%} por lado. Revisión mensual.", ""]
    lines += _metrics_table(full, "Periodo completo")
    lines += _metrics_table(first_half, f"Primera mitad ({BACKTEST_START.date()} a {SPLIT_DATE.date()})")
    lines += _metrics_table(second_half, f"Segunda mitad ({SPLIT_DATE.date()} a {end.date()})")
    lines += _metrics_table(ex_dominant, f"Sin {DOMINANT_TICKER} (robustez frente al ticker dominante)")
    lines += _metrics_table(stress, f"Costo {COST_RATE_STRESS:.1%} por lado (estrés de costos)")
    lines += ["### Retorno por año calendario (periodo completo)", "", "| Año | " + " | ".join(yearly.columns) + " |", "| --- |" + " ---: |" * len(yearly.columns)]
    for year, row in yearly.iterrows():
        lines.append(f"| {year} | " + " | ".join(_fmt(v) for v in row.values) + " |")
    lines += [""]
    lines += oos_lines
    held = target[target.target_weight > 0]
    lines += [f"### Cartera objetivo vigente (cierre {target['review_date'].iloc[0]})", "", "| Ticker | Score | r3 | r6-1 | r12-1 | > SMA200 | Peso |", "| --- | ---: | ---: | ---: | ---: | :---: | ---: |"]
    for _, row in held.iterrows():
        lines.append(f"| {row.ticker} | {row.score:.2f} | {_fmt(row.r3)} | {_fmt(row.r6)} | {_fmt(row.r12)} | {'sí' if row.above_sma200 else 'no'} | {_fmt(row.target_weight)} |")
    lines += ["", "Ver `current_target_portfolio.csv` para el ranking completo, `signals_<serie>.csv` para la cartera de cada revisión histórica y `paper_trading_log.csv` para la bitácora de carteras objetivo por corrida.", "", "**Lectura:** la vara justa es la EW rebalanceada mensual; el buy & hold sin rebalancear está dominado por el ticker de mayor crecimiento y solo se muestra como referencia. Ver `METODOLOGIA_GAMMA6_US.md` para hipótesis, reglas y riesgos."]
    (OUT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    universe = pd.read_csv(UNIVERSE_PATH, dtype=str).fillna("")
    tickers = universe.loc[universe["estado"].str.lower().eq("activo"), "yahoo_ticker"].tolist()
    print(f"Descargando precios de {len(tickers)} acciones...")
    prices = download_prices(tickers, start=PRICES_START)
    OUT.mkdir(parents=True, exist_ok=True)
    prices.to_csv(OUT / "prices_daily.csv", index=False)
    panel = to_panel(prices)
    write_results(panel, pd.Timestamp(panel.index.max()))


if __name__ == "__main__":
    main()
