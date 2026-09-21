"""La captura diaria toma el cierre del bloque `meta` de Yahoo.

El riesgo que estas pruebas cubren no es que falle: es que grabe un precio
intradía como si fuera un cierre. El almacén es de sólo agregar, así que un
número equivocado grabado hoy queda fijo para siempre.
"""

import pandas as pd
import pytest

from src.fetch_daily_close import capturar, fecha_de_rueda, fila, sesion_cerrada

# Valores reales de ILC.SN al 17-09-2026, comprobados contra investing.com.
FIN_SESION = 1789660800   # 2026-09-17 16:00:00 UTC
CIERRE = 1789661067       # 2026-09-17 16:04:27 UTC, cuatro minutos después

META = {
    "regularMarketPrice": 25000.0,
    "regularMarketTime": CIERRE,
    "regularMarketDayHigh": 25000.0,
    "regularMarketDayLow": 24380.0,
    "regularMarketVolume": 28945,
    "exchangeTimezoneName": "America/Santiago",
    "currentTradingPeriod": {"regular": {"start": 1789648200, "end": FIN_SESION}},
}


def _universo(filas=None):
    return pd.DataFrame(filas or [
        {"alphadata_ticker": "ILC", "yahoo_ticker": "ILC.SN", "nombre": "ILC",
         "tipo": "accion_local", "moneda": "CLP", "estado": "activo"},
    ])


DURANTE = pd.Timestamp(FIN_SESION - 3600, unit="s", tz="UTC")   # una hora antes del cierre
DESPUES = pd.Timestamp(FIN_SESION + 3600, unit="s", tz="UTC")   # una hora después
OTRO_DIA = pd.Timestamp(FIN_SESION + 3 * 86400, unit="s", tz="UTC")


def test_un_remate_posterior_a_la_campana_es_un_cierre():
    assert sesion_cerrada(META, ahora=DESPUES)


def test_la_ultima_punta_antes_de_la_campana_tambien_cuenta_si_la_sesion_termino():
    # El caso normal: salvo remate, la última operación ocurre segundos antes
    # de la campana. El 17-09-2026 la mayoría de los papeles marcó 15:59:49
    # contra un cierre a las 16:00:00. Exigir una operación posterior dejaba
    # fuera treinta y un instrumentos de cuarenta.
    justo_antes = {**META, "regularMarketTime": FIN_SESION - 11}
    assert sesion_cerrada(justo_antes, ahora=DESPUES)
    assert fila(justo_antes, "ILC", "ILC.SN", ahora=DESPUES) is not None


def test_un_precio_intradia_no_se_toma_por_cierre():
    intradia = {**META, "regularMarketTime": FIN_SESION - 1800}  # media hora antes
    assert not sesion_cerrada(intradia, ahora=DURANTE)
    assert fila(intradia, "ILC", "ILC.SN", ahora=DURANTE) is None


def test_una_rueda_de_un_dia_anterior_siempre_cuenta_como_cerrada():
    # Un lunes con el mercado abierto, el precio del viernes anterior ya es un
    # cierre aunque el reloj no haya pasado el fin de la sesión de hoy.
    assert sesion_cerrada(META, ahora=OTRO_DIA)


def test_sin_horario_de_sesion_no_se_asume_que_cerro():
    sin_horario = {**META, "currentTradingPeriod": {}}
    assert not sesion_cerrada(sin_horario, ahora=DURANTE)


def test_la_fecha_sale_del_huso_de_la_bolsa_y_no_del_servidor():
    # A las 16:04 UTC en Santiago son las 13:04 del mismo día. Si la marca
    # cayera de noche en UTC, fechar con el reloj del runner correría la serie.
    assert fecha_de_rueda(META) == pd.Timestamp("2026-09-17")
    tarde = {**META, "regularMarketTime": CIERRE + 8 * 3600}  # 00:04 UTC del 18
    assert fecha_de_rueda(tarde) == pd.Timestamp("2026-09-17")


def test_la_fila_recoge_cierre_maximo_minimo_y_volumen():
    resultado = fila(META, "ILC", "ILC.SN")
    assert resultado["date"] == pd.Timestamp("2026-09-17")
    assert resultado["close"] == pytest.approx(25000.0)
    assert resultado["high"] == pytest.approx(25000.0)
    assert resultado["low"] == pytest.approx(24380.0)
    assert resultado["volume"] == 28945
    # Sin factores de dividendo disponibles, el ajustado es el crudo.
    assert resultado["adjusted_close"] == pytest.approx(resultado["close"])


def test_captura_devuelve_la_fila_y_ninguna_incidencia():
    filas, incidencias = capturar(_universo(), descargar=lambda _: META, espera=0)
    assert len(filas) == 1 and incidencias.empty
    assert filas.iloc[0].alphadata_ticker == "ILC"


def test_una_descarga_fallida_se_reporta_y_no_detiene_al_resto():
    universo = _universo([
        {"alphadata_ticker": "ILC", "yahoo_ticker": "ILC.SN", "nombre": "ILC",
         "tipo": "accion_local", "moneda": "CLP", "estado": "activo"},
        {"alphadata_ticker": "ROTO", "yahoo_ticker": "ROTO.SN", "nombre": "Roto",
         "tipo": "accion_local", "moneda": "CLP", "estado": "activo"},
    ])

    def descargar(ticker):
        if ticker == "ROTO.SN":
            raise TimeoutError("sin respuesta")
        return META

    filas, incidencias = capturar(universo, descargar=descargar, espera=0)
    assert list(filas.alphadata_ticker) == ["ILC"]
    assert list(incidencias.alphadata_ticker) == ["ROTO"]


def test_los_instrumentos_que_no_son_chilenos_quedan_fuera():
    # EE.UU., el oro y el tipo de cambio siguen llegando por fetch_prices: por
    # esta vía se les grabaría un ajustado igual al crudo.
    universo = _universo([
        {"alphadata_ticker": "ABT", "yahoo_ticker": "ABT", "nombre": "Abbott",
         "tipo": "accion_us", "moneda": "USD", "estado": "activo"},
        {"alphadata_ticker": "IAU", "yahoo_ticker": "IAU", "nombre": "Oro",
         "tipo": "etf_us", "moneda": "USD", "estado": "activo"},
        {"alphadata_ticker": "USDCLP", "yahoo_ticker": "USDCLP=X", "nombre": "Dólar",
         "tipo": "fx", "moneda": "CLP", "estado": "activo"},
    ])
    filas, incidencias = capturar(universo, descargar=lambda _: META, espera=0)
    assert filas.empty and incidencias.empty
