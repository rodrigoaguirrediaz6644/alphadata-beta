"""Tabla de dividendos: derivación asistida y alarma por salto.

La decisión tomada es registro manual, ni ignorar los dividendos ni deducirlos
del salto de precio. Ignorarlos sesga el NAV entre 4% y 8% al año en bancos y
utilities chilenas, siempre hacia abajo. Deducirlos del salto es inferir
haciéndolo pasar por dato: no distingue un reparto de una mala impresión ni de
una noticia.

Lo que este módulo hace es **proponer** filas para la tabla a partir de una
fuente ajustada por dividendos, y verificar cada propuesta contra la serie
cruda antes de aceptarla. Lo que no verifica, no entra: se reporta aparte.

## Por qué hace falta la verificación

Comparar una serie ajustada contra el cierre crudo da una razón que cambia en
escalones, y la tentación es leer cada escalón como un dividendo. Medido sobre
los archivos de referencia aparecen dos fenómenos que se ven igual y no lo son:

- **Escalón permanente.** La razón cambia y se queda. SALFACORP pasa de 0,9580
  a 1,0000 el 06-05-2024 y no vuelve. En la serie cruda ese día el precio cae
  de 557,00 a 531,79, un -4,5% que el factor 0,957992 explica. Es un dividendo.

- **Bache transitorio.** La razón se aparta de 1 y vuelve en una semana. CHILE
  marca 0,9263 entre el 17 y el 21 de marzo de 2025 y vuelve a 1,0000 el 24.
  Ahí el dato malo es el nuestro: la fuente ajustada muestra la caída
  ex-dividendo el 17-03 y nuestra serie cruda la retrasa cinco ruedas. No es un
  dividendo que registrar, es un defecto que reportar.

Un escalón sólo se acepta como dividendo si la serie cruda cae en la fecha ex
en la magnitud que el factor predice.
"""

from __future__ import annotations

import pandas as pd

UMBRAL_ESCALON = .002      # un cambio menor es ruido de redondeo entre fuentes
VENTANA_MEDIANA = 5        # suaviza los días sueltos en que las fuentes difieren
TOLERANCIA_CRUCE = .25     # cuánto puede alejarse la caída real de la predicha
COLUMNAS = ["alphadata_ticker", "fecha_ex", "factor", "dividendo_pct", "caida_cruda", "veredicto"]


def _escalones(razon: pd.Series, umbral: float, ventana: int) -> list[tuple[pd.Timestamp, float, float]]:
    """Fechas donde la razón cambia de nivel, con el nivel de antes y de después."""
    suave = razon.rolling(ventana, center=True, min_periods=1).median()
    cambio = (suave / suave.shift(1) - 1).abs()
    salidas = []
    for fecha in suave.index[cambio > umbral]:
        i = suave.index.get_loc(fecha)
        if i == 0:
            continue
        salidas.append((fecha, float(suave.iloc[i - 1]), float(suave.iloc[i])))
    return salidas


def _es_permanente(razon: pd.Series, fecha: pd.Timestamp, despues: float, dias: int = 20,
                   umbral: float = UMBRAL_ESCALON) -> bool:
    """El nivel nuevo se sostiene, en vez de revertir a los pocos días."""
    posteriores = razon.loc[razon.index > fecha].head(dias)
    if posteriores.empty:
        return False
    return bool((posteriores / despues - 1).abs().median() <= umbral * 2)


def proponer(ajustada: pd.Series, cruda: pd.Series, ticker: str,
             umbral: float = UMBRAL_ESCALON, ventana: int = VENTANA_MEDIANA,
             tolerancia: float = TOLERANCIA_CRUCE) -> pd.DataFrame:
    """Propone filas de dividendo y clasifica cada escalón encontrado.

    El veredicto es uno de:

    - `dividendo`: escalón permanente y la caída de la serie cruda en la fecha
      ex coincide con la que el factor predice. Es candidato a entrar a la tabla.
    - `sin_respaldo`: escalón permanente, pero la serie cruda no cae como
      debería. No se registra; hay que mirarlo a mano.
    - `bache_transitorio`: la razón vuelve a su nivel anterior. Es un defecto de
      datos en una de las dos fuentes, no un reparto.
    """
    comun = ajustada.index.intersection(cruda.index)
    if len(comun) < ventana * 2:
        return pd.DataFrame(columns=COLUMNAS)
    razon = (ajustada.loc[comun] / cruda.loc[comun]).replace([float("inf"), float("-inf")], pd.NA).dropna()
    crudo = cruda.loc[razon.index]
    filas = []
    for fecha, antes, despues in _escalones(razon, umbral, ventana):
        factor = antes / despues
        dividendo = 1 - factor
        i = crudo.index.get_loc(fecha)
        caida = float(crudo.iloc[i] / crudo.iloc[i - 1] - 1) if i > 0 else float("nan")
        if not _es_permanente(razon, fecha, despues, umbral=umbral):
            veredicto = "bache_transitorio"
        elif dividendo > 0 and pd.notna(caida) and abs(caida + dividendo) <= max(tolerancia * dividendo, .005):
            veredicto = "dividendo"
        else:
            veredicto = "sin_respaldo"
        filas.append({"alphadata_ticker": ticker, "fecha_ex": fecha, "factor": factor,
                      "dividendo_pct": dividendo, "caida_cruda": caida, "veredicto": veredicto})
    return pd.DataFrame(filas, columns=COLUMNAS)


def alarma_por_salto(precios: pd.DataFrame, dividendos: pd.DataFrame | None = None,
                     umbral: float = .05) -> pd.DataFrame:
    """Caídas fuertes sin dividendo registrado para esa fecha.

    No ajusta nada: sólo impide que la tabla manual se quede atrás sin que
    nadie se entere, que es el riesgo real de anotar a mano.
    """
    datos = precios.copy()
    datos["date"] = pd.to_datetime(datos["date"], errors="coerce")
    panel = datos.dropna(subset=["date"]).pivot_table(index="date", columns="alphadata_ticker",
                                                      values="close", aggfunc="last").sort_index()
    registrados = set()
    if dividendos is not None and len(dividendos):
        conocidos = dividendos.copy()
        conocidos["fecha_ex"] = pd.to_datetime(conocidos["fecha_ex"], errors="coerce")
        registrados = set(zip(conocidos.alphadata_ticker, conocidos.fecha_ex))
    filas = []
    for ticker in panel.columns:
        retornos = panel[ticker].dropna().pct_change().dropna()
        for fecha, retorno in retornos[retornos <= -umbral].items():
            if (ticker, fecha) in registrados:
                continue
            filas.append({"alphadata_ticker": ticker, "date": fecha, "retorno": float(retorno)})
    return pd.DataFrame(filas, columns=["alphadata_ticker", "date", "retorno"])
