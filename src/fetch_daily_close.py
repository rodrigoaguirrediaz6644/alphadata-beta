"""Captura diaria del cierre chileno desde la cotización viva de Yahoo.

Yahoo dejó de actualizar el arreglo histórico de los tickers `.SN` el
17-07-2026, pero **sigue publicando la cotización viva** en el bloque `meta`
del mismo endpoint. Ese era el "dato fantasma" que aparecía cada viernes y se
perdía a la semana siguiente: no era basura, era el único dato bueno que
quedaba, y el almacén lo descartaba al reescribirse. Validado contra
investing.com al 17-09-2026, razón 1,000000 en los once instrumentos de
referencia, incluidos máximo, mínimo y volumen.

Por qué es un trabajo diario y no semanal: la SMA200, el momentum 12-1 y el
RSI(14) necesitan serie diaria. Con una captura semanal habría un punto real
cada cinco ruedas y los indicadores quedarían calculados sobre una escalera.

Lo que esta vía no da:

- **Cierre ajustado.** Sin historial no hay factores de dividendo. Aquí el
  ajustado se graba igual al crudo, lo que es correcto sólo mientras no haya
  reparto. La tabla manual de acciones corporativas es lo que cierra ese hueco.
- **Apertura.** `meta` no la trae. Ninguna de las cuatro estrategias la usa.
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from src.fetch_prices import PRICE_COLUMNS, _ajustar_chilenos, load_universe, operables
from src.dividendos import COLUMNAS_TABLA, descargar_eventos, detectar_nuevos, localizar_fecha_ex
from src.guards import ruedas_faltantes
from src.price_store import agregar

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AGENTE = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ESPERA_ENTRE_LLAMADAS = .4
# El feed histórico murió sólo para la bolsa local. Los instrumentos de EE.UU.,
# el oro y el tipo de cambio siguen llegando por `fetch_prices`, y capturarlos
# por esta vía les grabaría un ajustado igual al crudo, que en papeles que
# reparten dividendos sería peor que no tocarlos.
TIPOS_LOCALES = {"accion_local", "accion_sigma"}


def _descargar(yahoo_ticker: str, timeout: int = 30) -> dict:
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}"
           "?range=5d&interval=1d")
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENTE), timeout=timeout) as respuesta:
        cuerpo = json.load(respuesta)
    return cuerpo["chart"]["result"][0]["meta"]


def sesion_cerrada(meta: dict, ahora: pd.Timestamp | None = None) -> bool:
    """Decide si el precio que trae `meta` es un cierre y no un valor intradía.

    Sin esta comprobación, una corrida lanzada con el mercado abierto grabaría
    un precio intradía como si fuera el cierre del día, y el almacén de sólo
    agregar lo dejaría fijo para siempre.

    Lo que **no** sirve como criterio es exigir que la última operación sea
    posterior a la campana: salvo que haya remate de cierre, la última punta
    ocurre segundos antes. El 17-09-2026 la sesión terminó a las 16:00:00 UTC y
    la mayoría de los papeles marcó su última operación a las 15:59:49. Sólo
    nueve de cuarenta tenían remate posterior.

    El criterio correcto es si la rueda ya terminó:

    - Si la rueda es de un día anterior al de hoy en el huso de la bolsa,
      terminó, sin más que mirar.
    - Si es la de hoy, hay que haber pasado el fin de la sesión, sea porque el
      reloj ya lo pasó o porque hubo una operación en el remate.
    """
    marca = meta.get("regularMarketTime")
    if marca is None:
        return False
    ahora = pd.Timestamp.now(tz="UTC") if ahora is None else pd.Timestamp(ahora)
    if ahora.tzinfo is None:
        ahora = ahora.tz_localize("UTC")
    huso = meta.get("exchangeTimezoneName")
    hoy = (ahora.tz_convert(huso) if huso else ahora).normalize().tz_localize(None)
    rueda = fecha_de_rueda(meta)
    if rueda is not None and rueda < hoy:
        return True
    fin = (meta.get("currentTradingPeriod") or {}).get("regular", {}).get("end")
    if fin is None:
        return False
    return int(marca) >= int(fin) or ahora.timestamp() >= int(fin)


def fecha_de_rueda(meta: dict) -> pd.Timestamp | None:
    """La fecha de la rueda en el huso de la bolsa, no en el del servidor.

    Un runner en UTC puede estar en el día siguiente cuando en Santiago todavía
    es la tarde anterior; fechar con su reloj correría la serie un día.
    """
    marca = meta.get("regularMarketTime")
    huso = meta.get("exchangeTimezoneName")
    if marca is None:
        return None
    momento = pd.Timestamp(int(marca), unit="s", tz="UTC")
    if huso:
        momento = momento.tz_convert(huso)
    return momento.normalize().tz_localize(None)


def fila(meta: dict, alphadata_ticker: str, yahoo_ticker: str,
         ahora: pd.Timestamp | None = None) -> dict | None:
    """Convierte el bloque `meta` en una fila de precios, o descarta."""
    precio = meta.get("regularMarketPrice")
    fecha = fecha_de_rueda(meta)
    if precio is None or fecha is None or not sesion_cerrada(meta, ahora):
        return None
    return {
        "date": fecha,
        "alphadata_ticker": alphadata_ticker,
        "yahoo_ticker": yahoo_ticker,
        "open": pd.NA,  # `meta` no la trae; ninguna estrategia la usa
        "high": meta.get("regularMarketDayHigh"),
        "low": meta.get("regularMarketDayLow"),
        "close": float(precio),
        "adjusted_close": float(precio),  # sin factores de dividendo disponibles
        "volume": meta.get("regularMarketVolume"),
    }


def capturar(universe: pd.DataFrame, descargar: Callable[[str], dict] = _descargar,
             espera: float = ESPERA_ENTRE_LLAMADAS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recorre los instrumentos locales y devuelve (filas del día, incidencias)."""
    objetivo = operables(universe).loc[lambda u: u.tipo.isin(TIPOS_LOCALES)]
    filas, incidencias = [], []
    for item in objetivo.itertuples(index=False):
        try:
            meta = descargar(item.yahoo_ticker)
        except Exception as error:
            incidencias.append({"alphadata_ticker": item.alphadata_ticker, "motivo": f"descarga falló: {type(error).__name__}"})
            continue
        nueva = fila(meta, item.alphadata_ticker, item.yahoo_ticker)
        if nueva is None:
            motivo = "sesión abierta o sin cierre" if meta.get("regularMarketPrice") is not None else "sin precio"
            incidencias.append({"alphadata_ticker": item.alphadata_ticker, "motivo": motivo})
            continue
        filas.append(nueva)
        if espera:
            time.sleep(espera)
    columnas = PRICE_COLUMNS
    return (pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame(columns=columnas),
            pd.DataFrame(incidencias, columns=["alphadata_ticker", "motivo"]))


def vigilar_dividendos(universe: pd.DataFrame, precios: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Incorpora lo que se puede resolver hoy y deja pendiente sólo lo demás.

    Sin esto la tabla nace correcta y se degrada sola: el próximo reparto de
    cualquiera de los cuarenta instrumentos produciría un ajustado equivocado
    en silencio.

    El reparto entre incorporar y dejar pendiente **no es discrecional**, sale
    del mismo criterio que la tabla histórica:

    - Un dividendo **pequeño** no se puede confirmar con el precio: la prueba
      nula da 100% de falsos positivos en su banda. No tiene sentido dejarlo
      esperando una confirmación que no va a llegar nunca, así que entra de
      inmediato con la fecha por convención, exactamente como los 127
      históricos.
    - Un dividendo **grande** sí se puede confirmar, pero necesita que la rueda
      ex ya haya ocurrido y esté descargada. Mientras no calce queda pendiente,
      y se reintenta **cada día**: se resuelve solo en cuanto llegue el precio.

    Si no se distinguieran, el primer dividendo chico que repartiera cualquier
    papel dejaría la corrida bloqueada para siempre, esperando una confirmación
    imposible.
    """
    tabla_path = DATA / "dividendos.csv"
    pendientes_path = DATA / "dividendos_pendientes.csv"
    tabla = pd.read_csv(tabla_path, parse_dates=["fecha_ex", "fecha_declarada"]) if tabla_path.exists() else pd.DataFrame(columns=COLUMNAS_TABLA)
    pendientes = pd.read_csv(pendientes_path, parse_dates=["fecha_declarada"]) if pendientes_path.exists() else pd.DataFrame(columns=["alphadata_ticker", "fecha_declarada", "monto", "detectado"])
    ahora = pd.Timestamp.now(tz="UTC").tz_localize(None)
    locales = operables(universe).loc[lambda u: u.tipo.isin(TIPOS_LOCALES)]

    candidatos: list[dict] = []
    for item in locales.itertuples(index=False):
        try:
            eventos = descargar_eventos(item.yahoo_ticker, ahora - pd.Timedelta(days=120), ahora + pd.Timedelta(days=30))
        except Exception:
            continue
        for evento in detectar_nuevos(tabla, pd.DataFrame(), eventos, item.alphadata_ticker):
            candidatos.append({"alphadata_ticker": item.alphadata_ticker, **evento})
        time.sleep(.2)
    # Los que ya estaban pendientes se reintentan: puede que hoy sí calcen.
    for fila in pendientes.itertuples(index=False):
        candidatos.append({"alphadata_ticker": fila.alphadata_ticker, "monto": float(fila.monto),
                           "fecha_declarada": pd.Timestamp(fila.fecha_declarada)})

    incorporados, siguen_pendientes = [], []
    for candidato in candidatos:
        serie = precios.loc[precios.alphadata_ticker == candidato["alphadata_ticker"]].set_index("date")["close"]
        calce = localizar_fecha_ex(serie, candidato["fecha_declarada"], candidato["monto"])
        if calce is not None and not calce["rechazado"]:
            incorporados.append({**{k: v for k, v in calce.items() if k != "rechazado"}, **candidato})
        else:
            siguen_pendientes.append({**candidato, "detectado": ahora.date().isoformat()})

    if incorporados:
        tabla = pd.concat([tabla, pd.DataFrame(incorporados)], ignore_index=True)
        tabla = tabla.drop_duplicates(["alphadata_ticker", "fecha_declarada"], keep="last")
        tabla.sort_values(["alphadata_ticker", "fecha_ex"])[COLUMNAS_TABLA].to_csv(
            tabla_path, index=False, date_format="%Y-%m-%d")
        detalle = ", ".join(f"{i['alphadata_ticker']} {pd.Timestamp(i['fecha_ex']):%d-%m-%Y}" for i in incorporados)
        print(f"Dividendos incorporados a la tabla: {len(incorporados)} ({detalle}).")
    nueva = pd.DataFrame(siguen_pendientes, columns=["alphadata_ticker", "fecha_declarada", "monto", "detectado"])
    nueva.to_csv(pendientes_path, index=False, date_format="%Y-%m-%d")
    if len(nueva):
        detalle = ", ".join(f"{r.alphadata_ticker} {pd.Timestamp(r.fecha_declarada):%d-%m-%Y}" for r in nueva.itertuples())
        print(f"ADVERTENCIA: {len(nueva)} dividendos grandes sin confirmar todavía ({detalle}). "
              "Se reintentan cada día; si persisten, revisar a mano.")
    return tabla, nueva


def main() -> None:
    universe = load_universe()
    esperados = int(operables(universe).tipo.isin(TIPOS_LOCALES).sum())
    capturadas, incidencias = capturar(universe)
    # Ruidosamente y no en silencio: un cierre que no se captura hoy no se
    # puede recuperar mañana, así que un día en blanco tiene que romper el job
    # y avisar, no terminar con un mensaje amable y código cero.
    if capturadas.empty:
        detalle = "; ".join(f"{r.alphadata_ticker} ({r.motivo})" for r in incidencias.itertuples())
        raise SystemExit(f"Ningún cierre capturado de {esperados} instrumentos. {detalle}")
    if len(capturadas) < esperados * .75:
        detalle = "; ".join(f"{r.alphadata_ticker} ({r.motivo})" for r in incidencias.itertuples())
        raise SystemExit(f"Sólo se capturaron {len(capturadas)} cierres de {esperados}. {detalle}")
    ruta = DATA / "market_prices_daily.csv"
    guardado = pd.read_csv(ruta, parse_dates=["date"]) if ruta.exists() else pd.DataFrame(columns=PRICE_COLUMNS)
    antes = len(guardado)
    resultado, revisiones = agregar(guardado, capturadas)
    resultado = _ajustar_chilenos(resultado, universe)
    DATA.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(ruta, index=False, date_format="%Y-%m-%d")
    agregadas = len(resultado) - antes
    fechas = sorted({d.date().isoformat() for d in capturadas.date})
    print(f"Cierres leídos: {len(capturadas)} para {', '.join(fechas)}. Filas nuevas grabadas: {agregadas}.")
    if len(revisiones):
        revisiones.to_csv(DATA / "revisiones_precios.csv", index=False, date_format="%Y-%m-%d")
        print(f"ADVERTENCIA: {len(revisiones)} cierres ya grabados llegaron distintos. No se aplicaron; "
              "revisar data/revisiones_precios.csv")
    if len(incidencias):
        print("Sin capturar: " + "; ".join(f"{r.alphadata_ticker} ({r.motivo})" for r in incidencias.itertuples()))
    locales = set(universe.loc[universe.tipo.isin(TIPOS_LOCALES), "alphadata_ticker"])
    faltantes = ruedas_faltantes(resultado, locales, desde=pd.Timestamp("2026-09-18"))
    if len(faltantes):
        print("ADVERTENCIA: ruedas en que el ADR testigo operó y no hay cierre local grabado: "
              + ", ".join(f"{d:%d-%m-%Y}" for d in faltantes)
              + ". Si no son feriados chilenos, hay que rellenarlas a mano.")
    vigilar_dividendos(universe, resultado)
    (DATA / "ultima_captura_diaria.json").write_text(json.dumps({
        "ejecutada_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ruedas": fechas, "leidos": int(len(capturadas)), "agregados": int(agregadas),
        "incidencias": incidencias.to_dict("records"),
        "ruedas_sin_cierre_local": [d.date().isoformat() for d in faltantes],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
