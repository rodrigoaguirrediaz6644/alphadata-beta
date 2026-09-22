"""La cartera de ingreso: qué compra hoy el que entra, con sus relojes.

`GUIA_INGRESO.md` dice comprar la cartera vigente completa, y esa regla no
cambia: está medida y el filtro «sólo las que van abajo» no se distingue entre
submuestras. Lo que faltaba es que quien compra **sepa lo que está comprando**,
y eso son tres cosas que la guía no tenía porque hasta hace poco no existían.

**Hace cuánto la tiene el modelo.** Sin el tope de tenencia, Sigma-6 puede
sostener un nombre por años: BCI viene desde octubre de 2024. No es lo mismo
heredar una posición de dos semanas que una de dos años.

**Su próxima salida conocida, si la tiene.** En Sigma-6 la recomendación caduca
a los 365 días y eso es una fecha. En Delta-12 y Gamma-6 las salidas son por
ranking y **no tienen fecha**, que es distinto de no saberse: hay que decirlo en
vez de dejar la celda vacía.

**El costo del par entrada-salida en ese plazo.** Comprar una posición a dos
meses de su salida conocida paga las dos comisiones igual que una que va a durar
un año. Con el mínimo de $999,99 por operación, una posición de medio millón a
diez semanas de caducar cuesta 0,40% de tenencia: 2,1% anualizado. La misma
comisión repartida en diez meses es 0,51% anual, cuatro veces menos.

**Es información, no un filtro.** La decisión de comprar la cartera completa
está tomada y medida; lo que esto evita es enterarse después.
"""

from __future__ import annotations

import pandas as pd

# Las acciones chilenas se transan por unidades enteras, así que el monto de
# referencia casi nunca se puede gastar entero. Se redondea **hacia abajo** y
# el residuo queda en la caja de la pieza, igual que el producto de una venta.
# Con veinte posiciones el residuo es real y los pesos efectivos del primer día
# no van a calzar con los de referencia: eso es esperado, no un error.
REDONDEO = "unidades enteras, hacia abajo, residuo a la caja de la pieza"
def umbral_minimo(tasa: float, minimo: float) -> float:
    """Bajo este monto la comisión mínima sale más cara que el porcentual.

    **Es derivado, no un dato**: mínimo / tasa. Estuvo escrito como constante y
    también en la configuración, que son dos casas para un número que no tiene
    ninguna: cambiar el mínimo y olvidar el umbral lo deja mintiendo. Es la
    misma forma del defecto que ya costó dos años con el símbolo de Bank of
    America y meses con la tarifa de los CDV.
    """
    return minimo / tasa if tasa else float("inf")
# La misma para acción chilena y para CDV. Ver config/runtime.v2.json.
TARIFA = "0,15% + IVA = 0,1785%, con mínimo de $999,99"
SIN_FECHA = "por ranking, sin fecha"
PERMANENTE = "posición permanente"


def costo_de_una(monto: float, tasa: float, minimo: float) -> float:
    """Comisión de una operación: el porcentaje, o el mínimo si es mayor."""
    return max(tasa * monto, minimo)


def costo_del_par(monto: float, tasa: float, minimo: float) -> float:
    """Comisión de comprar y de vender la misma posición."""
    return 2 * costo_de_una(monto, tasa, minimo)


def cartera_de_ingreso(carteras: dict[str, pd.DataFrame], as_of: pd.Timestamp,
                       costos: dict[str, tuple[float, float]],
                       simbolos: pd.DataFrame | None = None) -> pd.DataFrame:
    """Una fila por posición vigente, con su monto, sus relojes y su costo.

    `costos` es `{estrategia: (tasa, minimo)}`. `simbolos` es la puerta de
    `src.cdv.estado`: sin ella, ningún nombre estadounidense trae símbolo.
    """
    puerta = ({r.ticker: r for r in simbolos.itertuples()} if simbolos is not None
              and len(simbolos) else {})
    filas = []
    for estrategia, cartera in carteras.items():
        if cartera is None or cartera.empty:
            continue
        tasa, minimo = costos[estrategia]
        for fila in cartera.to_dict("records"):
            monto, precio = fila.get("monto_clp"), fila.get("current_price")
            if monto is None or pd.isna(monto) or precio is None or pd.isna(precio) or precio <= 0:
                continue
            unidades = int(float(monto) // float(precio))
            efectivo = unidades * float(precio)
            costo = costo_del_par(efectivo, tasa, minimo) if efectivo > 0 else 0.
            apertura = pd.to_datetime(fila.get("opened_at"), errors="coerce")
            caduca = pd.to_datetime(fila.get("caduca"), errors="coerce")
            dias = fila.get("dias_para_caducar")
            if estrategia == "Oro":
                salida, plazo = PERMANENTE, None
            elif pd.notna(caduca):
                salida, plazo = f"{caduca:%d-%m-%Y}", (int(dias) if pd.notna(dias) else None)
            else:
                salida, plazo = SIN_FECHA, None
            g = puerta.get(fila["ticker"])
            if g is None:                       # chilena: se opera con su propio ticker
                simbolo, estado_s, motivo_s = fila["ticker"], "operable", ""
            elif g.estado == "operable":
                simbolo, estado_s, motivo_s = g.simbolo, g.estado, g.motivo
            else:
                simbolo, estado_s, motivo_s = "", g.estado, g.motivo
            filas.append({
                "estrategia": estrategia, "instrumento": fila["ticker"],
                "simbolo": simbolo, "estado_simbolo": estado_s, "motivo_simbolo": motivo_s,
                "monto_referencia": float(monto), "precio": float(precio),
                "unidades": unidades, "monto_efectivo": efectivo,
                "residuo": float(monto) - efectivo,
                "dias_en_cartera": (pd.Timestamp(as_of).normalize() - apertura.normalize()).days
                                   if pd.notna(apertura) else None,
                "proxima_salida": salida, "dias_hasta_la_salida": plazo,
                "costo_de_entrar": costo_de_una(efectivo, tasa, minimo) if efectivo > 0 else 0.,
                "sobre_el_umbral": bool(tasa * efectivo >= minimo) if efectivo > 0 else False,
                "umbral": umbral_minimo(tasa, minimo),
                "costo_del_par": costo,
                "costo_pct": costo / efectivo if efectivo else None,
                "costo_anualizado": (costo / efectivo) * 365 / plazo if efectivo and plazo else None,
            })
    return pd.DataFrame(filas)


def _pesos(valor) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"$ {float(valor):,.0f}".replace(",", ".")


def _pct(valor, digits: int = 2) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{float(valor):.{digits}%}".replace(".", ",")


def _bloqueadas(tabla: pd.DataFrame) -> list[str]:
    """Lo que la puerta de símbolos no dejó pasar, y por qué.

    El símbolo del CDV se arma pegando un sufijo al ticker, y **cuando un
    ticker es prefijo de otro la regla produce un instrumento real y
    equivocado**: BA + CL da BACL, que es Boeing, no Bank of America. No falla
    con ruido, falla con una serie de precios válida de otra empresa, y así
    duró dos años. Por eso no basta con haber arreglado ese caso: ningún nombre
    estadounidense aparece acá con símbolo si no pasó la verificación.
    """
    if "estado_simbolo" not in tabla.columns:
        return []
    malas = tabla.loc[tabla.estado_simbolo != "operable"]
    if malas.empty:
        return []
    lineas = ["## Lo que no se opera, y por qué", "",
              "**Estas posiciones no llevan símbolo**, así que no hay nada que teclear en la",
              "corredora. El modelo las tiene y su NAV las cuenta; lo que falta es poder",
              "comprarlas con la certeza de estar comprando la empresa correcta.", "",
              "| acción | pieza | qué pasa |", "|---|---|---|"]
    for r in malas.to_dict("records"):
        lineas.append(f"| {r['instrumento']} | {r['estrategia']} | {r['motivo_simbolo']} |")
    lineas += ["", "Mientras tanto ese monto queda en la caja de su pieza.", ""]
    return lineas


def markdown(tabla: pd.DataFrame, as_of: pd.Timestamp) -> str:
    """El documento que lee quien va a poner la primera orden."""
    if tabla.empty:
        return "# Cartera de ingreso\n\nSin posiciones vigentes.\n"
    lineas = [
        "# Cartera de ingreso",
        "",
        f"Lo que compra hoy el que entra, al cierre del {pd.Timestamp(as_of):%d-%m-%Y}.",
        "",
        "Se compra **la cartera vigente completa**, sin mirar si cada posición va",
        "arriba o abajo del precio de entrada del modelo y sin saltarse las que",
        "parezcan próximas a venderse. Las columnas de abajo son **información, no",
        "un filtro**: ver `GUIA_INGRESO.md` para por qué.",
        "",
        "## Órdenes a mercado, y el precio teórico es para después",
        "",
        "**Las órdenes van a mercado, no con precio límite.** La pantalla de la",
        "corredora muestra el último negocio, que puede ser de hace semanas: el día de",
        "la primera compra IAUCL exhibió $76.500 durante toda la jornada —cierre",
        "anterior, máximo, mínimo y último, los cuatro iguales, volumen cero— y llenó a",
        "**$77.300**. Trii no llena al precio exhibido: cotiza fresco al ejecutar. Poner",
        "un límite contra un precio rancio sólo agrega el riesgo de no llenar.",
        "",
        "**El precio teórico de la tabla es para contrastar después, no para poner un",
        "límite.** Es el subyacente en dólares por el tipo de cambio. Después de operar,",
        "anotar en `data/operaciones_reales.csv` el precio de llenado de cada posición:",
        "**si alguna se sale de ~1%, ahí sí hay algo que mirar.**",
        "",
        "**Con una trampa que ya apareció en la primera orden.** El contraste va contra el",
        "teórico **del día en que se ejecutó**, no contra el de esta tabla. El llenado de",
        "IAUCL a $77.300 el 22-09 queda 1,98% bajo el teórico de esta guía, que es del",
        "21-09 y se calculó con un cierre del subyacente de dos ruedas antes. Contra el",
        "teórico del 22-09 la diferencia es 0,05%. **Si se contrasta contra la columna",
        "impresa, la guardia va a sonar sola cada vez que el almacén venga un par de",
        "ruedas atrasado.**",
        "",
        "Para referencia de lo que es normal: en la orden del 22-09 el tipo de cambio",
        "implícito en el precio pagado fue 946,49 contra los 947,57 que ofrecía la",
        "pantalla de conversión de Trii el mismo día. **Difieren en 0,11%.**",
        "",
    ]
    for estrategia in ["Sigma-6", "Delta-12", "Gamma-6", "Oro"]:
        parte = tabla.loc[tabla.estrategia == estrategia]
        if parte.empty:
            continue
        lineas += [f"## {estrategia}", "",
                   "| acción | símbolo a operar | unidades | precio teórico | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |",
                   "|---|---|---:|---:|---:|---:|---:|---|---:|"]
        for r in parte.to_dict("records"):
            salida = r["proxima_salida"]
            if pd.notna(r["dias_hasta_la_salida"]):
                salida += f" · en {int(r['dias_hasta_la_salida'])} días"
            costo = f"{_pesos(r['costo_del_par'])} · {_pct(r['costo_pct'])}"
            if pd.notna(r["costo_anualizado"]):
                costo += f" · {_pct(r['costo_anualizado'], 1)} anual"
            dias = f"{int(r['dias_en_cartera'])} días" if pd.notna(r["dias_en_cartera"]) else "—"
            simbolo = r.get("simbolo") or "**no operar**"
            lineas.append(f"| {r['instrumento']} | {simbolo} | {r['unidades']:,} ".replace(",", ".")
                          + f"| {_pesos(r['precio'])} | {_pesos(r['monto_efectivo'])} | {_pesos(r['residuo'])} "
                          + f"| {dias} | {salida} | {costo} |")
        residuo = parte.residuo.sum()
        lineas += ["", f"Residuo de esta pieza: **{_pesos(residuo)}**, que queda en su caja.", ""]
    lineas += _bloqueadas(tabla)
    entrada = float(tabla.costo_de_entrar.sum())
    umbral = float(tabla.umbral.dropna().iloc[0]) if tabla.umbral.notna().any() else float("nan")
    total, efectivo = tabla.monto_referencia.sum(), tabla.monto_efectivo.sum()
    por_pieza = tabla.groupby("estrategia").agg(
        invertido=("monto_efectivo", "sum"), comision=("costo_de_entrar", "sum"),
        bajo_umbral=("sobre_el_umbral", lambda x: int((~x.astype(bool)).sum())))
    lineas += [
        "## Lo que va a cobrar la corredora el primer día",
        "",
        f"Comprar las {len(tabla)} posiciones cuesta **{_pesos(entrada)}** en comisiones.",
        "",
        "| pieza | se invierte | comisión | tarifa |",
        "|---|---:|---:|---|",
    ]
    for estrategia, r in por_pieza.iterrows():
        lineas.append(f"| {estrategia} | {_pesos(r.invertido)} | {_pesos(r.comision)} | {TARIFA} |")
    bajo = int(por_pieza.bajo_umbral.sum())
    lineas += [
        "",
        (f"**Ninguna posición paga el mínimo**: todas superan el umbral de "
         f"{_pesos(umbral)}, bajo el cual el mínimo sale más caro que el porcentual."
         if not bajo else
         f"**{bajo} posiciones quedan bajo el umbral de {_pesos(umbral)} y pagan el "
         "mínimo en vez del porcentual.**"),
        "",
        "**La tarifa es la misma para las tres piezas**, acción chilena o CDV. El sistema supuso",
        "durante meses un 0,1% para los CDV, y una pantalla de orden real de IAUCL lo desmintió",
        "al peso: $612.000 de valor, $1.092,42 de comisión, que es 0,1785% exacto.",
        "",
        "**Ojo con una cuenta fácil de hacer mal:** no es el 0,1785% de los $20 millones, porque",
        f"la base no son $20 millones. El redondeo a unidades enteras deja {_pesos(total - efectivo)} sin",
        "invertir, y sobre lo que sí se invierte la cuenta da exacta.",
        "",
        "Este número es lo primero que se puede contrastar contra la boleta de la corredora, y",
        "es la mejor validación del modelo de costo que hay: si Trii cobra otra cosa, el modelo",
        "está mal y hay que corregirlo antes de que la diferencia se acumule.",
        "",
    ]
    lineas += [
        "## El residuo del redondeo",
        "",
        f"Las acciones se transan por **{REDONDEO}**. De {_pesos(total)} de referencia se "
        f"gastan {_pesos(efectivo)} y quedan **{_pesos(total - efectivo)}** en caja, "
        f"un {_pct((total - efectivo) / total, 1)}.",
        "",
        "**Los pesos efectivos del primer día no van a calzar con los de referencia, y eso",
        "es esperado, no un error.** Cuanto más caro el instrumento, mayor el residuo: una",
        "posición donde caben cinco unidades deja mucho más suelto que una donde caben",
        "veinte mil.",
        "",
        "Para los CDV estadounidenses **hay que confirmar con la corredora si admiten",
        "fracciones o tienen lote mínimo**. Es una pregunta para Trii, no un cálculo, y",
        "aquí vale plata: es donde se concentra el residuo.",
        "",
    ]
    return "\n".join(lineas) + "\n"
