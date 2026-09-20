from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

CONJUNTO = "Conjunto AlphaData"
STRATEGIES = ["Sigma-6", "Delta-12", "Gamma-6"]
BENCHMARK = "IPSA TR"
SERIES = [CONJUNTO, *STRATEGIES, BENCHMARK]
COLORS = {CONJUNTO: "#101828", "Sigma-6": "#1570ef", "Delta-12": "#0e9384", "Gamma-6": "#dc6803", BENCHMARK: "#98a2b3"}
QUE_INVIERTE = {
    "Sigma-6": "Acciones chilenas",
    "Delta-12": "Acciones chilenas",
    "Gamma-6": "Acciones de EE.UU. (en pesos)",
    BENCHMARK: "La bolsa chilena completa",
}
HISTORICAL = ROOT / "data" / "historical_model_nav.csv"


def pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}%}".replace(".", ",")


def _signed(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return ("+" if value >= 0 else "") + pct(value)


def _metrics(values: pd.Series, dates: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(values, errors="coerce")
    keep = values.notna()
    values, dates = values[keep], pd.to_datetime(dates[keep])
    if len(values) < 2 or values.iloc[0] <= 0:
        return {"return": None, "cagr": None, "vol": None, "mdd": None, "positive_months": None, "last_year": None}
    returns = values.pct_change().dropna()
    years = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1 / 365.25)
    monthly = pd.Series(values.to_numpy(), index=dates).resample("ME").last().pct_change(fill_method=None).dropna()
    drawdown = values / values.cummax() - 1
    indexed = pd.Series(values.to_numpy(), index=dates)
    one_year_ago = dates.iloc[-1] - pd.DateOffset(years=1)
    window = indexed.loc[indexed.index >= one_year_ago]
    last_year = window.iloc[-1] / window.iloc[0] - 1 if len(window) > 1 and dates.iloc[0] <= one_year_ago else None
    return {
        "return": values.iloc[-1] / values.iloc[0] - 1,
        "cagr": (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1 if years >= .25 else None,
        "vol": returns.std() * np.sqrt(252) if len(returns) > 2 else None,
        "mdd": drawdown.min(),
        "positive_months": (monthly > 0).mean() if len(monthly) else None,
        "last_year": last_year,
    }


def is_continuous(values: pd.Series, limit: float = .25) -> bool:
    """Descarta una serie con saltos imposibles entre dos valoraciones.

    El cambio de proveedor del IPSA en julio de 2026 encadenó un salto de un día
    sobre el valor acumulado anterior. Una comparación construida sobre eso sería
    falsa, así que el informe prefiere callar y avisar antes que publicarla.
    """
    series = pd.to_numeric(values, errors="coerce").dropna()
    if len(series) < 3:
        return True
    return bool(series.pct_change(fill_method=None).dropna().abs().max() <= limit)


def _series_metrics(frame: pd.DataFrame) -> dict[str, dict]:
    return {name: _metrics(frame[name], frame["date"]) if name in frame else _metrics(pd.Series(dtype=float), pd.Series(dtype=float)) for name in SERIES}


def _chart(frame: pd.DataFrame) -> str:
    """Dibuja la evolución de los últimos 5 años y devuelve el bloque HTML."""
    if HISTORICAL.exists():
        data = pd.read_csv(HISTORICAL, parse_dates=["date"]).rename(columns={"IPSA Total Return": BENCHMARK}).sort_values("date")
    else:
        data = frame.copy()
    names = [name for name in SERIES if name in data and pd.to_numeric(data[name], errors="coerce").notna().sum() > 1]
    if len(data) < 2 or not names:
        return '<p class="muted">El gráfico aparecerá cuando haya al menos dos fechas de seguimiento.</p>'
    window = data.loc[data["date"] >= data["date"].max() - pd.DateOffset(years=5), ["date", *names]].copy()
    normalized = window[names].apply(pd.to_numeric, errors="coerce")
    for name in names:
        valid = normalized[name].dropna()
        normalized[name] = normalized[name] / valid.iloc[0] * 100 if len(valid) else np.nan

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output = ROOT / "reports" / "historical_performance.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10, 4.6), dpi=150)
    for name in names:
        series = normalized[name]
        width = 3.2 if name == CONJUNTO else 1.8
        axis.plot(window["date"], series, label=name, color=COLORS[name], linewidth=width)
        valid = series.dropna()
        if len(valid):
            axis.annotate(f"{valid.iloc[-1]:,.0f}".replace(",", "."), (window.loc[valid.index[-1], "date"], valid.iloc[-1]), xytext=(6, 0), textcoords="offset points", color=COLORS[name], weight="bold", va="center", fontsize=9)
    axis.axhline(100, color="#98a2b3", linewidth=1, linestyle="--")
    axis.set_title("Si hubieras puesto $100 hace 5 años, hoy tendrías…", loc="left", weight="bold")
    axis.grid(True, color="#eceff3", linewidth=.7)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(frameon=False, ncol=len(names), loc="upper left", fontsize=9)
    figure.tight_layout()
    figure.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return f'''<img src="cid:historical_performance" alt="Evolución de las estrategias en los últimos 5 años" style="display:block;width:100%;max-width:900px;height:auto">
    <p class="muted">Desde {window.date.min():%m-%Y} hasta {window.date.max():%m-%Y}. Los años anteriores a la puesta en marcha se calcularon aplicando las mismas reglas hacia atrás.</p>'''


def _orders(moves: pd.DataFrame, strategy: str) -> list[str]:
    if moves is None or moves.empty:
        return []
    labels = {"ENTRA": "Comprar", "SALE": "Vender", "AUMENTA": "Aumentar", "REDUCE": "Reducir"}
    rows = []
    for record in moves.to_dict("records"):
        action = str(record.get("action", ""))
        if action not in labels:
            continue
        weight = "toda la posición" if action == "SALE" else pct(float(record.get("target_weight") or 0))
        rows.append(f'<tr><td><strong>{labels[action]}</strong></td><td>{escape(str(record["ticker"]))}</td><td>{escape(strategy)}</td><td>{weight}</td></tr>')
    return rows


def _positions(portfolio: pd.DataFrame, currency: str = "$") -> str:
    if portfolio is None or portfolio.empty:
        return '<p class="muted">Sin posiciones abiertas.</p>'
    rows = []
    for record in portfolio.to_dict("records"):
        entry = pd.to_datetime(record.get("opened_at"), errors="coerce")
        gain = record.get("open_return")
        gain_text = _signed(float(gain)) if pd.notna(gain) else "—"
        color = "" if gain_text == "—" else ' class="up"' if float(gain) >= 0 else ' class="down"'
        price = record.get("current_price")
        price_text = f"{currency} {float(price):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(price) else "—"
        rows.append(f'<tr><td>{escape(str(record["ticker"]))}</td><td>{pct(float(record["target_weight"]))}</td><td>{entry:%d-%m-%Y}</td><td>{price_text}</td><td{color}>{gain_text}</td></tr>' if pd.notna(entry) else f'<tr><td>{escape(str(record["ticker"]))}</td><td>{pct(float(record["target_weight"]))}</td><td>—</td><td>{price_text}</td><td{color}>{gain_text}</td></tr>')
    return f'<table><thead><tr><th>Acción</th><th>Cuánto pesa</th><th>Comprada el</th><th>Precio hoy</th><th>Va ganando</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'


def build_public_report(
    as_of: pd.Timestamp,
    sigma: pd.DataFrame,
    delta: pd.DataFrame,
    sigma_moves: pd.DataFrame,
    delta_moves: pd.DataFrame,
    coverage: pd.DataFrame,
    errors: pd.DataFrame,
    history: pd.DataFrame,
    gamma: pd.DataFrame | None = None,
    gamma_moves: pd.DataFrame | None = None,
) -> tuple[str, str]:
    gamma = gamma if gamma is not None else pd.DataFrame(columns=["ticker", "target_weight"])
    gamma_moves = gamma_moves if gamma_moves is not None else pd.DataFrame(columns=["ticker", "action", "target_weight"])
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"])
    metrics = _series_metrics(history)
    portfolios = {"Sigma-6": sigma, "Delta-12": delta, "Gamma-6": gamma}
    moves = {"Sigma-6": sigma_moves, "Delta-12": delta_moves, "Gamma-6": gamma_moves}

    orders = [row for name in STRATEGIES for row in _orders(moves[name], name)]
    orders_block = (
        f'<table><thead><tr><th>Qué hacer</th><th>Acción</th><th>Estrategia</th><th>Cuánto</th></tr></thead><tbody>{"".join(orders)}</tbody></table>'
        if orders else '<p class="calm">No hay nada que comprar ni vender esta semana. Las carteras siguen igual.</p>'
    )

    conjunto = metrics[CONJUNTO]
    headline = _signed(conjunto["return"])
    benchmark_usable = BENCHMARK in history and is_continuous(history[BENCHMARK])
    versus = conjunto["return"] - metrics[BENCHMARK]["return"] if benchmark_usable and conjunto["return"] is not None and metrics[BENCHMARK]["return"] is not None else None

    summary_rows = []
    for name in ([CONJUNTO, *STRATEGIES, BENCHMARK] if benchmark_usable else [CONJUNTO, *STRATEGIES]):
        m = metrics[name]
        invierte = "Un tercio en cada estrategia" if name == CONJUNTO else QUE_INVIERTE[name]
        cuantas = "—" if name in {CONJUNTO, BENCHMARK} else str(len(portfolios[name]))
        strong = ' class="row-strong"' if name == CONJUNTO else ""
        summary_rows.append(f'<tr{strong}><td>{name}</td><td>{invierte}</td><td>{_signed(m["return"])}</td><td>{_signed(m["last_year"])}</td><td>{pct(m["mdd"])}</td><td>{cuantas}</td></tr>')

    problems = []
    if len(errors):
        problems.append(f"{len(errors)} recomendaciones nuevas no se pudieron usar porque venían incompletas.")
    if not benchmark_usable:
        problems.append("La serie del IPSA tiene un salto y quedó fuera de las comparaciones hasta corregirla.")
    if len(coverage) and (coverage.status != "OK").any():
        problems.append(f"{int((coverage.status != 'OK').sum())} instrumentos sin datos suficientes esta semana.")
    problems_block = f'<div class="warn"><strong>Revisar:</strong> {" ".join(problems)}</div>' if problems else '<p class="calm">Todos los datos llegaron completos.</p>'

    positions_blocks = "".join(
        f'<h3>{name} · {QUE_INVIERTE[name]}</h3>{_positions(portfolios[name])}'
        for name in STRATEGIES
    )

    html = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
    body{{margin:0;background:#f2f4f7;font:15px/1.5 -apple-system,Segoe UI,Arial,sans-serif;color:#1d2939}}
    .wrap{{max-width:760px;margin:auto;background:#fff}}
    .head{{padding:26px 30px;background:#101828;color:#fff}}.brand{{font-size:24px;font-weight:700}}.sub{{margin-top:4px;color:#c8cfda;font-size:14px}}
    section{{padding:24px 30px;border-bottom:1px solid #eaecf0}}
    h2{{margin:0 0 6px;font-size:18px;color:#101828}}h3{{margin:20px 0 8px;font-size:15px;color:#344054}}
    .lead{{font-size:15px;color:#475467;margin:0 0 16px}}
    .hero{{font-size:42px;font-weight:700;line-height:1.1;margin:6px 0}}.hero.up{{color:#067647}}.hero.down{{color:#b42318}}
    table{{width:100%;border-collapse:collapse;margin-top:6px}}
    th,td{{padding:9px 6px;border-bottom:1px solid #eaecf0;text-align:right;font-size:14px}}
    th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}
    th{{background:#f9fafb;color:#475467;font-weight:600}}
    .row-strong td{{font-weight:700;background:#f8fafc}}
    .up{{color:#067647}}.down{{color:#b42318}}
    .muted{{color:#667085;font-size:12px}}.calm{{color:#475467;background:#f0f9f4;padding:11px 13px;border-radius:8px;margin:6px 0 0}}
    .warn{{background:#fffaeb;border-left:4px solid #f79009;padding:11px 13px;border-radius:0 8px 8px 0}}
    .legend{{display:flex;gap:14px;flex-wrap:wrap;margin:0 0 10px;font-size:13px;color:#475467}}
    .legend i{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}
    .foot{{padding:20px 30px;color:#667085;font-size:12px}}
    @media(max-width:640px){{section,.head,.foot{{padding-left:16px;padding-right:16px}}th,td{{font-size:13px}}.hero{{font-size:34px}}}}
    </style></head><body><main class="wrap">
    <header class="head"><div class="brand">AlphaData</div><div class="sub">Informe semanal · {as_of:%d-%m-%Y}</div></header>

    <section><h2>Cómo va tu dinero</h2>
    <p class="lead">Poniendo la misma cantidad en cada una de las tres estrategias, desde que empezó el seguimiento llevas:</p>
    <div class="hero {'up' if (conjunto['return'] or 0) >= 0 else 'down'}">{headline}</div>
    <p class="lead">{'Eso es ' + _signed(versus) + ' comparado con haber invertido en la bolsa chilena completa.' if versus is not None else 'La comparación con la bolsa chilena aparecerá cuando su serie esté completa.'}</p>
    </section>

    <section><h2>Qué hay que hacer esta semana</h2>
    {orders_block}
    </section>

    <section><h2>Cada estrategia por separado</h2>
    <table><thead><tr><th>Estrategia</th><th>En qué invierte</th><th>Desde el inicio</th><th>Último año</th><th>Peor caída</th><th>Acciones</th></tr></thead>
    <tbody>{''.join(summary_rows)}</tbody></table>
    <p class="muted"><strong>Peor caída:</strong> lo máximo que llegó a bajar desde su punto más alto antes de recuperarse. Mientras más chica, más tranquilo el camino.</p>
    </section>

    <section><h2>Evolución</h2>{_chart(history)}</section>

    <section><h2>Qué tienes comprado hoy</h2>
    {positions_blocks}
    <p class="muted">Todos los precios están en pesos. Las acciones de Gamma-6 se compran en Chile como CDV, así que su resultado ya incluye el efecto del tipo de cambio.</p>
    </section>

    <section><h2>Estado de los datos</h2>{problems_block}</section>

    <footer class="foot">Esto es un seguimiento simulado: las operaciones no se ejecutan con dinero real. Los resultados anteriores a la puesta en marcha se calcularon aplicando las mismas reglas hacia atrás y no garantizan resultados futuros. No es una recomendación de inversión. La metodología y sus parámetros son información reservada.</footer>
    </main></body></html>'''

    lines = [
        "# AlphaData — informe semanal",
        "",
        f"**Fecha:** {as_of:%d-%m-%Y}",
        "",
        f"**Conjunto (un tercio en cada estrategia): {headline} desde el inicio.**",
        "",
        "## Qué hacer esta semana",
        "",
    ]
    if orders:
        labels = {"ENTRA": "Comprar", "SALE": "Vender", "AUMENTA": "Aumentar", "REDUCE": "Reducir"}
        for name in STRATEGIES:
            frame = moves[name]
            if frame is None or frame.empty:
                continue
            for record in frame.to_dict("records"):
                if str(record.get("action")) in labels:
                    detail = "toda la posición" if str(record["action"]) == "SALE" else pct(float(record.get("target_weight") or 0))
                    lines.append(f"- {labels[str(record['action'])]} {record['ticker']} ({name}) — {detail}")
    else:
        lines.append("- Sin cambios: las carteras siguen igual.")
    lines += ["", "## Cada estrategia", ""]
    for name in [CONJUNTO, *STRATEGIES, BENCHMARK]:
        lines.append(f"- {name}: {_signed(metrics[name]['return'])} desde el inicio; peor caída {pct(metrics[name]['mdd'])}.")
    lines += ["", "El informe HTML incluye el gráfico y las carteras. La metodología y sus parámetros son información reservada.", ""]
    return "\n".join(lines), html
