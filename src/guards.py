"""Guardias sobre los precios. Las tres frenan, no sólo avisan.

Vienen del incidente de septiembre de 2026: el feed chileno llevaba dos meses
entregando el mismo cierre repetido y `coverage_report.csv` decía `status OK`
con `lag_business_days 0` para cada uno de esos papeles, porque contaba filas y
medía el rezago de la fecha pero nunca comprobaba si los valores cambiaban.

Un dato que no cambia puede ser un dato muerto.
"""

from __future__ import annotations

import pandas as pd

# Calibrado con los datos, no supuesto. Entre enero de 2025 y el 16-07-2026 la
# racha más larga sin cambio de precio de todo el universo fue de 19 ruedas
# (INGEVEC), seguida de 14 (INDISA) y 10 (HITES): son papeles que no transan
# todos los días, no series muertas. En la ventana congelada la racha más corta
# fue de 23. El umbral va en medio.
MAX_RUEDAS_SIN_VARIACION = 20
# Un feed caído no se nota en un instrumento sino en todos a la vez. En periodo
# sano la fracción de instrumentos sin cambio de precio en una misma rueda tuvo
# mediana 10,3% y nunca pasó de 25,6% en 383 ruedas. El 20-07-2026, primera
# rueda tras el congelamiento, fue 100%.
FRACCION_MERCADO_DETENIDO = .5
UMBRAL_CONTRASTE = .01
UMBRAL_ADR = .01
VENTANA_ADR = 5

# El ADR cotiza en Nueva York y no depende del feed chileno: si se mueve
# mientras su acción local no, el mercado local está detenido, no quieto.
PARES_ADR = {"LTM-ADR": "LTM", "SQM-ADR": "SQM-B"}


def _panel(precios: pd.DataFrame, columna: str = "adjusted_close") -> pd.DataFrame:
    if precios is None or precios.empty or "date" not in precios:
        return pd.DataFrame()
    # El ajustado es el preferido, pero no siempre está: un panel recién
    # descargado o una fuente de contraste pueden traer sólo el cierre crudo.
    if columna not in precios:
        columna = "close" if "close" in precios else None
    if columna is None:
        return pd.DataFrame()
    datos = precios.copy()
    datos["date"] = pd.to_datetime(datos["date"], errors="coerce")
    return datos.dropna(subset=["date"]).pivot_table(index="date", columns="alphadata_ticker", values=columna, aggfunc="last").sort_index()


def ruedas_sin_variacion(precios: pd.DataFrame, columna: str = "adjusted_close") -> pd.Series:
    """Cuántas ruedas lleva cada instrumento con el mismo precio."""
    panel = _panel(precios, columna)
    if panel.empty:
        return pd.Series(dtype=int)
    cuenta = {}
    for ticker in panel.columns:
        serie = panel[ticker].dropna()
        if serie.empty:
            cuenta[ticker] = 0
            continue
        cambios = serie[serie.diff().fillna(1) != 0]
        ultimo = cambios.index.max() if len(cambios) else serie.index.min()
        cuenta[ticker] = int((serie.index > ultimo).sum())
    return pd.Series(cuenta, dtype=int).sort_values(ascending=False)


def series_detenidas(precios: pd.DataFrame, maximo: int = MAX_RUEDAS_SIN_VARIACION,
                     columna: str = "adjusted_close") -> pd.Index:
    """Instrumentos que hay que excluir de la valorización."""
    cuenta = ruedas_sin_variacion(precios, columna)
    return cuenta[cuenta > maximo].index


def ruedas_faltantes(precios: pd.DataFrame, locales: set[str], referencia: str = "LTM-ADR",
                     desde: pd.Timestamp | None = None) -> pd.DatetimeIndex:
    """Ruedas en que el testigo operó y ninguna acción local quedó grabada.

    Desde que el cierre chileno se toma de la cotización viva, un día perdido
    es irrecuperable: el arreglo histórico está congelado y `meta` sólo guarda
    el último. Antes esto no importaba, porque cada descarga traía la historia
    completa.

    El testigo por defecto es un ADR, que cotiza en Nueva York y cuyo historial
    sí funciona. Los calendarios no coinciden, así que los feriados chilenos
    aparecen como falsos positivos: son pocos al año y se revisan a mano, que
    es mejor que no enterarse de un día perdido.
    """
    panel = _panel(precios)
    if panel.empty or referencia not in panel:
        return pd.DatetimeIndex([])
    testigo = panel[referencia].dropna()
    presentes = panel[[c for c in panel.columns if c in locales]]
    if presentes.empty:
        return pd.DatetimeIndex([])
    con_dato = presentes.dropna(how="all").index
    faltan = testigo.index.difference(con_dato)
    return faltan[faltan >= desde] if desde is not None else faltan


def fraccion_sin_variacion(precios: pd.DataFrame, instrumentos: set[str] | None = None,
                           columna: str = "adjusted_close") -> pd.Series:
    """Por rueda, qué proporción de los instrumentos no movió su precio."""
    panel = _panel(precios, columna)
    if panel.empty:
        return pd.Series(dtype=float)
    if instrumentos:
        panel = panel[[c for c in panel.columns if c in instrumentos]]
    if panel.empty or panel.shape[1] == 0:
        return pd.Series(dtype=float)
    disponibles = panel.notna().sum(axis=1)
    return ((panel.diff() == 0).sum(axis=1) / disponibles.replace(0, pd.NA)).dropna()


def feed_detenido(precios: pd.DataFrame, instrumentos: set[str] | None = None,
                  umbral: float = FRACCION_MERCADO_DETENIDO, ruedas: int = 1) -> pd.DatetimeIndex:
    """Ruedas en que el mercado entero dejó de moverse, que es un feed caído.

    Es la guardia que habría avisado el mismo 20-07-2026 en vez de dos meses
    después, y la más robusta de todas: separa 25,6% de 92,3%.

    El volumen, que parecía el discriminador natural entre un papel que no
    transó y un feed muerto, **no sirve**: durante el congelamiento el
    proveedor entregó volumen cero en las 31 ruedas de todos los instrumentos
    afectados, igual que un papel ilíquido. Los dos casos se ven idénticos mirando
    un instrumento; se separan mirando el mercado completo.
    """
    fraccion = fraccion_sin_variacion(precios, instrumentos)
    if fraccion.empty:
        return pd.DatetimeIndex([])
    # La guardia pregunta si el feed está caído **ahora**, así que mira sólo las
    # últimas `ruedas` jornadas. Escanear toda la historia la vuelve inútil: hay
    # cinco ruedas antiguas con el mercado entero quieto —31-12-2015,
    # 19-04-2017 y tres días de octubre de 2024, feriados o huecos del dato
    # viejo— y con ellas dentro la corrida quedaba bloqueada para siempre por
    # algo ocurrido hace dos años. Con `ruedas=0` se revisa todo, que es lo que
    # hacen las pruebas de regresión sobre el incidente.
    ventana = fraccion if not ruedas else fraccion.tail(ruedas)
    return pd.DatetimeIndex(ventana.index[ventana > umbral])


def contraste_entre_fuentes(principal: pd.DataFrame, contraste: pd.DataFrame,
                            umbral: float = UMBRAL_CONTRASTE, columna: str = "close") -> pd.DataFrame:
    """Fechas en que las dos fuentes no dicen lo mismo del mismo cierre."""
    a, b = _panel(principal, columna), _panel(contraste, columna)
    tickers = a.columns.intersection(b.columns)
    fechas = a.index.intersection(b.index)
    filas = []
    for ticker in tickers:
        x, y = a.loc[fechas, ticker], b.loc[fechas, ticker]
        desvio = (x / y - 1).abs()
        for fecha in desvio[desvio > umbral].dropna().index:
            filas.append({"alphadata_ticker": ticker, "date": fecha, "principal": float(x.loc[fecha]),
                          "contraste": float(y.loc[fecha]), "desvio": float(desvio.loc[fecha])})
    return pd.DataFrame(filas, columns=["alphadata_ticker", "date", "principal", "contraste", "desvio"])


def adr_contra_local(precios: pd.DataFrame, pares: dict[str, str] | None = None,
                     ventana: int = VENTANA_ADR, umbral: float = UMBRAL_ADR) -> pd.DataFrame:
    """Delata un mercado local detenido usando el ADR como testigo.

    Si en la ventana el ADR se movió más que `umbral` y la acción local no se
    movió nada, el problema no es que la acción esté quieta: es que su feed
    dejó de publicar. Habría delatado el incidente el 18-07-2026.
    """
    pares = pares or PARES_ADR
    panel = _panel(precios)
    filas = []
    if panel.empty:
        return pd.DataFrame(columns=["adr", "local", "movimiento_adr", "movimiento_local", "desde", "hasta"])
    for adr, local in pares.items():
        if adr not in panel or local not in panel:
            continue
        a = panel[adr].dropna().tail(ventana)
        l = panel[local].dropna().tail(ventana)
        if len(a) < 2 or len(l) < 2:
            continue
        mov_adr = abs(a.iloc[-1] / a.iloc[0] - 1)
        mov_local = abs(l.iloc[-1] / l.iloc[0] - 1)
        variaciones_locales = int((l.diff().fillna(0) != 0).sum())
        if mov_adr > umbral and variaciones_locales == 0:
            filas.append({"adr": adr, "local": local, "movimiento_adr": float(mov_adr),
                          "movimiento_local": float(mov_local), "desde": l.index.min(), "hasta": l.index.max()})
    return pd.DataFrame(filas, columns=["adr", "local", "movimiento_adr", "movimiento_local", "desde", "hasta"])
