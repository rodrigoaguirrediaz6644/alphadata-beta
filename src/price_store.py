"""Almacén de precios de sólo agregar.

La regla: una fila ya grabada para un instrumento y una fecha es definitiva.
Fecha, apertura, máximo, mínimo, cierre crudo y volumen son hechos del mercado
y no cambian después. Lo que sí cambia hacia atrás es el cierre ajustado,
porque cada dividendo reescala toda la historia previa.

Por qué importa: hasta septiembre de 2026 el archivo se reescribía completo en
cada corrida con lo que devolviera el proveedor. Cuando el feed chileno se
detuvo el 17-07-2026 y empezó a entregar historial congelado con una sola fila
viva, esa fila viva revertía al valor congelado en la descarga siguiente y
nadie lo notó durante dos meses. Con un almacén de sólo agregar, el precio
bueno del 15 de julio habría quedado grabado, los viernes siguientes no habrían
traído ninguna fila nueva, y la detención habría saltado a la vista esa misma
semana.

Una diferencia en un dato pasado no se aplica sola: se informa. Sólo es
aceptable si hay una acción corporativa que la explique.
"""

from __future__ import annotations

import pandas as pd

CLAVE = ["alphadata_ticker", "date"]
CRUDAS = ["open", "high", "low", "close", "volume"]
DERIVADA = "adjusted_close"


def _indexar(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty or "date" not in frame:
        return pd.DataFrame(columns=CLAVE + CRUDAS + [DERIVADA, "yahoo_ticker"])
    salida = frame.copy()
    salida["date"] = pd.to_datetime(salida["date"], errors="coerce")
    return salida.dropna(subset=["date", "alphadata_ticker"]).drop_duplicates(CLAVE, keep="last")


def instrumentos_con_simbolo_nuevo(guardado: pd.DataFrame, nuevo: pd.DataFrame) -> set[str]:
    """Instrumentos cuyo símbolo de proveedor cambió desde la última descarga.

    Al sustituir un símbolo extinto por otro —pasó con IPSA_TR— las dos series
    tienen niveles distintos y no se pueden encadenar: mezclarlas inventa un
    salto de rentabilidad. Esos instrumentos se regraban enteros.
    """
    cambiados = set()
    if guardado.empty or nuevo.empty or "yahoo_ticker" not in guardado or "yahoo_ticker" not in nuevo:
        return cambiados
    for ticker, grupo in nuevo.groupby("alphadata_ticker"):
        antes = set(guardado.loc[guardado.alphadata_ticker == ticker, "yahoo_ticker"].dropna().astype(str))
        ahora = set(grupo["yahoo_ticker"].dropna().astype(str))
        if antes and ahora and antes != ahora:
            cambiados.add(str(ticker))
    return cambiados


def agregar(guardado: pd.DataFrame, nuevo: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Incorpora la descarga sin tocar lo ya grabado.

    Devuelve `(resultado, revisiones)`. `revisiones` son las fechas en que el
    proveedor entregó un dato crudo distinto del guardado: se informan y **no**
    se aplican. El cierre ajustado sí se actualiza, porque es derivado.
    """
    guardado, nuevo = _indexar(guardado), _indexar(nuevo)
    if guardado.empty:
        return nuevo.sort_values(CLAVE).reset_index(drop=True), pd.DataFrame(columns=["alphadata_ticker", "date", "columna", "guardado", "recibido"])
    regrabar = instrumentos_con_simbolo_nuevo(guardado, nuevo)
    guardado = guardado.loc[~guardado.alphadata_ticker.isin(regrabar)]

    g = guardado.set_index(CLAVE)
    n = nuevo.set_index(CLAVE)
    comunes = g.index.intersection(n.index)

    revisiones = []
    for columna in CRUDAS:
        if columna not in g or columna not in n:
            continue
        antes = pd.to_numeric(g.loc[comunes, columna], errors="coerce")
        ahora = pd.to_numeric(n.loc[comunes, columna], errors="coerce")
        difiere = (antes - ahora).abs() > (antes.abs() * 1e-9)
        difiere = difiere & antes.notna() & ahora.notna()
        for clave in comunes[difiere]:
            revisiones.append({"alphadata_ticker": clave[0], "date": clave[1], "columna": columna,
                               "guardado": float(antes.loc[clave]), "recibido": float(ahora.loc[clave])})

    resultado = g.copy()
    if DERIVADA in n and len(comunes):
        resultado.loc[comunes, DERIVADA] = n.loc[comunes, DERIVADA]  # el ajustado es derivado y sí se recalcula
    nuevas = n.loc[n.index.difference(g.index)]
    resultado = pd.concat([resultado, nuevas]) if len(nuevas) else resultado
    resultado = resultado.reset_index().sort_values(CLAVE).reset_index(drop=True)
    return resultado, pd.DataFrame(revisiones, columns=["alphadata_ticker", "date", "columna", "guardado", "recibido"])


def cambios_de_ajuste(guardado: pd.DataFrame, nuevo: pd.DataFrame, tolerancia: float = 1e-6) -> pd.DataFrame:
    """Rastro de las acciones corporativas implícitas en el cierre ajustado.

    Un dividendo reescala todo el tramo anterior a su fecha ex por un mismo
    factor. Se informa el factor y cuántos días abarca para poder explicarlo,
    en vez de dejar que la historia cambie en silencio.
    """
    guardado, nuevo = _indexar(guardado), _indexar(nuevo)
    if guardado.empty or nuevo.empty or DERIVADA not in guardado or DERIVADA not in nuevo:
        return pd.DataFrame(columns=["alphadata_ticker", "desde", "hasta", "dias", "factor"])
    g = guardado.set_index(CLAVE)[DERIVADA]
    n = nuevo.set_index(CLAVE)[DERIVADA]
    comunes = g.index.intersection(n.index)
    razon = (pd.to_numeric(n.loc[comunes], errors="coerce") / pd.to_numeric(g.loc[comunes], errors="coerce")).dropna()
    razon = razon[(razon - 1).abs() > tolerancia]
    filas = []
    for ticker, grupo in razon.groupby(level=0):
        fechas = grupo.index.get_level_values(1)
        filas.append({"alphadata_ticker": ticker, "desde": fechas.min(), "hasta": fechas.max(),
                      "dias": int(len(grupo)), "factor": float(grupo.median())})
    return pd.DataFrame(filas, columns=["alphadata_ticker", "desde", "hasta", "dias", "factor"])
