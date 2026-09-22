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
# Bajo este monto la comisión mínima sale más cara que el porcentual:
# minimo / tasa, con los dos medidos sobre órdenes reales de Trii.
UMBRAL_MINIMO = 560_218
# La misma para acción chilena y para CDV. Ver config/runtime.v2.json.
TARIFA = "0,1785%, con mínimo de $999,99"
SIN_FECHA = "por ranking, sin fecha"
PERMANENTE = "posición permanente"


def costo_de_una(monto: float, tasa: float, minimo: float) -> float:
    """Comisión de una operación: el porcentaje, o el mínimo si es mayor."""
    return max(tasa * monto, minimo)


def costo_del_par(monto: float, tasa: float, minimo: float) -> float:
    """Comisión de comprar y de vender la misma posición."""
    return 2 * costo_de_una(monto, tasa, minimo)


def cartera_de_ingreso(carteras: dict[str, pd.DataFrame], as_of: pd.Timestamp,
                       costos: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """Una fila por posición vigente, con su monto, sus relojes y su costo.

    `costos` es `{estrategia: (tasa, minimo)}`.
    """
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
            filas.append({
                "estrategia": estrategia, "instrumento": fila["ticker"],
                "monto_referencia": float(monto), "precio": float(precio),
                "unidades": unidades, "monto_efectivo": efectivo,
                "residuo": float(monto) - efectivo,
                "dias_en_cartera": (pd.Timestamp(as_of).normalize() - apertura.normalize()).days
                                   if pd.notna(apertura) else None,
                "proxima_salida": salida, "dias_hasta_la_salida": plazo,
                "costo_de_entrar": costo_de_una(efectivo, tasa, minimo) if efectivo > 0 else 0.,
                "sobre_el_umbral": bool(tasa * efectivo >= minimo) if efectivo > 0 else False,
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
    ]
    for estrategia in ["Sigma-6", "Delta-12", "Gamma-6", "Oro"]:
        parte = tabla.loc[tabla.estrategia == estrategia]
        if parte.empty:
            continue
        lineas += [f"## {estrategia}", "",
                   "| acción | unidades | a gastar | residuo | en cartera hace | próxima salida | costo ida y vuelta |",
                   "|---|---:|---:|---:|---:|---|---:|"]
        for r in parte.to_dict("records"):
            salida = r["proxima_salida"]
            if pd.notna(r["dias_hasta_la_salida"]):
                salida += f" · en {int(r['dias_hasta_la_salida'])} días"
            costo = f"{_pesos(r['costo_del_par'])} · {_pct(r['costo_pct'])}"
            if pd.notna(r["costo_anualizado"]):
                costo += f" · {_pct(r['costo_anualizado'], 1)} anual"
            dias = f"{int(r['dias_en_cartera'])} días" if pd.notna(r["dias_en_cartera"]) else "—"
            lineas.append(f"| {r['instrumento']} | {r['unidades']:,} ".replace(",", ".")
                          + f"| {_pesos(r['monto_efectivo'])} | {_pesos(r['residuo'])} "
                          + f"| {dias} | {salida} | {costo} |")
        residuo = parte.residuo.sum()
        lineas += ["", f"Residuo de esta pieza: **{_pesos(residuo)}**, que queda en su caja.", ""]
    entrada = float(tabla.costo_de_entrar.sum())
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
         f"{_pesos(UMBRAL_MINIMO)}, bajo el cual el mínimo sale más caro que el porcentual."
         if not bajo else
         f"**{bajo} posiciones quedan bajo el umbral de {_pesos(UMBRAL_MINIMO)} y pagan el "
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
