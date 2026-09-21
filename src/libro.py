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


def abiertas(libro: pd.DataFrame, estrategia: str) -> dict[str, pd.Timestamp]:
    """Las posiciones vivas de una estrategia, con su fecha de entrada."""
    if libro.empty:
        return {}
    vivas = libro.loc[(libro.estrategia == estrategia) & libro.fecha_salida.isna()]
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


def guardar(libro: pd.DataFrame, ruta: str | Path) -> None:
    libro.sort_values(["estrategia", "fecha_entrada", "instrumento"]).to_csv(
        ruta, index=False, date_format="%Y-%m-%d")
