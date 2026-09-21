"""Reconstruye el libro de posiciones: cuándo entró cada una y a qué precio.

    PYTHONPATH=. python -m tools.construir_libro              # ensayo
    PYTHONPATH=. python -m tools.construir_libro --confirmar  # escribe

El informe mostraba las veintiuna posiciones abiertas el 17-09-2026, que es
fiel a lo que hizo el sistema al reiniciarse pero no a lo que dice la
estrategia: no distingue una posición recién tomada de una que viene corriendo
ocho meses y se vende en la próxima revisión.

## Qué hace y qué no

Entrega **fechas y precios de entrada**. No entrega NAV, y esa línea no se
cruza: `data/strategy_nav.csv` se queda en 100 desde el 16-09-2026.

Una posición va a mostrar +8% mientras su estrategia muestra −0,1%, y **eso no
es una contradicción**. La ganancia no realizada de una posición desde que se
compró y el rendimiento de la cartera en un periodo son dos mediciones
distintas, como en cualquier cartola. Encadenarlas es exactamente lo que
fabricó el +30% que este proyecto vino a terminar.

## Las condiciones del recorrido

- **Con los módulos de producción.** Las mismas funciones `sigma6`, `delta12`,
  `gamma6` y `oro` que corren los viernes. Un script paralelo mediría el script
  paralelo.
- **Sin mirar hacia adelante.** En cada revisión el almacén se corta en esa
  fecha. Es el error más fácil de cometer acá y el más difícil de detectar
  después, porque produce un libro perfectamente verosímil.
- **Las recomendaciones se filtran por `available_at`**, que es lo que hace
  `sigma6`: una recomendación publicada el martes y disponible el jueves no se
  pudo usar el miércoles.
- **Cada estrategia con su calendario**: Delta-12 y Gamma-6 mensuales, Sigma-6
  semanal.
- **La serie de precios entra completa hacia atrás.** El momentum 12-1 necesita
  doce meses previos, aunque las entradas que se muestran empiecen en 2025.
- **El recorrido se calienta un año antes de lo que publica.** Ver
  `DESDE_CALENTAMIENTO`.

## La prueba que decide si esto se publica

Llevado hasta el 17-09-2026, el recorrido tiene que reproducir **exactamente**
las carteras publicadas. Si no calzan, no está reproduciendo producción y el
libro no vale nada: se reporta la discrepancia y no se escribe. No se ajusta el
recorrido hasta que calce, que es otra forma de inventar el resultado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.fetch_prices import load_universe
from src.strategy_engine import (delta12, gamma6, oro, sigma6, to_clp, validate_recommendations)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
# Dos fechas distintas, que antes eran una sola.
#
# El recorrido arranca un año antes de lo que publica. Las cuatro piezas son
# dependientes del camino —Sigma-6 tiene tope de tenencia, Delta-12 usa el RSI
# como condición de permanencia, Gamma-6 filtra por tendencia— así que el
# estado al entrar a la ventana condiciona todas las fechas posteriores.
# Arrancando en 2025, BCI quedaba con entrada el 16-01-2026; con calentamiento
# queda el 24-10-2025, y ésa es la correcta.
#
# Un año basta, y para Sigma-6 no es sólo empírico: su tope es de 365 días, así
# que el camino desde 365 días antes determina el estado. Para Delta-12 y
# Gamma-6, que no tienen tope, la suficiencia **es empírica**: se midió que
# 2024, 2023 y 2021 dan exactamente las mismas fechas, no se demostró que no
# puedan cambiar. Si alguna de esas dos reglas se modifica, hay que volver a
# medirlo.
DESDE_CALENTAMIENTO = pd.Timestamp("2024-01-02")
# Piso de publicación. Hacia atrás no hay dato reparado en que confiar, así que
# las filas del tramo de calentamiento se conservan para auditar y para los
# contadores de tenencia, pero no se muestran nunca ni llevan precio.
DESDE, HASTA = pd.Timestamp("2025-01-02"), pd.Timestamp("2026-09-17")
CALENTAMIENTO = "calentamiento"
# El oro no tiene señal: entra por decisión. El 01-01-2026 es feriado y no hay
# precio, así que la fecha mostrada es la pedida y el precio de entrada es el
# cierre de la primera rueda de 2026. No es un error que corregir.
ORO_FECHA_DECISION = pd.Timestamp("2026-01-01")
COLUMNAS = ["estrategia", "instrumento", "fecha_entrada", "precio_entrada",
            "fecha_salida", "origen"]


def _sesiones(precios: pd.DataFrame, tickers: set[str]) -> pd.DatetimeIndex:
    fechas = precios.loc[precios.alphadata_ticker.isin(tickers), "date"]
    return pd.DatetimeIndex(sorted(pd.to_datetime(fechas).unique()))


def _revisiones(sesiones: pd.DatetimeIndex, periodo: str, desde, hasta) -> list[pd.Timestamp]:
    """Las fechas de señal de una estrategia, con su propio calendario.

    Para las mensuales se descarta el mes en curso, y no es un ajuste: es la
    regla de producción. `run_pipeline` calcula el corte como
    `as_of.to_period('M') - 1`, o sea el último día del **mes anterior**, y
    mantiene esa cartera durante el mes siguiente. Tomando el 17-09 como
    revisión se obtenía una cartera distinta de la publicada, porque septiembre
    todavía no termina.
    """
    dentro = sesiones[(sesiones >= desde) & (sesiones <= hasta)]
    if dentro.empty:
        return []
    grupos = pd.Series(dentro, index=dentro).groupby(dentro.to_period(periodo)).max()
    if periodo == "M":
        grupos = grupos[grupos.index < pd.Timestamp(hasta).to_period("M")]
    return [pd.Timestamp(f) for f in grupos]


def recorrer(nombre: str, revisiones: list[pd.Timestamp], elegir) -> tuple[list[dict], set[str]]:
    """Camina las revisiones anotando aperturas y cierres."""
    abiertas: dict[str, pd.Timestamp] = {}
    movimientos: list[dict] = []
    for fecha in revisiones:
        actual = set(elegir(fecha))
        for ticker in sorted(set(abiertas) - actual):
            movimientos.append({"estrategia": nombre, "instrumento": ticker,
                                "fecha_entrada": abiertas.pop(ticker), "fecha_salida": fecha})
        for ticker in sorted(actual - set(abiertas)):
            abiertas[ticker] = fecha
    for ticker, entrada in abiertas.items():
        movimientos.append({"estrategia": nombre, "instrumento": ticker,
                            "fecha_entrada": entrada, "fecha_salida": pd.NaT})
    return movimientos, set(abiertas)


def precio_de(precios: pd.DataFrame, ticker: str, fecha: pd.Timestamp) -> float | None:
    """El cierre crudo de la fecha de entrada: lo que habrías pagado.

    En pesos también para Gamma-6 y el oro, que se compran en Chile como CDV y
    cuyo precio el informe muestra convertido. Guardarlo en dólares haría que
    la variación se calculara contra un precio de hoy en pesos, y el número
    saldría absurdo.
    """
    filas = precios.loc[(precios.alphadata_ticker == ticker) & (precios.date == fecha), "close"].dropna()
    return float(filas.iloc[0]) if len(filas) else None


def main(confirmar: bool = False) -> int:
    universo = load_universe()
    precios = pd.read_csv(DATA / "market_prices_daily.csv", parse_dates=["date"])
    crudo = pd.read_csv(DATA / "recommendations_input.csv", dtype=str).fillna("")
    validas, _ = validate_recommendations(crudo, set(universo.alphadata_ticker))

    # Los precios de los instrumentos en dólares se convierten a pesos, igual
    # que hace el informe, para que el precio de entrada y el de hoy estén en
    # la misma moneda.
    fx = precios.loc[precios.alphadata_ticker == "USDCLP"]
    precios_mostrados = to_clp(precios, universo, fx)
    locales = set(universo.loc[universo.tipo.isin({"accion_local", "accion_sigma"}), "alphadata_ticker"])
    us = set(universo.loc[universo.tipo == "accion_us", "alphadata_ticker"])
    etf = set(universo.loc[universo.tipo == "etf_us", "alphadata_ticker"])
    ses_cl, ses_us = _sesiones(precios, locales), _sesiones(precios, us)

    # Sin mirar hacia adelante: en cada revisión el almacén se corta ahí.
    def hasta_la_fecha(fecha):
        return precios.loc[precios.date <= fecha]

    estado = {"sigma_entries": {}}

    def elegir_sigma(fecha):
        nonlocal estado
        cartera, _, estado = sigma6(validas, hasta_la_fecha(fecha), fecha, estado)
        return list(cartera.ticker)

    def elegir_delta(fecha):
        return list(delta12(hasta_la_fecha(fecha), universo, fecha)[0].ticker)

    def elegir_gamma(fecha):
        return list(gamma6(hasta_la_fecha(fecha), universo, fecha)[0].ticker)

    print(f"Recorrido de {DESDE_CALENTAMIENTO.date()} a {HASTA.date()}; "
          f"se publica desde {DESDE.date()}")
    recorridos, vivas = [], {}
    for nombre, revisiones, elegir in [
            ("Sigma-6", _revisiones(ses_cl, "W-FRI", DESDE_CALENTAMIENTO, HASTA), elegir_sigma),
            ("Delta-12", _revisiones(ses_cl, "M", DESDE_CALENTAMIENTO, HASTA), elegir_delta),
            ("Gamma-6", _revisiones(ses_us, "M", DESDE_CALENTAMIENTO, HASTA), elegir_gamma)]:
        movimientos, abiertas = recorrer(nombre, revisiones, elegir)
        print(f"  {nombre:<9} {len(revisiones):>3} revisiones   "
              f"{len(movimientos):>3} posiciones anotadas   {len(abiertas)} abiertas al final")
        recorridos.extend(movimientos)
        vivas[nombre] = abiertas

    # El oro entra por decisión, sin señal. Ver ORO_FECHA_DECISION.
    cartera_oro, _ = oro(precios.loc[precios.alphadata_ticker.isin(etf)], universo, HASTA)
    for ticker in cartera_oro.ticker:
        recorridos.append({"estrategia": "Oro", "instrumento": ticker,
                           "fecha_entrada": ORO_FECHA_DECISION, "fecha_salida": pd.NaT})
    vivas["Oro"] = set(cartera_oro.ticker)

    print("\nPRUEBA DE ACEPTACIÓN — reproducir las carteras publicadas:")
    publicadas = {}
    for nombre, archivo in [("Sigma-6", "portfolio_sigma6"), ("Delta-12", "portfolio_delta12"),
                            ("Gamma-6", "portfolio_gamma6"), ("Oro", "portfolio_oro")]:
        publicadas[nombre] = set(pd.read_csv(DATA / f"{archivo}.csv").ticker)
    todo_calza = True
    for nombre, esperada in publicadas.items():
        obtenida = vivas.get(nombre, set())
        calza = obtenida == esperada
        todo_calza &= calza
        marca = "calza" if calza else "NO CALZA"
        print(f"  {nombre:<9} {marca:<9} publicada {len(esperada)}, recorrido {len(obtenida)}")
        if not calza:
            print(f"      sobran  {sorted(obtenida - esperada) or '-'}")
            print(f"      faltan  {sorted(esperada - obtenida) or '-'}")
    if not todo_calza:
        print("\nEl recorrido no reproduce producción. No se escribe el libro: "
              "uno que no calza con lo que el sistema tiene hoy es peor que no tenerlo.")
        return 1
    print("  las cuatro carteras reproducidas exactamente.")

    libro = pd.DataFrame(recorridos)
    entradas = pd.to_datetime(libro.fecha_entrada)
    calienta = (entradas < DESDE) & (libro.estrategia != "Oro")
    libro["origen"] = [CALENTAMIENTO if c else "recorrido" for c in calienta]
    libro["precio_entrada"] = [
        None if c
        else precio_de(precios_mostrados, f.instrumento,
                       f.fecha_entrada if f.estrategia != "Oro"
                       else ses_us[ses_us >= ORO_FECHA_DECISION][0])
        for c, f in zip(calienta, libro.itertuples())]
    libro = libro[COLUMNAS].sort_values(["estrategia", "fecha_entrada", "instrumento"])

    # Una posición del tramo de calentamiento que siguiera abierta desaparecería
    # del informe, porque no lleva precio. Hoy no hay ninguna; si aparece, hay
    # que decidirla a mano y no dejarla pasar en silencio.
    colgada = libro[(libro.origen == CALENTAMIENTO) & libro.fecha_salida.isna()]
    if len(colgada):
        print("\nHay posiciones del calentamiento todavía abiertas; no se escribe:")
        print(colgada.to_string(index=False))
        return 1
    print(f"\n{int(calienta.sum())} filas del tramo de calentamiento: se conservan "
          f"como '{CALENTAMIENTO}', sin precio, y no se publican.")

    abiertas = libro[libro.fecha_salida.isna()]
    print(f"\nLibro: {len(libro)} posiciones, {len(abiertas)} abiertas al 17-09-2026.")
    print(abiertas.assign(fecha_entrada=lambda d: pd.to_datetime(d.fecha_entrada).dt.date)[
        ["estrategia", "instrumento", "fecha_entrada", "precio_entrada"]].to_string(index=False))

    if not confirmar:
        print("\nEnsayo: no se escribió nada. Repetir con --confirmar.")
        return 0
    libro.to_csv(DATA / "libro_posiciones.csv", index=False, date_format="%Y-%m-%d")
    print(f"\nEscrito data/libro_posiciones.csv con {len(libro)} filas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--confirmar" in sys.argv))
