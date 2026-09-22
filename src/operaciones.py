"""Lo que Rodrigo tiene de verdad, leído de `data/operaciones_reales.csv`.

Desde el 22-09-2026 hay plata real en la cuenta, y eso abre una falla que antes
no podía existir: **tener comprado algo que el modelo ya vendió.** Nada la
detectaría sola. El informe habla de la cartera del modelo y la cuenta habla de
otra cosa, y las dos se ven perfectamente sanas por separado.

## Por qué sobre instrumentos y no sobre cantidades

Las cantidades **no van a calzar y eso no es un error**. La primera compra fue
de 8 IAUCL cuando la cartera de referencia son 63: una compra de prueba. Y
aunque estuviera completa, el redondeo a unidades enteras y el momento de cada
orden hacen que las cantidades bailen siempre.

Lo que sí es un error, y es el que importa, es de otra clase: que en la cuenta
haya un instrumento que el modelo **no tiene**. Eso significa una de dos cosas,
y las dos hay que mirarlas: o se compró algo que el modelo nunca pidió, o el
modelo lo vendió y la venta no se ejecutó.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COMPRAS = {"COMPRA"}
VENTAS = {"VENTA"}
# Una orden que no se ejecutó no cambia lo que hay en la cuenta. `cantidad` es
# lo que se ejecutó de verdad, así que basta con sumarla, pero se deja escrito
# porque la tentación de sumar `cantidad_pedida` va a existir.
EJECUTADAS = {"EJECUTADA", "PARCIAL"}


def cargar(ruta: str | Path) -> pd.DataFrame:
    ruta = Path(ruta)
    if not ruta.exists():
        return pd.DataFrame(columns=["estrategia", "instrumento", "accion", "estado", "cantidad"])
    return pd.read_csv(ruta)


def tenencias(operaciones: pd.DataFrame) -> dict[str, float]:
    """`{instrumento: unidades}` con lo que quedó en la cuenta, neto de ventas."""
    if operaciones.empty or "instrumento" not in operaciones:
        return {}
    d = operaciones.loc[operaciones.estado.isin(EJECUTADAS) & operaciones.instrumento.notna()].copy()
    if d.empty:
        return {}
    d["signo"] = d.accion.map(lambda a: 1 if a in COMPRAS else (-1 if a in VENTAS else 0))
    d["neto"] = d.signo * pd.to_numeric(d.cantidad, errors="coerce").fillna(0)
    total = d.groupby("instrumento").neto.sum()
    return {t: float(v) for t, v in total.items() if v > 0}


def descalce(operaciones: pd.DataFrame, carteras: dict[str, list[str] | set[str]]) -> list[str]:
    """Instrumentos que están en la cuenta y no en ninguna cartera del modelo.

    `carteras` es `{estrategia: instrumentos}`. Devuelve la lista ordenada, que
    vacía es la respuesta normal.
    """
    del_modelo = {t for lista in carteras.values() for t in lista}
    return sorted(t for t in tenencias(operaciones) if t not in del_modelo)
