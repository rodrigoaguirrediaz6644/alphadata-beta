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

import json
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


def movimientos_de(publicada: dict[str, dict[str, str]],
                   vigente: dict[str, dict[str, str]]) -> pd.DataFrame:
    """Qué cambió desde el informe anterior. No desde la fecha de señal.

    Antes esto leía el libro en la fecha de señal vigente, y cualquier cambio
    que el libro situara en una fecha anterior quedaba invisible. No era
    excepcional: **ocurre cada vez que el libro se reconstruye**, o sea cada
    vez que cambia una regla.

    Y ya causó daño. El primer informe dijo «Comprar CENCOMALLS». Al encender
    la SMA200 el recorrido situó su salida en la revisión del 11-09, no en la
    del 17-09, así que el informe siguiente no la tenía y **nunca dijo que la
    vendiera**. Quien la hubiera comprado se quedaba con una posición que el
    modelo ya no tiene y sin ninguna instrucción.

    Lo que el lector necesita no es «qué movimientos hay en la fecha de señal»
    sino «qué cambió desde la última vez que leí». Eso es la diferencia entre
    dos carteras publicadas, venga de donde venga: de una revisión nueva o de
    una reconstrucción del libro.

    `publicada` y `vigente` son `{estrategia: {instrumento: fecha_entrada}}`.
    """
    filas = []
    for estrategia in sorted(set(publicada) | set(vigente)):
        antes = publicada.get(estrategia, {})
        ahora = vigente.get(estrategia, {})
        for instrumento in sorted(set(antes) - set(ahora)):
            filas.append({"estrategia": estrategia, "instrumento": instrumento,
                          "accion": "VENDER", "fecha": pd.NaT})
        for instrumento in sorted(set(ahora) - set(antes)):
            filas.append({"estrategia": estrategia, "instrumento": instrumento,
                          "accion": "COMPRAR", "fecha": pd.to_datetime(ahora[instrumento])})
    columnas = ["estrategia", "instrumento", "accion", "fecha"]
    if not filas:
        return pd.DataFrame(columns=columnas)
    return pd.DataFrame(filas)[columnas].sort_values(["estrategia", "accion", "instrumento"])


def cartera_publicada(ruta: str | Path, as_of=None) -> dict[str, dict[str, str]]:
    """La cartera del último informe emitido con **otra** fecha de referencia.

    Antes guardaba una sola cartera sin fecha, así que re-correr el pipeline el
    mismo día borraba lo que había que comparar: la primera corrida escribía la
    cartera nueva y la segunda no encontraba diferencia. **Las órdenes de venta
    desaparecían en silencio y el informe salía igual de creíble**, porque un
    bloque sin movimientos no se ve roto, se ve como una semana sin cambios. Es
    la misma falla que tenían las series sin recalcular.

    Ahora el archivo guarda una entrada por fecha de referencia y se compara
    contra la última **distinta** de `as_of`. Misma fecha y mismos datos, mismo
    informe, sin importar cuántas veces se corra.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    guardado = json.loads(ruta.read_text(encoding="utf-8"))
    historial = guardado.get("historial")
    if historial is None:                      # formato antiguo, de una sola cartera
        return guardado.get("carteras", {})
    if as_of is None:
        anteriores = sorted(historial)
    else:
        corte = pd.Timestamp(as_of).date().isoformat()
        anteriores = sorted(f for f in historial if f < corte)
        if not anteriores and corte in historial:
            # Re-corrida del mismo día: la base es lo que ya se publicó hoy, no
            # «nada». Sin esto, volver a correr listaba la cartera entera como
            # si fuera nueva.
            anteriores = [corte]
    return historial[anteriores[-1]]["carteras"] if anteriores else {}


def guardar_publicada(carteras: dict[str, dict[str, str]], fecha, ruta: str | Path,
                      maximo: int = 12) -> None:
    """Agrega la cartera de esta fecha sin pisar las anteriores.

    Se conservan las últimas `maximo` fechas: alcanza de sobra para comparar y
    evita que el archivo crezca sin límite.
    """
    ruta = Path(ruta)
    guardado = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    historial = guardado.get("historial")
    if historial is None:
        historial = ({guardado["emitido"]: {"carteras": guardado["carteras"],
                                            "procedencia": guardado.get("procedencia")}}
                     if guardado.get("emitido") and guardado.get("carteras") else {})
    clave = pd.Timestamp(fecha).date().isoformat()
    historial[clave] = {"carteras": carteras}
    for viejo in sorted(historial)[:-maximo]:
        historial.pop(viejo)
    ruta.write_text(json.dumps({"historial": dict(sorted(historial.items()))},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
