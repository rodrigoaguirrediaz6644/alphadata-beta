from __future__ import annotations

from html import escape
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SERIES = ["Sigma-6", "Delta-12", "IPSA TR"]
COLORS = {"Sigma-6": "#1570ef", "Delta-12": "#0e9384", "IPSA TR": "#7a5af8"}


def pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}%}"


def _metrics(values: pd.Series, dates: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(values, errors="coerce")
    keep = values.notna()
    values, dates = values[keep], pd.to_datetime(dates[keep])
    if len(values) < 2 or values.iloc[0] <= 0:
        return {"return": None, "cagr": None, "vol": None, "mdd": None, "positive_months": None}
    returns = values.pct_change().dropna()
    years = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1 / 365.25)
    monthly = pd.Series(values.to_numpy(), index=dates).resample("ME").last().pct_change().dropna()
    drawdown = values / values.cummax() - 1
    return {
        "return": values.iloc[-1] / values.iloc[0] - 1,
        "cagr": (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1 if years >= .25 else None,
        "vol": returns.std() * np.sqrt(252) if len(returns) > 2 else None,
        "mdd": drawdown.min(),
        "positive_months": (monthly > 0).mean() if len(monthly) else None,
    }


def _points(values: pd.Series, width: int = 820, height: int = 220) -> str:
    values = pd.to_numeric(values, errors="coerce").interpolate().ffill().bfill()
    if len(values) < 2 or values.isna().all():
        return ""
    lo, hi = float(values.min()), float(values.max())
    span = hi - lo or 1.0
    xs = np.linspace(40, width - 15, len(values))
    ys = 15 + (hi - values.to_numpy()) / span * (height - 40)
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))


def _line_chart(history: pd.DataFrame, drawdown: bool = False) -> str:
    if len(history) < 2:
        return '<div class="empty">El seguimiento gráfico oficial aparecerá cuando existan al menos dos fechas de valoración.</div>'
    data = history.copy().sort_values("date")
    lines = []
    for name in SERIES:
        values = pd.to_numeric(data[name], errors="coerce")
        if drawdown:
            values = values / values.cummax() - 1
        else:
            first = values.dropna().iloc[0] if values.notna().any() else np.nan
            values = values / first * 100 if pd.notna(first) and first else values
        points = _points(values)
        if points:
            lines.append(f'<polyline points="{points}" fill="none" stroke="{COLORS[name]}" stroke-width="3"/>')
    title = "Retrocesos del paper trading" if drawdown else "Evolución del paper trading · base 100"
    return f'''<div class="chart"><div class="chart-title">{title}</div>
    <svg viewBox="0 0 820 220" role="img" aria-label="{title}">
    <line x1="40" y1="20" x2="805" y2="20" class="grid"/><line x1="40" y1="100" x2="805" y2="100" class="grid"/><line x1="40" y1="180" x2="805" y2="180" class="grid"/>{''.join(lines)}</svg></div>'''


def _table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return '<p class="empty">Sin posiciones o movimientos.</p>'
    labels = {"ticker": "Acción", "target_weight": "Peso objetivo", "action": "Movimiento", "change": "Cambio"}
    rows = []
    for record in df[columns].to_dict("records"):
        cells = []
        for column in columns:
            value = record[column]
            if column in {"target_weight", "change"}:
                value = pct(float(value))
            cells.append(f"<td>{escape(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    heads = "".join(f"<th>{labels.get(c, c.replace('_', ' ').title())}</th>" for c in columns)
    return f"<table><thead><tr>{heads}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _historical_references() -> dict[str, dict]:
    path = ROOT / "strategies.v2.json"
    if not path.exists():
        return {}
    config = json.loads(path.read_text(encoding="utf-8"))
    return {item["commercial_name"]: item.get("historical_reference", {}) for item in config.get("strategies", [])}


def build_public_report(
    as_of: pd.Timestamp,
    sigma: pd.DataFrame,
    delta: pd.DataFrame,
    sigma_moves: pd.DataFrame,
    delta_moves: pd.DataFrame,
    coverage: pd.DataFrame,
    errors: pd.DataFrame,
    history: pd.DataFrame,
) -> tuple[str, str]:
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"])
    sigma_cash = 1 - sigma.target_weight.sum() if len(sigma) else 1.0
    delta_cash = 1 - delta.target_weight.sum() if len(delta) else 1.0
    metrics = {name: _metrics(history[name], history["date"]) for name in SERIES}
    refs = _historical_references()

    ref_rows = []
    for name in ["Sigma-6", "Delta-12"]:
        ref = refs.get(name, {})
        ref_rows.append(f"<tr><td>{name}</td><td>{pct(ref.get('total_return'))}</td><td>{pct(ref.get('cagr'))}</td><td>{pct(ref.get('maximum_drawdown'))}</td><td>{ref.get('period') or ref.get('common_comparison_period') or 'Periodo histórico validado'}</td></tr>")
    ref_rows.append('<tr><td>IPSA Total Return</td><td colspan="3">Serie histórica comparativa pendiente de incorporación al registro automático</td><td>—</td></tr>')

    metric_rows = []
    for label, key in [("Rentabilidad acumulada", "return"), ("CAGR", "cagr"), ("Volatilidad anual", "vol"), ("Máximo retroceso", "mdd"), ("Meses positivos", "positive_months")]:
        metric_rows.append("<tr><td>" + label + "</td>" + "".join(f"<td>{pct(metrics[n][key])}</td>" for n in SERIES) + "</tr>")

    legends = "".join(f'<span><i style="background:{COLORS[n]}"></i>{n}</span>' for n in SERIES)
    status = "Completo" if errors.empty and (coverage.status == "OK").all() else "Con observaciones"
    html = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
    body{{margin:0;background:#f5f7fa;font:14px Arial,sans-serif;color:#25364a}}.wrap{{max-width:980px;margin:auto;background:#fff}}.head{{padding:28px 34px;background:#102a43;color:#fff}}.brand{{font-size:25px;font-weight:bold}}.sub{{margin-top:6px;color:#cfe0f1}}section{{padding:24px 34px;border-bottom:1px solid #e4e7ec}}h2{{margin:0 0 16px;color:#102a43;font-size:19px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}}.card,.chart{{border:1px solid #e4e7ec;border-radius:10px;padding:14px}}.big{{font-size:24px;font-weight:bold;margin:8px 0}}.muted,.empty{{color:#667085;font-size:12px}}.legend{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:10px}}.legend i{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}.chart-title{{font-weight:bold;color:#344054}}svg{{width:100%;height:auto}}.grid{{stroke:#e9edf2}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #e4e7ec;text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{background:#f8fafc;color:#475467}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.note{{background:#fff7d6;padding:12px;border-left:4px solid #fdb022}}.foot{{padding:22px 34px;color:#667085;font-size:11px;line-height:1.5}}@media(max-width:700px){{.cards,.two{{grid-template-columns:1fr}}section,.head{{padding-left:18px;padding-right:18px}}}}
    </style></head><body><main class="wrap"><header class="head"><div class="brand">AlphaData</div><div class="sub">Informe de estrategias · {as_of:%d de %m de %Y}</div></header>
    <section><h2>Resumen ejecutivo</h2><div class="cards"><div class="card"><strong>Sigma-6</strong><div class="big">{pct(metrics['Sigma-6']['return'])}</div><div class="muted">Paper trading desde inicio</div><p>{len(sigma)} posiciones · {pct(sigma_cash)} en caja</p></div><div class="card"><strong>Delta-12</strong><div class="big">{pct(metrics['Delta-12']['return'])}</div><div class="muted">Paper trading desde inicio</div><p>{len(delta)} posiciones · {pct(delta_cash)} en caja</p></div><div class="card"><strong>IPSA Total Return</strong><div class="big">{pct(metrics['IPSA TR']['return'])}</div><div class="muted">Benchmark oficial</div><p>Estado de datos: {status}</p></div></div></section>
    <section><h2>Referencia histórica de backtest</h2><p class="muted">Resultados simulados anteriores al paper trading. No representan operaciones reales.</p><table><thead><tr><th>Serie</th><th>Rentabilidad</th><th>CAGR</th><th>Máximo retroceso</th><th>Periodo</th></tr></thead><tbody>{''.join(ref_rows)}</tbody></table></section>
    <section><h2>Seguimiento oficial</h2><div class="legend">{legends}</div>{_line_chart(history)}<br>{_line_chart(history, True)}</section>
    <section><h2>Métricas del paper trading</h2><table><thead><tr><th>Métrica</th><th>Sigma-6</th><th>Delta-12</th><th>IPSA TR</th></tr></thead><tbody>{''.join(metric_rows)}</tbody></table></section>
    <section><div class="two"><div><h2>Sigma-6 · cartera</h2>{_table(sigma,['ticker','target_weight'])}<p><strong>Caja:</strong> {pct(sigma_cash)}</p><h3>Movimientos</h3>{_table(sigma_moves,['ticker','action','target_weight','change'])}</div><div><h2>Delta-12 · cartera</h2>{_table(delta,['ticker','target_weight'])}<p><strong>Caja:</strong> {pct(delta_cash)}</p><h3>Movimientos</h3>{_table(delta_moves,['ticker','action','target_weight','change'])}</div></div></section>
    <section><h2>Control del informe</h2><p>Datos actualizados al {as_of:%d-%m-%Y} · Estado: {status} · Filas rechazadas: {len(errors)} · Cobertura suficiente: {int((coverage.status=='OK').sum())}/{len(coverage)}</p><div class="note"><strong>Información reservada:</strong> este informe comunica resultados, cartera y movimientos. No publica fórmulas, indicadores, parámetros ni reglas de decisión.</div></section>
    <footer class="foot"><strong>Advertencia:</strong> los backtests son simulaciones y el paper trading corresponde a una cartera modelo. No constituyen asesoría personalizada ni garantizan resultados futuros. La rentabilidad personal puede diferir por precios de ejecución, costos e impuestos.</footer></main></body></html>'''

    md = f"""# AlphaData — informe de estrategias\n\n**Fecha de corte:** {as_of:%d-%m-%Y}\n\n## Resumen\n\n- Sigma-6: {len(sigma)} posiciones; caja {pct(sigma_cash)}.\n- Delta-12: {len(delta)} posiciones; caja {pct(delta_cash)}.\n- Estado de datos: {status}.\n\nEl informe HTML contiene las comparaciones, gráficos, carteras y movimientos. La metodología y sus parámetros son información reservada.\n\n> Resultados históricos simulados y paper trading; no constituyen recomendación de inversión ni garantizan resultados futuros.\n"""
    return md, html
