"""El libro de posiciones, que lo escribe producción.

`tools/construir_libro.py` llenó el pasado una sola vez. De aquí en adelante
cada corrida agrega sus aperturas y sus cierres. Si el libro siguiera siendo un
artefacto derivado que se regenera entero, en tres meses estaríamos otra vez
sin saber desde cuándo viene cada posición.

## La línea que no se cruza

El libro guarda **fechas y precios de entrada**. No guarda NAV.

Una posición puede mostrar +8% mientras su estrategia muestra −0,1%, y eso no
es una contradicción: la ganancia no realizada de una posición desde que se
compró y el rendimiento de la cartera en un periodo son dos mediciones
distintas, como en cualquier cartola. Encadenarlas es exactamente lo que
fabricó el +30% que este proyecto vino a terminar.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNAS = ["estrategia", "instrumento", "fecha_entrada", "precio_entrada",
            "fecha_salida", "origen"]


def cargar(ruta: str | Path) -> pd.DataFrame:
    ruta = Path(ruta)
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS)
    return pd.read_csv(ruta, parse_dates=["fecha_entrada", "fecha_salida"])


CALENTAMIENTO = "calentamiento"


def _vivas(libro: pd.DataFrame, estrategia: str) -> pd.DataFrame:
    """Las posiciones abiertas que se pueden publicar.

    El recorrido arranca un año antes del piso de publicación para que el
    estado sea el correcto al entrar a la ventana. Esas filas se conservan
    —sirven para auditar y para los contadores de tenencia— pero no llevan
    precio, porque vienen de un tramo sin reparar, y no se muestran nunca.
    """
    vivas = libro.loc[(libro.estrategia == estrategia) & libro.fecha_salida.isna()]
    return vivas.loc[vivas.origen != CALENTAMIENTO] if "origen" in vivas else vivas


def abiertas(libro: pd.DataFrame, estrategia: str) -> dict[str, pd.Timestamp]:
    """Las posiciones vivas de una estrategia, con su fecha de entrada."""
    if libro.empty:
        return {}
    vivas = _vivas(libro, estrategia)
    return dict(zip(vivas.instrumento, pd.to_datetime(vivas.fecha_entrada)))


def _precio(precios: pd.DataFrame, ticker: str, fecha: pd.Timestamp) -> float | None:
    """Cierre crudo de la fecha de señal, en la moneda que muestra el informe."""
    hasta = precios.loc[(precios.alphadata_ticker == ticker) & (precios.date <= fecha), ["date", "close"]].dropna()
    if hasta.empty:
        return None
    return float(hasta.sort_values("date").close.iloc[-1])


def anotar(libro: pd.DataFrame, estrategia: str, cartera: pd.DataFrame,
           fecha_senal: pd.Timestamp, precios: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Agrega las aperturas y cierra las salidas de una estrategia.

    Devuelve el libro actualizado y una lista legible de lo que anotó, para que
    la corrida lo informe y quede en el registro del commit.
    """
    vivas = abiertas(libro, estrategia)
    actual = set(cartera.ticker) if len(cartera) else set()
    fecha_senal = pd.Timestamp(fecha_senal)
    movimientos: list[str] = []

    salidas = sorted(set(vivas) - actual)
    if salidas:
        cierre = libro.fecha_salida.isna() & (libro.estrategia == estrategia) & libro.instrumento.isin(salidas)
        libro.loc[cierre, "fecha_salida"] = fecha_senal
        movimientos += [f"cierra {t}" for t in salidas]

    entradas = []
    for ticker in sorted(actual - set(vivas)):
        entradas.append({"estrategia": estrategia, "instrumento": ticker,
                         "fecha_entrada": fecha_senal, "precio_entrada": _precio(precios, ticker, fecha_senal),
                         "fecha_salida": pd.NaT, "origen": "produccion"})
        movimientos.append(f"abre {ticker}")
    if entradas:
        libro = pd.concat([libro, pd.DataFrame(entradas)], ignore_index=True)
    return libro[COLUMNAS], movimientos


def movimientos_de(libro: pd.DataFrame, fechas_senal: dict[str, pd.Timestamp]) -> pd.DataFrame:
    """Lo que se abrió y se cerró en la fecha de señal vigente de cada estrategia.

    Es la única fuente del bloque de movimientos del informe. Antes salía de
    comparar la cartera publicada con la anterior, y eso confundía dos cosas:
    lo que cambió esta semana y lo que hay que comprar para entrar hoy. Tras
    el reinicio el informe decía «Comprar INTC» en la misma página en que la
    tabla decía «comprada el 30-09-2025».

    La mayoría de las semanas esto viene vacío, porque tres de las cuatro
    piezas son mensuales. Un bloque vacío se lee como informe roto, así que
    quien lo dibuje tiene que decirlo con todas sus letras.
    """
    filas = []
    for estrategia, fecha in fechas_senal.items():
        if fecha is None or pd.isna(fecha):
            continue
        fecha = pd.Timestamp(fecha)
        de_la_estrategia = libro.loc[libro.estrategia == estrategia] if len(libro) else libro
        for _, fila in de_la_estrategia.iterrows():
            if pd.notna(fila.fecha_salida) and pd.Timestamp(fila.fecha_salida) == fecha:
                filas.append({"estrategia": estrategia, "instrumento": fila.instrumento,
                              "accion": "VENDER", "fecha": fecha})
            elif pd.isna(fila.fecha_salida) and pd.Timestamp(fila.fecha_entrada) == fecha:
                filas.append({"estrategia": estrategia, "instrumento": fila.instrumento,
                              "accion": "COMPRAR", "fecha": fecha})
    columnas = ["estrategia", "instrumento", "accion", "fecha"]
    if not filas:
        return pd.DataFrame(columns=columnas)
    return pd.DataFrame(filas)[columnas].sort_values(["estrategia", "accion", "instrumento"])


def precios_de_entrada(libro: pd.DataFrame, estrategia: str) -> dict[str, float]:
    """El precio anotado al abrir, que no vuelve a calcularse.

    La fecha ya estaba protegida por el libro; el precio no lo estaba. En una
    copia de trabajo con veinte ruedas de febrero alteradas, el informe pasaba
    de mostrar ITAUCL a $20.900 y +22,9% a mostrarlo a $8.360 y +207,3%. Lo
    que se pagó es un hecho y no se recalcula.

    La variación sí sigue saliendo de la serie ajustada, a propósito: si
    mañana se corrige un dividendo mal fechado, ese número tiene que moverse.
    """
    if libro.empty:
        return {}
    vivas = _vivas(libro, estrategia)
    vivas = vivas.loc[vivas.precio_entrada.notna()]
    return dict(zip(vivas.instrumento, vivas.precio_entrada.astype(float)))


def guardar(libro: pd.DataFrame, ruta: str | Path) -> None:
    libro.sort_values(["estrategia", "fecha_entrada", "instrumento"]).to_csv(
        ruta, index=False, date_format="%Y-%m-%d")
