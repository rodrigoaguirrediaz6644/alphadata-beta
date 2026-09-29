from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

CONJUNTO = "Conjunto AlphaData"
# Sigma-6 salió de la asignación el 22-09-2026 y no aparece en el cuerpo del
# informe. Su serie histórica se conserva y se sigue dibujando en la
# reconstrucción, que es historia del proyecto.
STRATEGIES = ["Delta-12", "Gamma-6", "Oro"]
RETIRADAS = ["Sigma-6"]
BENCHMARK = "Mercado chileno"
SERIES = [CONJUNTO, *STRATEGIES, BENCHMARK]
SERIES_RECONSTRUCCION = [CONJUNTO, *STRATEGIES, *RETIRADAS, BENCHMARK]
COLORS = {CONJUNTO: "#101828", "Sigma-6": "#1570ef", "Delta-12": "#0e9384", "Gamma-6": "#dc6803", "Oro": "#ca8504", BENCHMARK: "#98a2b3"}
# Cómo se llaman las series **en lo que se publica**. Adentro —columnas, libro,
# configuración— siguen con su nombre de siempre: cambiar el nombre de una
# columna guardada es reescribir historia por un asunto de presentación.
# «Ipsa» es el índice real (MSCI IPSA Gross en pesos), que la captura diaria
# actualiza sola desde src/indice_ipsa.py. No es la canasta igual peso, que rinde
# unos 6 puntos menos y por eso no puede llevar ese nombre.
NOMBRE_PUBLICO = {"Delta-12": "Delta12", "Gamma-6": "Gamma6", CONJUNTO: "AlphaData", "IPSA": "Ipsa"}
TITULO_GRAFICO = "Desempeño AlphaData últimos 5 años"
ARCHIVO_GRAFICO = "reconstruccion.png"
# AlphaData en rojo y grueso; las demás delgadas y en tonos que no se le
# parezcan. El naranjo y el dorado de antes se confundían con el rojo.
COLORES_GRAFICO = {"AlphaData": "#d92d20", "Delta12": "#1570ef", "Gamma6": "#099250",
                   "Oro": "#eaaa08", "Ipsa": "#98a2b3"}
GROSOR_PRINCIPAL, GROSOR_RESTO = 3, 1


def _publico(texto: str) -> str:
    """Los nombres de las estrategias como se publican, en todo el informe."""
    return texto.replace("Delta-12", "Delta12").replace("Gamma-6", "Gamma6")
QUE_INVIERTE = {
    "Sigma-6": "Acciones chilenas (retirada)",
    "Delta-12": "Acciones chilenas",
    "Gamma-6": "Acciones de EE.UU.",
    "Oro": "ETF de Oro",
    BENCHMARK: "La bolsa chilena completa",
}
HISTORICAL = ROOT / "data" / "reconstruccion_historica.csv"
# Las pruebas lo redirigen a un directorio temporal. Sin eso, correr la suite
# sobrescribe los gráficos publicados con los de un fixture sintético, y lo que
# queda commiteado es una curva que no existió.
DIRECTORIO_GRAFICOS = ROOT / "reports"


def pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}%}".replace(".", ",")


MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


def _fecha_larga(fecha: pd.Timestamp) -> str:
    """«01 de Enero del 2026». Sin `locale`, que en un runner no está puesto."""
    return f"{fecha.day:02d} de {MESES[fecha.month - 1].capitalize()} del {fecha.year}"


def _porcentaje_corto(valor: float) -> str:
    """«37,5%» y «25%»: sin el decimal cuando no dice nada."""
    return f"{valor * 100:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "%"


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


def _suavizar(fechas: pd.Series, valores: pd.Series, pasos: int = 12) -> tuple[list, list]:
    """Una curva suave que pasa por el cierre de cada mes y por el último dato.

    **No es un promedio móvil.** Un promedio desplaza la curva y la hace
    terminar en un valor que no es el de hoy, y el número rotulado al final de
    la línea tiene que ser el mismo de la tabla. Esto toma el cierre de cada
    mes, que son valores reales, y los une con una curva (Catmull-Rom) en vez
    de con rectas. Lo que se pierde es el zigzag diario dentro del mes.
    """
    serie = pd.Series(pd.to_numeric(valores, errors="coerce").to_numpy(),
                      index=pd.to_datetime(fechas)).dropna()
    if len(serie) < 4:
        return list(serie.index), list(serie.to_numpy())
    mensual = serie.groupby(serie.index.to_period("M")).tail(1)
    puntos = pd.concat([serie.iloc[[0]], mensual])
    puntos = puntos[~puntos.index.duplicated(keep="last")].sort_index()
    x = puntos.index.astype("int64").to_numpy(dtype=float)
    y = puntos.to_numpy(dtype=float)
    if len(y) < 4:
        return list(puntos.index), list(y)
    xs, ys = [], []
    for i in range(len(y) - 1):
        p0, p1, p2, p3 = y[max(i - 1, 0)], y[i], y[i + 1], y[min(i + 2, len(y) - 1)]
        for k in range(pasos):
            u = k / pasos
            xs.append(x[i] + (x[i + 1] - x[i]) * u)
            ys.append(.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2
                            + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3))
    xs.append(x[-1])
    ys.append(y[-1])
    return list(pd.to_datetime(np.array(xs).astype("int64"))), ys


def _separar(valores: dict[str, float], minimo: float) -> dict[str, float]:
    """Dónde va el rótulo de cada línea para que dos finales parecidos no se tapen."""
    puestos, anterior = {}, None
    for nombre, valor in sorted(valores.items(), key=lambda par: par[1]):
        anterior = valor if anterior is None else max(valor, anterior + minimo)
        puestos[nombre] = anterior
    return puestos


def _dibujar(data: pd.DataFrame, nombres: list[str], titulo: str, archivo: str,
             pie: str, colores: dict | None = None, principal: str = CONJUNTO,
             suave: bool = False, grosores: tuple[float, float] = (3.2, 1.8),
             años: int | None = 5) -> str:
    """Dibuja una serie de NAV y devuelve el bloque HTML.

    `titulo` es el texto alternativo de la imagen; adentro del gráfico no va
    título, que ya lo lleva la sección.
    """
    colores = colores or COLORS
    if len(data) < 2 or not nombres:
        return ""
    # `años=None`: la serie ya viene recortada por quien la calcula, y recortarla
    # de nuevo podría sacarle el primer día, que es donde vale 100.
    ventana = (data[["date", *nombres]].copy() if años is None else
               data.loc[data["date"] >= data["date"].max() - pd.DateOffset(years=años), ["date", *nombres]].copy())
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
    finales = {}
    for nombre in nombres:
        serie = normalizado[nombre]
        x, y = _suavizar(ventana["date"], serie) if suave else (ventana["date"], serie)
        # La principal se dibuja encima de las demás.
        eje.plot(x, y, label=nombre, color=colores[nombre],
                 linewidth=grosores[0] if nombre == principal else grosores[1],
                 zorder=3 if nombre == principal else 2,
                 solid_capstyle="round", solid_joinstyle="round")
        validos = serie.dropna()
        if len(validos):
            finales[nombre] = (ventana.loc[validos.index[-1], "date"], float(validos.iloc[-1]))
    # El rótulo dice el valor real del último día aunque se corra para no taparse.
    bajo, alto = eje.get_ylim()
    alturas = _separar({n: v for n, (_, v) in finales.items()}, (alto - bajo) * .045)
    for nombre, (fecha, valor) in finales.items():
        eje.annotate(f"{valor:,.0f}".replace(",", "."), (fecha, alturas[nombre]),
                     xytext=(6, 0), textcoords="offset points", color=colores[nombre],
                     weight="bold", va="center", fontsize=9)
    eje.axhline(100, color="#98a2b3", linewidth=1, linestyle="--")
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
            + (f'<p class="muted">{pie}</p>' if pie else ""))


def _series_presentes(data: pd.DataFrame, series: list[str] | None = None) -> list[str]:
    return [n for n in (series or SERIES)
            if n in data and pd.to_numeric(data[n], errors="coerce").notna().sum() > 1]


def _chart(serie: pd.DataFrame | None) -> str:
    """El gráfico de los últimos cinco años, con la misma serie que la tabla.

    Es **un solo gráfico**. El del seguimiento en vivo salió del informe: medía
    desde el 16-09-2026 y todo lo demás mide desde el 1 de enero o a cinco años.

    Sale de la serie que produce `desempeño_del_modelo` y no del archivo de la
    reconstrucción, que termina en julio de 2026: con el archivo, el gráfico y
    la tabla de arriba habrían contado períodos distintos con el mismo nombre.
    """
    if serie is None or len(serie) < 2:
        return ""
    datos = serie.rename(columns=NOMBRE_PUBLICO)
    datos["date"] = pd.to_datetime(datos["date"])
    nombres = _series_presentes(datos, list(COLORES_GRAFICO))
    return _dibujar(datos.sort_values("date"), nombres, TITULO_GRAFICO, ARCHIVO_GRAFICO, "",
                    colores=COLORES_GRAFICO, principal="AlphaData", suave=True,
                    grosores=(GROSOR_PRINCIPAL, GROSOR_RESTO)) if nombres else ""


def _precio(valor, moneda: str) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{moneda} {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _positions(portfolio: pd.DataFrame, currency: str = "$") -> str:
    """Qué hay en cada cartera, desde cuándo y cómo va.

    El precio de ingreso va al lado del actual a propósito: sin él, la
    rentabilidad es un número que el lector tiene que creer. Con los dos
    precios a la vista, lo puede verificar de memoria.

    La columna de dividendos aparece sólo donde hay dividendos itemizados, que
    hoy es el mercado chileno.
    """
    if portfolio is None or portfolio.empty:
        return '<p class="muted">Sin posiciones abiertas.</p>'
    hay_dividendos = "dividendos_clp" in portfolio and portfolio["dividendos_clp"].notna().any()
    hay_caducidad = "caduca" in portfolio and portfolio["caduca"].notna().any()
    rows = []
    for record in portfolio.to_dict("records"):
        entry = pd.to_datetime(record.get("opened_at"), errors="coerce")
        fecha = f"{entry:%d-%m-%Y}" if pd.notna(entry) else "—"
        gain = record.get("open_return")
        gain_text = _signed(float(gain)) if pd.notna(gain) else "—"
        color = "" if gain_text == "—" else ' class="up"' if float(gain) >= 0 else ' class="down"'
        celdas = [escape(str(record["ticker"])), pct(float(record["target_weight"])), fecha,
                  _precio(record.get("entry_price"), currency),
                  _precio(record.get("current_price"), currency)]
        if hay_dividendos:
            celdas.append(_precio(record.get("dividendos_clp"), currency))
        if hay_caducidad:
            celdas.append(_caducidad(record.get("caduca"), record.get("dias_para_caducar")))
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in celdas)
                    + f'<td{color}>{gain_text}</td></tr>')
    cabecera = (["Acción", "Inversión", "Fecha de ingreso", "Precio de ingreso", "Precio actual"]
                + (["Dividendos recibidos"] if hay_dividendos else [])
                + (["Recomendación vigente hasta"] if hay_caducidad else [])
                + ["Rentabilidad"])
    return ("<table><thead><tr>" + "".join(f"<th>{c}</th>" for c in cabecera)
            + f'</tr></thead><tbody>{"".join(rows)}</tbody></table>')


# Cuántos días puede tener la última fila del registro antes de que salte a la
# vista. **Una sola casa con el panel de salud**: dos umbrales para la misma
# pregunta terminarían discrepando, y ya sabemos cómo termina eso.
def _dias_registro() -> int:
    from src.salud import DIAS_REGISTRO
    return DIAS_REGISTRO


TITULO_GENERACIONAL = "Estrategia Ahorro Generacional"
QUE_ES_GENERACIONAL = ("Estrategia diseñada para ahorro en la cuenta 2 de la AFP. Consiste en cambiar la "
                       "inversión entre el fondo de renta variable y el de renta fija (más riesgoso y más "
                       "conservador).")
TITULO_GRAFICO_GENERACIONAL = "Desempeño Ahorro Generacional últimos 10 años"
ARCHIVO_GRAFICO_GENERACIONAL = "ahorro_generacional.png"
COLORES_GENERACIONAL = {"Ahorro Generacional": "#d92d20", "Fondo A": "#1570ef", "Fondo E": "#099250"}


def _estado_generacional(g: dict) -> dict | None:
    """En qué fondo está la estrategia y si acaba de cambiar.

    **Describe a la estrategia, no le recomienda nada a nadie**, y no dice
    cuánto tarda el traspaso: eso depende de la AFP. Hay cambio cuando las
    señales de hoy y la posición en vigor difieren, o sea que la estrategia ya
    cambió de fondo y la posición en vigor todavía no lo refleja. Sin eso el
    informe podía tener un cambio pendiente y no decirlo.
    """
    if not g.get("recomendado"):
        return None
    fecha = lambda d: f"{pd.Timestamp(d):%d-%m-%Y}"
    cambio = g.get("cambio_en_curso")
    return {"fondo": f"Fondo {g['recomendado']}",
            "desde": fecha(g["recomendado_desde"]) if g.get("recomendado_desde") else None,
            "cambio": (f"la estrategia pasó de Fondo {cambio['desde']} a Fondo {cambio['hacia']} "
                       f"el {fecha(cambio['fecha'])}.") if cambio else None}


def _generacional(g: dict | None, as_of) -> dict:
    """Lo que la sección muestra, una sola vez para el HTML y para el texto plano.

    Los nombres de los fondos vienen del registro. En abril de 2027 los
    multifondos desaparecen y esto tiene que seguir diciendo la verdad sin que
    nadie edite la plantilla.
    """
    if g is None:
        return {"aviso": "El registro no se pudo leer en esta corrida. El resto del informe no depende de él.",
                "cambios": [], "cabecera": [], "filas": [], "serie": None, "estado": None}
    dias = (pd.Timestamp(as_of).normalize() - pd.Timestamp(g["fecha"]).normalize()).days
    # Una tabla que dejó de actualizarse se ve igual que una al día: si el
    # registro se quedó atrás, se dice.
    aviso = (f"El registro dejó de crecer: el último día es el {pd.Timestamp(g['fecha']):%d-%m-%Y}, "
             f"hace {int(dias)} días." if dias > _dias_registro() else "")
    evolucion = g.get("evolucion") or {}
    cabecera = ([f"Desde el {pd.Timestamp(evolucion['inicio_año']):%d-%m-%Y}", "Últimos 5 años", "Últimos 10 años"]
                if evolucion else [])
    return {"aviso": aviso, "estado": _estado_generacional(g),
            "cambios": [(f"{pd.Timestamp(fecha):%d-%m-%Y}", f"De Fondo {desde} a Fondo {hacia}")
                        for fecha, desde, hacia in g.get("cambios") or []],
            "cabecera": cabecera,
            "filas": [(nombre, [_signed(r.get(p)) for p in ("año", "cinco_años", "diez_años")])
                      for nombre, r in evolucion.get("filas", [])],
            "serie": evolucion.get("serie")}


def _grafico_generacional(serie: dict | None) -> str:
    """El gráfico de diez años, con la misma serie que sostiene la tabla."""
    if not serie or len(serie.get("fechas", [])) < 2:
        return ""
    datos = pd.DataFrame({"date": pd.to_datetime(serie["fechas"]),
                          **{n: v for n, v in serie.items() if n != "fechas"}})
    nombres = _series_presentes(datos, list(COLORES_GENERACIONAL))
    return _dibujar(datos, nombres, TITULO_GRAFICO_GENERACIONAL, ARCHIVO_GRAFICO_GENERACIONAL, "",
                    colores=COLORES_GENERACIONAL, principal="Ahorro Generacional", suave=True,
                    grosores=(GROSOR_PRINCIPAL, GROSOR_RESTO), años=None) if nombres else ""


def _generacional_lineas(g: dict | None, as_of) -> list[str]:
    """La sección en texto plano: la evolución primero y los cambios al final."""
    s = _generacional(g, as_of)
    lineas = [QUE_ES_GENERACIONAL]
    if s["aviso"]:
        lineas += ["", f"**{s['aviso']}**"]
    if s["estado"]:
        e = s["estado"]
        lineas += ["", f"**Cambio de fondo:** {e['cambio']}" if e["cambio"] else
                   f"La estrategia está en el {e['fondo']}" + (f", sin cambios desde el {e['desde']}." if e["desde"] else ".")]
    if s["filas"]:
        lineas += ["", "**Evolución**"]
        lineas += [f"- {nombre}: " + "; ".join(f"{valor} {titulo[0].lower() + titulo[1:]}"
                                               for titulo, valor in zip(s["cabecera"], valores)) + "."
                   for nombre, valores in s["filas"]]
    if s["cambios"]:
        lineas += ["", f"**Últimos {len(s['cambios'])} cambios**"]
        lineas += [f"- {fecha}: {cambio}" for fecha, cambio in s["cambios"]]
    return lineas


def _generacional_html(g: dict | None, as_of) -> str:
    """Explicación, evolución, gráfico y, al final, los últimos cambios."""
    s = _generacional(g, as_of)
    out = [f'<p class="lead">{escape(QUE_ES_GENERACIONAL)}</p>']
    if s["aviso"]:
        out.append(f'<div class="warn">{escape(s["aviso"])}</div>')
    if s["estado"]:
        e = s["estado"]
        out.append(f'<div class="warn"><strong>Cambio de fondo:</strong> {escape(e["cambio"])}</div>' if e["cambio"] else
                   f'<p class="calm">La estrategia está en el {escape(e["fondo"])}'
                   + (f", sin cambios desde el {e['desde']}." if e["desde"] else ".") + "</p>")
    if s["filas"]:
        out.append("<h3>Evolución</h3><table><thead><tr><th>Fondo</th>"
                   + "".join(f"<th>{escape(c)}</th>" for c in s["cabecera"]) + "</tr></thead><tbody>"
                   + "".join(f'<tr{" class=\"row-strong\"" if nombre == "Ahorro Generacional" else ""}>'
                             f"<td>{escape(nombre)}</td>" + "".join(f"<td>{v}</td>" for v in valores) + "</tr>"
                             for nombre, valores in s["filas"])
                   + "</tbody></table>")
    dibujo = _grafico_generacional(s["serie"])
    if dibujo:
        out.append(f"<h3>{TITULO_GRAFICO_GENERACIONAL}</h3>{dibujo}")
    if s["cambios"]:
        out.append(f'<h3>Últimos {len(s["cambios"])} cambios</h3>'
                   '<table><thead><tr><th>Fecha</th><th>Cambio de fondo</th></tr></thead><tbody>'
                   + "".join(f"<tr><td>{fecha}</td><td>{escape(cambio)}</td></tr>" for fecha, cambio in s["cambios"])
                   + "</tbody></table>")
    return "".join(out)


def _negritas(texto: str) -> str:
    partes = texto.split("**")
    return "".join(p if i % 2 == 0 else f"<strong>{p}</strong>" for i, p in enumerate(partes))


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


def _caja(portfolio: pd.DataFrame, capital: float | None) -> str:
    """Lo que queda sin invertir en una pieza.

    Sigma-6 sólo compra lo que Credicorp recomienda y el momentum confirma, y
    topa cada nombre en 10%: con cinco posiciones deja la mitad en caja. En
    porcentajes eso pasaba inadvertido; en pesos son $2.500.000 quietos y hay
    que decirlo.
    """
    if portfolio is None or portfolio.empty or not capital:
        return ""
    libre = 1 - float(portfolio.target_weight.sum())
    if libre <= .005:
        return ""
    return (f'<p class="muted">En caja: {_pesos(libre * capital, "$")} '
            f'({pct(libre)} de la pieza), porque no hay más nombres que cumplan las condiciones.</p>')


def _cambios(movimientos: pd.DataFrame | None, carteras: dict) -> list[tuple[str, str]]:
    """Qué cambió en cada estrategia, una línea por estrategia.

    Todas aparecen siempre, también las que no cambiaron: tres de las piezas
    son mensuales y la mayoría de las semanas no hay nada, y una estrategia que
    no se nombra se lee como una que se olvidó.

    Lo que entra lleva el porcentaje **del capital de su estrategia**, que es
    el peso con que la cartera lo publica.
    """
    if movimientos is None:
        movimientos = pd.DataFrame(columns=["estrategia", "instrumento", "accion"])
    otras = [e for e in dict.fromkeys(movimientos["estrategia"].astype(str)) if e not in STRATEGIES]
    lineas = []
    for nombre in [*STRATEGIES, *otras]:
        propios = movimientos.loc[movimientos["estrategia"].astype(str) == nombre].to_dict("records")
        if not propios:
            lineas.append((nombre, "Sin cambios" if nombre == "Oro" else "Sin cambios de cartera"))
            continue
        cartera = carteras.get(nombre)
        pesos = (cartera.set_index("ticker")["target_weight"].astype(float).to_dict()
                 if cartera is not None and len(cartera) else {})
        frases = [f"Sale {r['instrumento']}." for r in propios if str(r["accion"]) == "VENDER"]
        for r in propios:
            if str(r["accion"]) != "COMPRAR":
                continue
            entra = str(r["instrumento"])
            frases.append(f"Entra {entra} con {_porcentaje_corto(pesos[entra])} del capital de {nombre}."
                          if entra in pesos else f"Entra {entra}.")
        lineas.append((nombre, " ".join(frases)))
    return lineas


def _movimientos(movimientos: pd.DataFrame | None, ha_entrado: bool = True,
                 carteras: dict | None = None) -> str:
    """El bloque «Cambios en las estrategias».

    **Es una afirmación sobre el modelo, no una orden al lector**, y esa
    distinción no es de estilo. Al retirarse Sigma-6 el bloque decía «Vender
    BCI, LTM, PARAUCO y VAPORES» a alguien que no tenía ninguna de las cuatro
    porque todavía no había entrado al mercado: cierto sobre el modelo,
    imposible de ejecutar, y al mismo tiempo la guía de ingreso le decía
    comprar la cartera completa. Por eso dice qué sale y qué entra, y mientras
    no haya operaciones registradas lo avisa arriba.
    """
    aviso = ("" if ha_entrado else
             '<p class="calm"><strong>Todavía no has comprado nada</strong>, así que esto es '
             'información sobre el modelo y no una lista de órdenes. Lo que te toca hacer es '
             'el detalle de carteras que viene más abajo.</p>')
    return aviso + "".join(
        f'<p class="lead" style="margin:0 0 6px"><strong>{escape(nombre)}:</strong> {escape(texto)}</p>'
        for nombre, texto in _cambios(movimientos, carteras or {}))


def build_public_report(
    as_of: pd.Timestamp,
    delta: pd.DataFrame,
    delta_moves: pd.DataFrame,
    coverage: pd.DataFrame,
    errors: pd.DataFrame,
    history: pd.DataFrame,
    gamma: pd.DataFrame | None = None,
    gamma_moves: pd.DataFrame | None = None,
    oro: pd.DataFrame | None = None,
    oro_moves: pd.DataFrame | None = None,
    movimientos: pd.DataFrame | None = None,
    capital_por_pieza: dict | None = None,
    vigencia: dict | None = None,
    salud: list | None = None,
    conocidos: list | None = None,
    ha_entrado: bool = True,
    generacional: dict | None = None,
    desempeño: dict | None = None,
) -> tuple[str, str]:
    """El informe que se publica y se envía.

    `coverage`, `errors`, `vigencia`, `salud` y `conocidos` se siguen
    recibiendo y **ya no se publican**: la sección «¿Hay que preocuparse?»
    salió del informe. La corrida las sigue calculando.
    """
    vacio_cartera = pd.DataFrame(columns=["ticker", "target_weight"])
    vacio_movs = pd.DataFrame(columns=["ticker", "action", "target_weight"])
    gamma = gamma if gamma is not None else vacio_cartera
    gamma_moves = gamma_moves if gamma_moves is not None else vacio_movs
    oro = oro if oro is not None else vacio_cartera
    oro_moves = oro_moves if oro_moves is not None else vacio_movs
    history = history.copy()
    history["date"] = pd.to_datetime(history["date"])
    metrics = _series_metrics(history)
    portfolios = {"Delta-12": delta, "Gamma-6": gamma, "Oro": oro}
    moves = {"Delta-12": delta_moves, "Gamma-6": gamma_moves, "Oro": oro_moves}

    # Dos bloques separados, que el informe mezcló desde siempre bajo un mismo
    # título: lo que cambió esta semana no es lo mismo que lo que hay que
    # comprar para entrar hoy. Confundirlos es lo que produjo un «Comprar INTC»
    # en la misma página en que la tabla decía «comprada el 30-09-2025».
    reparto_corto = (", ".join(f"{n} {pct(v / sum(capital_por_pieza.values()))}"
                               for n, v in capital_por_pieza.items())
                     if capital_por_pieza else "las piezas en partes iguales")
    orders_block = _movimientos(movimientos, ha_entrado, portfolios)
    conjunto = metrics[CONJUNTO]
    headline = _signed(conjunto["return"])
    benchmark_usable = BENCHMARK in history and is_continuous(history[BENCHMARK])
    versus = conjunto["return"] - metrics[BENCHMARK]["return"] if benchmark_usable and conjunto["return"] is not None and metrics[BENCHMARK]["return"] is not None else None

    # El titular es la rentabilidad del año calendario con el reparto vigente,
    # no la del seguimiento en vivo: ésa sigue en la tabla de cada estrategia y
    # en el gráfico. Sin el dato del año se conserva el titular anterior, que
    # dice desde cuándo mide, antes que publicar un número con otro rótulo.
    #
    # El número va pegado al título y la explicación debajo: arriba del número
    # no va nada.
    if desempeño:
        rinde = desempeño["año"][CONJUNTO]
        pie_titular = f"Invirtiendo en AlphaData desde el {_fecha_larga(desempeño['desde'])} al día de hoy."
        titular = (f'<h2>Cómo va tu dinero este año</h2>'
                   f'<div class="hero {"up" if rinde >= 0 else "down"}">{_signed(rinde)}</div>'
                   f'<p class="lead">{pie_titular}</p>')
        titular_md = f"**Cómo va tu dinero este año: {_signed(rinde)}.** {pie_titular}"
    else:
        comparacion = ('Eso es ' + _signed(versus) + ' comparado con haber invertido en la bolsa chilena completa.'
                       if versus is not None else
                       'La comparación con la bolsa chilena aparecerá cuando su serie esté completa.')
        titular = (f'<h2>Cómo va tu dinero</h2>'
                   f'<p class="lead">Repartiendo el capital en {reparto_corto}, desde que empezó el seguimiento llevas:</p>'
                   f'<div class="hero {"up" if (conjunto["return"] or 0) >= 0 else "down"}">{headline}</div>'
                   f'<p class="lead">{comparacion}</p>')
        titular_md = f"**Conjunto ({reparto_corto}): {headline} desde el {pd.to_datetime(history['date']).min():%d-%m-%Y}.**"

    # La tabla de desempeño: cada estrategia y, en la última fila, AlphaData.
    # Las tres columnas salen de aplicar las reglas a los precios, igual que el
    # titular. El mercado chileno no va: la tabla es de lo que se invierte.
    inicio_año = desempeño["desde"] if desempeño else pd.Timestamp(year=as_of.year, month=1, day=1)
    en_que = dict(QUE_INVIERTE)
    en_que[CONJUNTO] = (desempeño or {}).get("reparto") or (
        {n: v / sum(capital_por_pieza.values()) for n, v in capital_por_pieza.items()} if capital_por_pieza else {})
    resumen = [*STRATEGIES, CONJUNTO]

    def _medida(cual: str, nombre: str) -> float | None:
        return ((desempeño or {}).get(cual) or {}).get(nombre)

    summary_rows = []
    for name in resumen:
        invierte = ("<br>".join(f"{_porcentaje_corto(w)} en {n}" for n, w in en_que[name].items())
                    if name == CONJUNTO else en_que[name])
        strong = ' class="row-strong"' if name == CONJUNTO else ""
        summary_rows.append(f'<tr{strong}><td>{"AlphaData" if name == CONJUNTO else name}</td><td>{invierte}</td>'
                            f'<td>{_signed(_medida("año", name))}</td><td>{_signed(_medida("cinco_años", name))}</td>'
                            f'<td>{pct(_medida("retroceso", name))}</td></tr>')

    positions_blocks = "".join(
        f'<h3>{name} · {QUE_INVIERTE[name]}</h3>{_positions(portfolios[name])}{_caja(portfolios[name], (capital_por_pieza or {}).get(name))}'
        for name in STRATEGIES if name in portfolios
    )

    dibujo = _chart((desempeño or {}).get("serie"))
    grafico = f'<section><h2>{TITULO_GRAFICO}</h2>{dibujo}</section>' if dibujo else ""

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

    <section>{titular}</section>

    <section><h2>Cambios en las estrategias</h2>
    {orders_block}
    </section>

    <section><h2>Desempeño separado por estrategia</h2>
    <table><thead><tr><th>Estrategia</th><th>En qué invierte</th><th>Desde el {inicio_año:%d-%m-%Y}</th><th>Últimos 5 años</th><th>Máximo retroceso en 5 años</th></tr></thead>
    <tbody>{''.join(summary_rows)}</tbody></table>
    <p class="muted"><strong>Máximo retroceso:</strong> lo máximo que llegó a bajar desde su punto más alto antes de recuperarse. Mientras más chica, más tranquilo el camino.</p>
    </section>

    {grafico}

    <section><h2>Detalle de carteras</h2>
    {positions_blocks}
    </section>

    <section><h2>{TITULO_GENERACIONAL}</h2>
    {_generacional_html(generacional, as_of)}
    </section>

    </main></body></html>'''

    lines = [
        "# AlphaData — informe semanal",
        "",
        f"**Fecha:** {as_of:%d-%m-%Y}",
        "",
        titular_md,
        "",
        "## Cambios en las estrategias",
        "",
    ]
    lines += [f"- {nombre}: {texto}" for nombre, texto in _cambios(movimientos, portfolios)]
    if not ha_entrado:
        lines.append("- Todavía no has comprado nada: esto es información sobre el modelo, no una "
                     "lista de órdenes. Lo que te toca hacer es el detalle de carteras.")
    lines += ["", "## Desempeño separado por estrategia", ""]
    for name in resumen:
        lines.append(f"- {'AlphaData' if name == CONJUNTO else name}: {_signed(_medida('año', name))} desde el {inicio_año:%d-%m-%Y}; "
                     f"{_signed(_medida('cinco_años', name))} en los últimos 5 años; "
                     f"máximo retroceso en 5 años {pct(_medida('retroceso', name))}.")
    lines += ["", f"## {TITULO_GENERACIONAL}", ""] + _generacional_lineas(generacional, as_of)
    lines += ["", "El informe HTML incluye el gráfico y las carteras. La metodología y sus parámetros son información reservada.", ""]
    return _publico("\n".join(lines)), _publico(html)
