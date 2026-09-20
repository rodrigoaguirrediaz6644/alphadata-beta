"""Vara de medir para candidatos a proveedor de precios chilenos.

Un candidato no se elige por catálogo ni por promesa de cobertura: se valida
contra los datos que ya sabemos buenos, en el tramo que ambos comparten.

Lo que se mide y por qué:

- **Razón mediana.** Si el candidato publica el mismo instrumento con la misma
  convención de cierre, la razón típica contra el cierre guardado es 1. Una
  mediana distinta de 1 significa otra convención —típicamente una serie
  ajustada por dividendos contra una cruda— y descalifica de inmediato, porque
  ya no se están comparando los mismos números.

- **Días que calzan exacto.** Medido sobre los once archivos de referencia da
  entre 90% y 98% según el instrumento. No es 100%: proveedores distintos
  difieren en el cierre de días poco líquidos. Por eso el umbral por defecto es
  90% y no 100%.

- **Desvío de los días que no calzan.** En la referencia el percentil 95 del
  desvío queda bajo 1,2%. Un candidato con la mediana en 1 pero con desvíos
  grandes está publicando otra cosa en los días que difiere.

- **Bloques de factor constante.** Días consecutivos con el mismo factor son un
  ajuste por dividendo o split, no un error. Se informan aparte para poder
  explicarlos en vez de contarlos como ruido.

Los umbrales por defecto salen de medir la referencia, no de teoría. Están para
ser revisados cuando haya un candidato real que medir.
"""

from __future__ import annotations

import pandas as pd

TOLERANCIA = 1e-6
MINIMO_EXACTOS = .90
MAXIMO_DESVIO_P95 = .012


def _bloques(razon: pd.Series, tolerancia: float) -> list[dict]:
    """Agrupa en tramos los días consecutivos que comparten el mismo factor."""
    fuera = razon[(razon - 1).abs() > tolerancia]
    bloques: list[dict] = []
    for fecha, factor in fuera.items():
        previo = bloques[-1] if bloques else None
        if previo is not None and abs(factor / previo["factor"] - 1) <= 1e-4:
            previo["hasta"] = fecha
            previo["dias"] += 1
            continue
        bloques.append({"desde": fecha, "hasta": fecha, "dias": 1, "factor": float(factor)})
    return bloques


def comparar(candidato: pd.Series, referencia: pd.Series, tolerancia: float = TOLERANCIA) -> dict:
    """Compara un candidato contra el cierre guardado en el tramo común."""
    candidato = pd.to_numeric(candidato, errors="coerce").dropna()
    referencia = pd.to_numeric(referencia, errors="coerce").dropna()
    comun = candidato.index.intersection(referencia.index)
    vacio = {"dias": 0, "razon_mediana": None, "exactos": None, "desvio_p95": None, "desvio_max": None, "bloques": []}
    if len(comun) == 0:
        return vacio
    razon = (candidato.loc[comun] / referencia.loc[comun]).replace([float("inf"), float("-inf")], pd.NA).dropna()
    if razon.empty:
        return vacio
    desvio = (razon - 1).abs()
    return {
        "dias": int(len(razon)),
        "razon_mediana": float(razon.median()),
        "exactos": float((desvio <= tolerancia).mean()),
        "desvio_p95": float(desvio.quantile(.95)),
        "desvio_max": float(desvio.max()),
        "bloques": [b for b in _bloques(razon, tolerancia) if b["dias"] > 1],
    }


def aprueba(resultado: dict, minimo_exactos: float = MINIMO_EXACTOS,
            maximo_desvio_p95: float = MAXIMO_DESVIO_P95, tolerancia: float = TOLERANCIA) -> bool:
    """Decide si un candidato sirve como fuente de precios.

    Exige las tres cosas a la vez: misma convención de cierre (mediana en 1),
    coincidencia exacta casi siempre, y que lo que no calza sea pequeño.
    """
    if not resultado["dias"] or resultado["razon_mediana"] is None:
        return False
    return (abs(resultado["razon_mediana"] - 1) <= tolerancia
            and resultado["exactos"] >= minimo_exactos
            and resultado["desvio_p95"] <= maximo_desvio_p95)


def serie_guardada(precios: pd.DataFrame, ticker: str, columna: str = "close") -> pd.Series:
    """El cierre crudo guardado para un instrumento, indexado por fecha."""
    filas = precios.loc[precios.alphadata_ticker == ticker, ["date", columna]].dropna()
    return filas.set_index("date")[columna].sort_index()
