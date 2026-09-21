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

import json
import urllib.request

import numpy as np
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


# --- la tabla: el proveedor declara, el precio confirma ---------------------

AGENTE = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
VENTANA_BUSQUEDA = (-10, 2)   # ruedas alrededor de la fecha declarada
TOLERANCIA_MINIMA = .005
VECES_LA_VOLATILIDAD = 2.0
# Por debajo de este tamaño —la caída esperada medida en tolerancias— buscar la
# fecha en el precio no informa nada. Medido con una prueba nula sobre 1.480
# fechas sin dividendo, usando los montos reales de cada papel y la misma
# ventana de búsqueda, la tasa de falsos positivos es:
#
#     tamaño < 0,5      100,0%
#     0,5 a 1            99,7%
#     1 a 2              74,7%
#     2 a 4               6,1%
#     > 4                 0,0%
#
# O sea: en una serie ruidosa el confirmador encuentra una caída del tamaño
# pedido casi siempre, aunque no haya habido dividendo. Sólo por encima de 2
# tolerancias la confirmación significa algo.
UMBRAL_CONFIRMABLE = 2.0
# Para los que no se pueden confirmar se usa la convención chilena, medida
# sobre los que sí: la fecha ex está 5 ruedas antes de la que declara el
# proveedor (mediana 5, cuartiles 4 y 5, en los calces fiables).
DESFASE_POR_CONVENCION = 5
# Dos instrumentos, dos columnas, cada una con su etiqueta. `caida_observada`
# es el metodo por precio: mide el retorno crudo de la rueda ex, que trae la
# caida del dividendo **mas el movimiento del mercado de ese dia**.
# `caida_por_contraste` mide la razon entre las dos fuentes del mismo dia, donde
# ese movimiento se cancela, y resulta entre cuatro y diez veces mas preciso
# sobre los dividendos que los dos alcanzan. Ver
# research/dividendos/CONFIRMACION_POR_CONTRASTE.md.
#
# Un dividendo que los dos confirman esta mejor respaldado que uno con
# cualquiera de los dos solo, y por eso las columnas conviven en vez de
# pisarse. La consecuencia hay que asumirla: **los confirmados solo por precio
# son la evidencia mas debil de la tabla, no la mas fuerte.**
COLUMNAS_TABLA = ["alphadata_ticker", "fecha_ex", "monto", "fecha_declarada", "tamano",
                  "caida_esperada", "caida_observada", "error",
                  "caida_por_contraste", "error_contraste", "origen"]
CONFIRMADA = "confirmada por el precio"
POR_CONTRASTE = "confirmada por contraste entre fuentes"
POR_AMBOS = "confirmada por precio y contraste"


def confirmada_por_precio(origen) -> bool:
    return str(origen) in {CONFIRMADA, POR_AMBOS}
POR_CONVENCION = f"fecha por convención ({DESFASE_POR_CONVENCION} ruedas antes de la declarada)"


def descargar_eventos(yahoo_ticker: str, desde: pd.Timestamp, hasta: pd.Timestamp,
                      timeout: int = 30) -> list[dict]:
    """Dividendos declarados por el proveedor, con fecha y monto.

    El arreglo histórico de los `.SN` sigue congelado, pero el bloque de
    eventos de la misma respuesta sí llega: son cosas distintas dentro del
    mismo JSON.
    """
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}"
           f"?period1={int(desde.timestamp())}&period2={int(hasta.timestamp())}"
           "&interval=1d&events=div")
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENTE), timeout=timeout) as respuesta:
        cuerpo = json.load(respuesta)
    eventos = cuerpo["chart"]["result"][0].get("events", {}).get("dividends", {})
    return [{"fecha_declarada": pd.Timestamp(int(k), unit="s").normalize(), "monto": float(v["amount"])}
            for k, v in sorted(eventos.items(), key=lambda x: int(x[0]))]


def tolerancia_de(cruda: pd.Series, veces: float = VECES_LA_VOLATILIDAD,
                  minima: float = TOLERANCIA_MINIMA) -> float:
    """Cuánto puede alejarse la caída observada de la esperada.

    No es un umbral fijo, y la razón es aritmética: lo que se observa el día ex
    es `-monto/precio` **más el movimiento del mercado de ese día**. El residuo
    después de quitar el dividendo es ese movimiento, así que la tolerancia
    tiene que ser del tamaño del ruido diario del propio instrumento.

    Con un punto porcentual fijo quedaban fuera 18 dividendos, y 17 de ellos
    tenían un error menor a 1,4 veces la volatilidad diaria de su papel: se
    rechazaban por haber caído en un día movido, no por estar mal fechados. El
    único con error de 3,5 volatilidades —VAPORES, mayo de 2025— sigue fuera.
    """
    retornos = pd.to_numeric(cruda, errors="coerce").dropna().pct_change().dropna()
    if len(retornos) < 30:
        return max(minima, .01)
    return max(minima, veces * float(retornos.tail(500).std()))


def localizar_fecha_ex(cruda: pd.Series, fecha_declarada: pd.Timestamp, monto: float,
                       ventana: tuple[int, int] = VENTANA_BUSQUEDA,
                       tolerancia: float | None = None) -> dict | None:
    """Encuentra la rueda en que el precio cayó lo que el dividendo predice.

    El proveedor no declara la fecha ex sino una posterior. Medido sobre 113
    dividendos chilenos: sólo 3 caen en la fecha declarada, el desfase mediano
    es de 5 ruedas, y la caída ocurre antes de la fecha declarada en 71 de los
    113 casos. En Chile el derecho a dividendo se fija días hábiles antes del
    pago, así que la acción transa ex- bastante antes de la fecha del evento.

    **No se aplica un corrimiento fijo**, porque el desfase no es constante: va
    de 0 a 9 ruedas. Se busca en una ventana la rueda cuya caída coincide con
    la que el monto predice, y sólo se acepta si coincide dentro de la
    tolerancia. El monto lo declara el proveedor; la fecha la confirma el
    precio. Lo que no calza no entra: se reporta para confirmarlo a mano.
    """
    cruda = pd.to_numeric(cruda, errors="coerce").dropna().sort_index()
    if len(cruda) < 2:
        return None
    if tolerancia is None:
        tolerancia = tolerancia_de(cruda)
    posicion = int(cruda.index.searchsorted(fecha_declarada))
    previas = cruda.iloc[:posicion]
    if previas.empty or previas.iloc[-1] <= 0:
        return None
    tamano = (monto / previas.iloc[-1]) / tolerancia

    if tamano < UMBRAL_CONFIRMABLE:
        # El precio no puede decir nada: se usa la convención y se marca como tal.
        indice = max(0, posicion - DESFASE_POR_CONVENCION)
        return {"fecha_ex": cruda.index[indice], "tamano": tamano,
                "caida_esperada": -monto / previas.iloc[-1], "caida_observada": np.nan,
                "error": np.nan, "origen": POR_CONVENCION, "rechazado": False}

    desde, hasta = max(1, posicion + ventana[0]), min(len(cruda) - 1, posicion + ventana[1])
    if desde > hasta:
        return None
    mejor = None
    for i in range(desde, hasta + 1):
        anterior, actual = cruda.iloc[i - 1], cruda.iloc[i]
        if anterior <= 0:
            continue
        esperada = -monto / anterior
        observada = actual / anterior - 1
        error = abs(observada - esperada)
        if mejor is None or error < mejor["error"]:
            mejor = {"fecha_ex": cruda.index[i], "caida_esperada": esperada,
                     "caida_observada": observada, "error": error}
    if mejor is None:
        return None
    return {**mejor, "tamano": tamano, "origen": CONFIRMADA, "rechazado": mejor["error"] > tolerancia}


def factores(dividendos: pd.DataFrame, cruda: pd.Series) -> pd.Series:
    """Factor acumulado de ajuste por fecha: el producto de los repartos futuros.

    `adjusted_close(t) = close(t) x factor(t)`, donde el factor es el producto
    de `(1 - monto/cierre_previo)` sobre todas las fechas ex posteriores a `t`.
    Es el ajuste estándar hacia atrás, y calcularlo desde el crudo más la tabla
    es lo que cierra el círculo del almacén: lo inmutable se guarda, lo que
    cambia hacia atrás se deriva.
    """
    cruda = pd.to_numeric(cruda, errors="coerce").dropna().sort_index()
    factor = pd.Series(1.0, index=cruda.index)
    if dividendos is None or dividendos.empty or cruda.empty:
        return factor
    eventos = dividendos.copy()
    eventos["fecha_ex"] = pd.to_datetime(eventos["fecha_ex"], errors="coerce")
    for evento in eventos.dropna(subset=["fecha_ex"]).itertuples(index=False):
        previas = cruda.loc[cruda.index < evento.fecha_ex]
        if previas.empty or previas.iloc[-1] <= 0:
            continue
        unitario = 1 - float(evento.monto) / previas.iloc[-1]
        if not (0 < unitario <= 1):
            continue
        factor.loc[factor.index < evento.fecha_ex] *= unitario
    return factor


def derivar_ajustado(crudo: pd.DataFrame, dividendos: pd.DataFrame) -> pd.Series:
    """Recalcula `adjusted_close` desde el cierre crudo y la tabla de dividendos."""
    salida = pd.Series(index=crudo.index, dtype=float)
    for ticker, grupo in crudo.groupby("alphadata_ticker"):
        serie = grupo.set_index("date")["close"]
        propios = dividendos.loc[dividendos.alphadata_ticker == ticker] if len(dividendos) else dividendos
        f = factores(propios, serie)
        salida.loc[grupo.index] = (serie * f).reindex(serie.index).to_numpy()
    return salida


def detectar_nuevos(tabla: pd.DataFrame, pendientes: pd.DataFrame,
                    eventos: list[dict], ticker: str) -> list[dict]:
    """Eventos del proveedor que todavía no están en la tabla ni pendientes.

    Sin esto la tabla nace correcta y se degrada sola: el próximo reparto de
    cualquiera de los cuarenta instrumentos produciría un ajustado equivocado
    en silencio, que es exactamente el modo de falla que este trabajo vino a
    terminar.
    """
    conocidas = set()
    for origen in (tabla, pendientes):
        if origen is None or origen.empty or "fecha_declarada" not in origen:
            continue
        propios = origen.loc[origen.alphadata_ticker == ticker, "fecha_declarada"]
        conocidas |= {pd.Timestamp(f).normalize() for f in pd.to_datetime(propios, errors="coerce").dropna()}
    return [e for e in eventos if pd.Timestamp(e["fecha_declarada"]).normalize() not in conocidas]


def aplicar_ajuste(precios: pd.DataFrame, dividendos: pd.DataFrame, tickers: set[str]) -> pd.DataFrame:
    """Reemplaza `adjusted_close` por el derivado, sólo en los instrumentos dados.

    Cierra el círculo del almacén de sólo agregar: el cierre crudo es un hecho
    y se guarda; el ajustado cambia hacia atrás con cada reparto y se calcula.
    Deja de venir del proveedor, cuyo factor escalonaba entre cinco y siete
    ruedas después de la caída ex real y producía movimientos ficticios de
    hasta 9%.

    Los instrumentos fuera de `tickers` —los de EE.UU., el oro, el tipo de
    cambio— conservan el ajustado del proveedor, que en su mercado funciona.
    """
    salida = precios.copy()
    afectados = salida.alphadata_ticker.isin(tickers)
    if not afectados.any():
        return salida
    salida.loc[afectados, "adjusted_close"] = derivar_ajustado(salida.loc[afectados], dividendos)
    return salida
