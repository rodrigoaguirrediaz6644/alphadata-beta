from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

CONJUNTO = "Conjunto AlphaData"
STRATEGIES = ["Sigma-6", "Delta-12", "Gamma-6", "Oro"]
BENCHMARK = "IPSA TR"
SERIES = [CONJUNTO, *STRATEGIES, BENCHMARK]
COLORS = {CONJUNTO: "#101828", "Sigma-6": "#1570ef", "Delta-12": "#0e9384", "Gamma-6": "#dc6803", "Oro": "#ca8504", BENCHMARK: "#98a2b3"}
QUE_INVIERTE = {
    "Sigma-6": "Acciones chilenas",
    "Delta-12": "Acciones chilenas",
    "Gamma-6": "Acciones de EE.UU. (en pesos)",
    "Oro": "Oro, como seguro del conjunto",
    BENCHMARK: "La bolsa chilena completa",
}
HISTORICAL = ROOT / "data" / "reconstruccion_historica.csv"
from src.nav_historico import LIMITE_CONCENTRACION  # noqa: E402  (el límite es del modelo, no del informe)
# Las pruebas lo redirigen a un directorio temporal. Sin eso, correr la suite
# sobrescribe los gráficos publicados con los de un fixture sintético, y lo que
# queda commiteado es una curva que no existió.
DIRECTORIO_GRAFICOS = ROOT / "reports"


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


def _dibujar(data: pd.DataFrame, nombres: list[str], titulo: str, archivo: str,
             pie: str) -> str:
    """Dibuja una serie de NAV y devuelve el bloque HTML."""
    if len(data) < 2 or not nombres:
        return ""
    ventana = data.loc[data["date"] >= data["date"].max() - pd.DateOffset(years=5), ["date", *nombres]].copy()
    normalizado = ventana[nombres].apply(pd.to_numeric, errors="coerce")
    for nombre in nombres:
        validos = normalizado[nombre].dropna()
        normalizado[nombre] = normalizado[nombre] / validos.iloc[0] * 100 if len(validos) else np.nan

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    salida = DIRECTORIO_GRAFICOS / archivo
    salida.parent.mkdir(parents=True, exist_ok=True)
    figura, eje = plt.subplots(figsize=(10, 4.6), dpi=150)
    for nombre in nombres:
        serie = normalizado[nombre]
        eje.plot(ventana["date"], serie, label=nombre, color=COLORS[nombre],
                 linewidth=3.2 if nombre == CONJUNTO else 1.8)
        validos = serie.dropna()
        if len(validos):
            eje.annotate(f"{validos.iloc[-1]:,.0f}".replace(",", "."),
                         (ventana.loc[validos.index[-1], "date"], validos.iloc[-1]),
                         xytext=(6, 0), textcoords="offset points", color=COLORS[nombre],
                         weight="bold", va="center", fontsize=9)
    eje.axhline(100, color="#98a2b3", linewidth=1, linestyle="--")
    eje.set_title(titulo, loc="left", weight="bold")
    eje.grid(True, color="#eceff3", linewidth=.7)
    eje.spines[["top", "right"]].set_visible(False)
    eje.legend(frameon=False, ncol=len(nombres), loc="upper left", fontsize=9)
    figura.tight_layout()
    figura.savefig(salida, bbox_inches="tight", facecolor="white")
    plt.close(figura)
    # El `src` apunta al archivo, no a un `cid`. Así el informe se ve completo
    # abriendo reports/latest_report.html desde cualquier parte; el correo lo
    # reescribe a `cid:` al armar el adjunto, que es donde esa forma sí sirve.
    return (f'<img src="{archivo}" alt="{titulo}" '
            'style="display:block;width:100%;max-width:900px;height:auto">'
            f'<p class="muted">{pie}</p>')


def _series_presentes(data: pd.DataFrame) -> list[str]:
    return [n for n in SERIES if n in data and pd.to_numeric(data[n], errors="coerce").notna().sum() > 1]


def _chart(frame: pd.DataFrame, benchmark_usable: bool = True) -> str:
    """Dos gráficos separados: el seguimiento en vivo y la reconstrucción.

    **No se encadenan, y la separación es estructural y no visual.** Son dos
    archivos distintos —`strategy_nav.csv` y `reconstruccion_historica.csv`—
    que se leen por separado y se dibujan por separado. Antes se pegaban en
    memoria escalando una sobre la otra, y eso fue lo que hizo que un +30%
    inventado se leyera como resultado. Un corte dibujado se borra; dos
    gráficos con dos títulos no se juntan solos.
    """
    vivo = frame.copy()
    vivo["date"] = pd.to_datetime(vivo["date"])
    nombres_vivo = [n for n in _series_presentes(vivo) if n != BENCHMARK or benchmark_usable]
    bloques = []
    if len(vivo) >= 2 and nombres_vivo:
        bloques.append(_dibujar(vivo, nombres_vivo, "Seguimiento en vivo", "seguimiento_vivo.png",
                                f"Desde el {vivo.date.min():%d-%m-%Y}, cuando empezó esta serie."))
    else:
        bloques.append(f'<p class="muted">El seguimiento en vivo empezó el '
                       f'{vivo.date.min():%d-%m-%Y}; el gráfico aparece con la segunda jornada.</p>')

    if HISTORICAL.exists():
        recon = pd.read_csv(HISTORICAL, parse_dates=["date"]).rename(
            columns={"IPSA Total Return": BENCHMARK}).sort_values("date")
        nombres = _series_presentes(recon)
        if nombres:
            bloques.append("<h3>Reconstrucción</h3>" + _dibujar(
                recon, nombres, "Aplicando las mismas reglas hacia atrás", "reconstruccion.png",
                f"De {recon.date.min():%m-%Y} a {recon.date.max():%m-%Y}. Es una serie distinta "
                "de la de arriba y no se encadena con ella."))
    return "".join(bloques)


def _precio(valor, moneda: str) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{moneda} {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _positions(portfolio: pd.DataFrame, currency: str = "$") -> str:
    """Qué hay comprado, cuántos pesos es, desde cuándo y cómo va.

    El precio de entrada va al lado del de hoy a propósito: sin él, «va
    ganando 22,9%» es un número que el lector tiene que creer. Con los dos
    precios a la vista, lo puede verificar de memoria.

    Y cuando hubo dividendo de por medio, la columna dice cuántos pesos por
    acción llegaron a la cuenta. Nueve de veinte filas lo tienen: son
    demasiadas para una nota al pie, y el monto es información que igual se
    quiere. La variación queda algo por encima de sumarlo a mano porque
    reinvierte el dividendo el día en que se pagó; eso va dicho en una línea
    bajo la tabla, no fila por fila.
    """
    if portfolio is None or portfolio.empty:
        return '<p class="muted">Sin posiciones abiertas.</p>'
    hay_montos = "monto_clp" in portfolio and portfolio["monto_clp"].notna().any()
    hay_dividendos = "dividendos_clp" in portfolio and portfolio["dividendos_clp"].notna().any()
    hay_deriva = "peso_real" in portfolio and portfolio["peso_real"].notna().any()
    hay_caducidad = "caduca" in portfolio and portfolio["caduca"].notna().any()
    rows = []
    for record in portfolio.to_dict("records"):
        entry = pd.to_datetime(record.get("opened_at"), errors="coerce")
        fecha = f"{entry:%d-%m-%Y}" if pd.notna(entry) else "—"
        gain = record.get("open_return")
        gain_text = _signed(float(gain)) if pd.notna(gain) else "—"
        color = "" if gain_text == "—" else ' class="up"' if float(gain) >= 0 else ' class="down"'
        if gain_text != "—" and record.get("con_dividendo"):
            gain_text += " *"
        celdas = [escape(str(record["ticker"]))]
        if hay_montos:
            celdas.append(_pesos(record.get("monto_clp"), currency))
        celdas.append(pct(float(record["target_weight"])))
        if hay_deriva:
            celdas.append(_deriva(record.get("peso_real"), record.get("target_weight")))
        celdas += [fecha,
                   _precio(record.get("entry_price"), currency),
                   _precio(record.get("current_price"), currency)]
        if hay_dividendos:
            celdas.append(_precio(record.get("dividendos_clp"), currency))
        if hay_caducidad:
            celdas.append(_caducidad(record.get("caduca"), record.get("dias_para_caducar")))
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in celdas)
                    + f'<td{color}>{gain_text}</td></tr>')
    cabecera = (["Acción"]
                + (["Cuánto invertir"] if hay_montos else [])
                + ["Peso de entrada"]
                + (["Peso hoy"] if hay_deriva else [])
                + ["Comprada el", "Precio de entrada", "Precio hoy"]
                + (["Dividendos cobrados"] if hay_dividendos else [])
                + (["Recomendación vigente hasta"] if hay_caducidad else [])
                + ["Va ganando"])
    return ("<table><thead><tr>" + "".join(f"<th>{c}</th>" for c in cabecera)
            + f'</tr></thead><tbody>{"".join(rows)}</tbody></table>')


def _deriva(real, objetivo, limite: float | None = LIMITE_CONCENTRACION) -> str:
    """El peso al que llegó la posición, contra el que el modelo supone.

    El peso de referencia sólo aplica al entrar: la política dice dejar correr
    los pesos y operar nada más que entradas y salidas, así que el peso real es
    el único que existe después. La columna no es una instrucción pendiente.
    Se marca cuando la diferencia pasa de dos puntos, que es donde deja de ser
    ruido.

    Y avisa cuando la posición se acerca al límite de concentración, que sí es
    una instrucción: al pasarlo se recorta hasta el límite en la revisión
    siguiente.
    """
    if real is None or pd.isna(real) or objetivo is None or pd.isna(objetivo):
        return "—"
    real = float(real)
    texto = pct(real)
    if limite is not None and real >= limite:
        return f'<strong class="down">{texto}</strong> · se recorta al {pct(limite, 0)}'
    if limite is not None and real >= limite - .03:
        return f"<strong>{texto}</strong> · cerca del {pct(limite, 0)}"
    return f"<strong>{texto}</strong>" if abs(real - float(objetivo)) > .02 else texto


def _vigencia(vigencia: dict | None) -> str:
    """Qué nombres necesitan recomendación nueva y antes de cuándo.

    Y si la más reciente pasó el umbral, que la estrategia está detenida. Un mes
    saltado tiene que ser ruidoso y no silencioso: todo lo que este sistema
    reparó fue algo que dejó de actualizarse sin avisar.
    """
    if not vigencia or vigencia.get("dias") is None:
        return ""
    dias, umbral = int(vigencia["dias"]), int(vigencia["umbral"])
    renovar = vigencia.get("renovar") or []
    lista = "".join(
        f'<li><strong>{escape(str(r["ticker"]))}</strong> — antes del '
        f'{pd.to_datetime(r["caduca"]):%d-%m-%Y}'
        + (f' (en {int(r["dias_para_caducar"])} días)' if pd.notna(r.get("dias_para_caducar")) else "")
        + "</li>"
        for r in renovar)
    if vigencia.get("detenida"):
        return ('<div class="warn"><strong>Sigma-6 está detenida.</strong> La recomendación más '
                f'reciente tiene {dias} días y el límite son {umbral}. La estrategia conserva su '
                'cartera y no abre posiciones nuevas; tampoco vende, porque una venta disparada por '
                'la falta del dato no es una señal. Se reanuda sola en cuanto entren recomendaciones '
                f'nuevas.{("<p>Necesitan recomendación nueva:</p><ul>" + lista + "</ul>") if lista else ""}'
                "</div>")
    quedan = umbral - dias
    cuerpo = (f'<p class="muted">La recomendación más reciente tiene {dias} días. Si llega a '
              f'{umbral} sin que entren nuevas, Sigma-6 conserva la cartera y deja de abrir '
              f'posiciones: quedan {quedan} días.</p>')
    if lista:
        cuerpo += f"<p class=\"muted\">Necesitan recomendación nueva:</p><ul>{lista}</ul>"
    return cuerpo


def _caducidad(fecha, dias) -> str:
    """Hasta cuándo vale la recomendación que sostiene la posición.

    Sigma-6 sólo compra lo que sus recomendaciones sostienen, y una
    recomendación caduca al año. Con el flujo de Credicorp detenido desde el
    22-07-2026, ése es el reloj que va a ir vaciando la estrategia: VAPORES el
    24-11-2026 y el resto hasta julio de 2027. Una salida por calendario es
    información de ejecución.

    El tope de tenencia de 365 días, que esta columna mostraba antes, salió el
    21-09-2026.
    """
    fecha = pd.to_datetime(fecha, errors="coerce")
    if pd.isna(fecha):
        return "—"
    texto = f"{fecha:%d-%m-%Y}"
    if dias is not None and pd.notna(dias) and int(dias) <= 90:
        return f"<strong>{texto}</strong> · en {int(dias)} días"
    return texto


def _pesos(valor, moneda: str) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{moneda} {float(valor):,.0f}".replace(",", ".")


def _caja(portfolio: pd.DataFrame, capital_por_pieza: float | None) -> str:
    """Lo que queda sin invertir en una pieza.

    Sigma-6 sólo compra lo que Credicorp recomienda y el momentum confirma, y
    topa cada nombre en 10%: con cinco posiciones deja la mitad en caja. En
    porcentajes eso pasaba inadvertido; en pesos son $2.500.000 quietos y hay
    que decirlo.
    """
    if portfolio is None or portfolio.empty or not capital_por_pieza:
        return ""
    libre = 1 - float(portfolio.target_weight.sum())
    if libre <= .005:
        return ""
    return (f'<p class="muted">En caja: {_pesos(libre * capital_por_pieza, "$")} '
            f'({pct(libre)} de la pieza), porque no hay más nombres que cumplan las condiciones.</p>')


def _movimientos(movimientos: pd.DataFrame | None) -> str:
    """Qué cambió desde el informe anterior. No desde la fecha de señal.

    Tres de las cuatro piezas son mensuales, así que la mayoría de las semanas
    esto viene vacío. Un bloque vacío se lee como informe roto: cuando no hay
    nada, hay que decirlo con todas sus letras.
    """
    if movimientos is None or movimientos.empty:
        return ('<p class="calm"><strong>Sin cambios desde el informe anterior.</strong> '
                'Las carteras de abajo siguen tal cual.</p>')
    filas = []
    for r in movimientos.to_dict("records"):
        fecha = pd.to_datetime(r.get("fecha"), errors="coerce")
        desde = f"desde el {fecha:%d-%m-%Y}" if pd.notna(fecha) else "—"
        filas.append(f'<tr><td><strong>{escape(str(r["accion"]).capitalize())}</strong></td>'
                     f'<td>{escape(str(r["instrumento"]))}</td>'
                     f'<td>{escape(str(r["estrategia"]))}</td><td>{desde}</td></tr>')
    return ('<table><thead><tr><th>Qué hacer</th><th>Acción</th><th>Estrategia</th>'
            f'<th>En cartera</th></tr></thead><tbody>{"".join(filas)}</tbody></table>')


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
    oro: pd.DataFrame | None = None,
    oro_moves: pd.DataFrame | None = None,
    movimientos: pd.DataFrame | None = None,
    capital_por_pieza: float | None = None,
    vigencia: dict | None = None,
) -> tuple[str, str]:
    vacio_cartera = pd.DataFrame(columns=["ticker", "target_weight"])
    vacio_movs = pd.DataFrame(columns=["ticker", "action", "target_weight"])
    gamma = gamma if gamma is not None else vacio_cartera
    gamma_moves = gamma_moves if gamma_moves is not None else vacio_movs
    oro = oro if oro is not None else vacio_cartera
    oro_moves = oro_moves if oro_moves is not None else vacio_movs
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"])
    metrics = _series_metrics(history)
    portfolios = {"Sigma-6": sigma, "Delta-12": delta, "Gamma-6": gamma, "Oro": oro}
    moves = {"Sigma-6": sigma_moves, "Delta-12": delta_moves, "Gamma-6": gamma_moves, "Oro": oro_moves}

    # Dos bloques separados, que el informe mezcló desde siempre bajo un mismo
    # título: lo que cambió esta semana no es lo mismo que lo que hay que
    # comprar para entrar hoy. Confundirlos es lo que produjo un «Comprar INTC»
    # en la misma página en que la tabla decía «comprada el 30-09-2025».
    orders_block = _movimientos(movimientos)
    reparto = (f"Con un capital de {_pesos(capital_por_pieza * len(STRATEGIES), '$')} repartido en cuartos, "
               f"a cada pieza le tocan {_pesos(capital_por_pieza, '$')}. La columna dice cuántos pesos va "
               "en cada acción."
               if capital_por_pieza else
               "El peso de entrada es dentro de su propia pieza, y cada pieza es un cuarto del total.")

    conjunto = metrics[CONJUNTO]
    headline = _signed(conjunto["return"])
    benchmark_usable = BENCHMARK in history and is_continuous(history[BENCHMARK])
    versus = conjunto["return"] - metrics[BENCHMARK]["return"] if benchmark_usable and conjunto["return"] is not None and metrics[BENCHMARK]["return"] is not None else None

    # Una sola lista para la tabla y para el texto plano: cuando estaban
    # separadas, el markdown siguió publicando el IPSA roto que el HTML ya
    # ocultaba.
    resumen = [CONJUNTO, *STRATEGIES, BENCHMARK] if benchmark_usable else [CONJUNTO, *STRATEGIES]

    summary_rows = []
    for name in resumen:
        m = metrics[name]
        invierte = "Partes iguales en las cuatro piezas" if name == CONJUNTO else QUE_INVIERTE[name]
        cuantas = "—" if name in {CONJUNTO, BENCHMARK} else str(len(portfolios[name]))
        strong = ' class="row-strong"' if name == CONJUNTO else ""
        summary_rows.append(f'<tr{strong}><td>{name}</td><td>{invierte}</td><td>{_signed(m["return"])}</td><td>{_signed(m["last_year"])}</td><td>{pct(m["mdd"])}</td><td>{cuantas}</td></tr>')

    problems = []
    aviso_vigencia = _vigencia(vigencia)
    if len(errors):
        problems.append(f"{len(errors)} recomendaciones nuevas no se pudieron usar porque venían incompletas.")
    if not benchmark_usable:
        problems.append("La serie del IPSA tiene un salto y quedó fuera de las comparaciones hasta corregirla.")
    if len(coverage) and (coverage.status != "OK").any():
        problems.append(f"{int((coverage.status != 'OK').sum())} instrumentos sin datos suficientes esta semana.")
    problems_block = f'<div class="warn"><strong>Revisar:</strong> {" ".join(problems)}</div>' if problems else '<p class="calm">Todos los datos llegaron completos.</p>'

    inicio = pd.to_datetime(history["date"]).min()
    # La nota del asterisco sólo se imprime si alguna fila lo lleva.
    con_dividendo = any(bool(frame["con_dividendo"].any()) for frame in portfolios.values()
                        if frame is not None and "con_dividendo" in frame and len(frame))
    con_monto = any(bool(frame["dividendos_clp"].notna().any()) for frame in portfolios.values()
                    if frame is not None and "dividendos_clp" in frame and len(frame))
    notas = []
    if con_monto:
        notas.append('<p class="muted"><strong>Dividendos cobrados</strong> son pesos por acción que ya'
                     ' llegaron a la cuenta. Sumarlos al precio de hoy da algo menos que «va ganando»,'
                     ' porque la variación los reinvierte el día en que se pagaron.</p>')
    if con_dividendo:
        notas.append('<p class="muted"><strong>*</strong> Esa acción repartió dividendos que la variación'
                     ' incluye, pero que no están itemizados: la tabla de dividendos sólo cubre el'
                     ' mercado chileno.</p>')
    nota_dividendos = "".join(notas)

    positions_blocks = "".join(
        f'<h3>{name} · {QUE_INVIERTE[name]}</h3>{_positions(portfolios[name])}{_caja(portfolios[name], capital_por_pieza)}'
        for name in STRATEGIES if name in portfolios
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
    <p class="lead">Poniendo la misma cantidad en cada una de las cuatro piezas, desde que empezó el seguimiento llevas:</p>
    <div class="hero {'up' if (conjunto['return'] or 0) >= 0 else 'down'}">{headline}</div>
    <p class="lead">{'Eso es ' + _signed(versus) + ' comparado con haber invertido en la bolsa chilena completa.' if versus is not None else 'La comparación con la bolsa chilena aparecerá cuando su serie esté completa.'}</p>
    </section>

    <section><h2>Qué cambió desde el informe anterior</h2>
    {orders_block}
    </section>

    <section><h2>Cada estrategia por separado</h2>
    <table><thead><tr><th>Estrategia</th><th>En qué invierte</th><th>Desde el {inicio:%d-%m-%Y}</th><th>Último año</th><th>Peor caída</th><th>Acciones</th></tr></thead>
    <tbody>{''.join(summary_rows)}</tbody></table>
    <p class="muted"><strong>Peor caída:</strong> lo máximo que llegó a bajar desde su punto más alto antes de recuperarse. Mientras más chica, más tranquilo el camino.</p>
    </section>

    <section><h2>Evolución</h2>
    <p class="lead">El seguimiento en vivo corre desde el {inicio:%d-%m-%Y}.</p>
    {_chart(history, benchmark_usable)}</section>

    <section><h2>La cartera completa</h2>
    <p class="lead">{reparto}</p>
    {positions_blocks}
    {nota_dividendos}
    <p class="muted"><strong>Va ganando</strong> es cuánto se movió el precio de esa acción desde el día en que se compró, que es distinto del rendimiento de la estrategia desde el {inicio:%d-%m-%Y}: una acción comprada hace ocho meses puede ir muy arriba aunque la estrategia lleve poco medida. Los dos números son correctos y no tienen por qué calzar.</p>
    <p class="muted">Las fechas y los precios de entrada salen de aplicar las reglas a la serie histórica, no de operaciones registradas en vivo: «comprada el 27-02-2026» quiere decir que el modelo la seleccionó ese día y no la ha soltado. Sigma-6 se apoya en recomendaciones externas que tienen fecha de vencimiento: la columna dice hasta cuándo vale la que sostiene cada posición, y cuando vence, la venta cae en la primera revisión semanal posterior.</p>
    <p class="muted">Todos los precios están en pesos. Gamma-6 y el oro se compran en Chile como CDV, así que su resultado ya incluye el efecto del tipo de cambio. El oro no se compra ni se vende por señales: es una posición fija que está para amortiguar las caídas del resto.</p>
    </section>

    <section><h2>Estado de los datos</h2>{aviso_vigencia}{problems_block}</section>

    </main></body></html>'''

    lines = [
        "# AlphaData — informe semanal",
        "",
        f"**Fecha:** {as_of:%d-%m-%Y}",
        "",
        f"**Conjunto (partes iguales en las cuatro piezas): {headline} desde el {inicio:%d-%m-%Y}.**",
        "",
        "## Qué cambió desde el informe anterior",
        "",
    ]
    if movimientos is not None and len(movimientos):
        for record in movimientos.to_dict("records"):
            fecha = pd.to_datetime(record.get("fecha"), errors="coerce")
            desde = f" — en cartera desde el {fecha:%d-%m-%Y}" if pd.notna(fecha) else ""
            lines.append(f"- {str(record['accion']).capitalize()} {record['instrumento']} "
                         f"({record['estrategia']}){desde}")
    else:
        lines.append("- Sin cambios desde el informe anterior. Las carteras siguen tal cual.")
    lines += ["", "## Cada estrategia", ""]
    for name in resumen:
        lines.append(f"- {name}: {_signed(metrics[name]['return'])} desde el {inicio:%d-%m-%Y}; peor caída {pct(metrics[name]['mdd'])}.")
    if not benchmark_usable:
        lines.append("- La comparación con la bolsa chilena no está disponible: la serie del IPSA tiene un salto y quedó fuera hasta corregirla.")
    lines += ["", "El informe HTML incluye el gráfico y las carteras. La metodología y sus parámetros son información reservada.", ""]
    return "\n".join(lines), html
