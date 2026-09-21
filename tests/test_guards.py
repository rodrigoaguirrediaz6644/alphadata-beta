from pathlib import Path

import numpy as np
import pandas as pd

from src.guards import (MAX_RUEDAS_SIN_VARIACION, adr_contra_local, contraste_entre_fuentes,
                        feed_detenido, fraccion_sin_variacion, ruedas_sin_variacion, series_detenidas)

ROOT = Path(__file__).resolve().parents[1]


def _precios_del_incidente() -> pd.DataFrame:
    """Datos reales del feed detenido, congelados como fixture.

    Se extrajeron de `data/market_prices_daily.csv` mientras el incidente
    seguía ahí. Apuntar estas pruebas al archivo vivo las volvía frágiles: en
    cuanto la captura diaria empezó a traer cierres buenos, los instrumentos
    dejaron de estar detenidos y la regresión falló sin que nada se hubiera
    roto. El incidente es un hecho del pasado y como tal se conserva.
    """
    return pd.read_csv(ROOT / "tests" / "fixtures" / "incidente_feed_chileno.csv", parse_dates=["date"])


def _panel(valores: dict[str, list[float]], inicio="2026-01-05") -> pd.DataFrame:
    fechas = pd.bdate_range(inicio, periods=max(len(v) for v in valores.values()))
    filas = []
    for ticker, serie in valores.items():
        for fecha, valor in zip(fechas, serie):
            filas.append({"date": fecha, "alphadata_ticker": ticker, "close": valor, "adjusted_close": valor})
    return pd.DataFrame(filas)


# --- guardia 1: serie sin variación, calibrada con la evidencia ----------------------

def test_cuenta_las_ruedas_que_un_precio_lleva_sin_moverse():
    panel = _panel({"VIVO": list(np.arange(100, 130.0)), "MUERTO": [100.0] * 30})
    cuenta = ruedas_sin_variacion(panel)
    assert cuenta["VIVO"] == 0
    assert cuenta["MUERTO"] == 29


def test_un_papel_iliquido_no_se_marca_detenido():
    # INGEVEC llegó a 19 ruedas seguidas sin cambiar de precio en un periodo
    # sano, e INDISA a 14. Son papeles que no transan todos los días, no series
    # muertas. El umbral está en 20 justamente para dejarlos pasar.
    iliquido = list(np.arange(100, 110.0)) + [110.0] * 19 + [111.0]
    assert len(series_detenidas(_panel({"INGEVEC": iliquido}))) == 0


def test_una_racha_mas_larga_que_cualquiera_observada_si_se_marca():
    # En la ventana congelada la racha más corta fue de 23 ruedas.
    muerto = list(np.arange(100, 110.0)) + [110.0] * 23
    assert list(series_detenidas(_panel({"BCI": muerto}))) == ["BCI"]
    assert MAX_RUEDAS_SIN_VARIACION == 20


def test_el_incidente_de_2026_aparece_como_series_detenidas():
    detenidas = set(series_detenidas(_precios_del_incidente()))
    assert {"BCI", "PARAUCO", "ILC", "BSANTANDER"} <= detenidas


# --- guardia 2: el mercado entero quieto, que es un feed caído -----------------------

def test_en_un_mercado_normal_solo_una_minoria_se_queda_quieta():
    # Medido entre 2025 y julio de 2026: mediana 10,3%, máximo 25,6% en 383
    # ruedas. Ninguna por encima del 60%.
    sube = list(np.arange(100, 110.0))
    quieto = [100.0] * 10
    fraccion = fraccion_sin_variacion(_panel({"A": sube, "B": sube, "C": sube, "D": quieto}))
    assert fraccion.max() <= .25
    assert len(feed_detenido(_panel({"A": sube, "B": sube, "C": sube, "D": quieto}))) == 0


def test_el_mercado_entero_quieto_frena_la_corrida():
    quieto = [100.0] * 10
    caidas = feed_detenido(_panel({"A": quieto, "B": quieto, "C": quieto}))
    assert len(caidas) == 1


def test_una_rueda_plana_antigua_no_bloquea_la_corrida_de_hoy():
    # La guardia pregunta por ahora, no por la historia. Hay cinco ruedas
    # antiguas con el mercado entero quieto —feriados y huecos del dato viejo—
    # y con ellas dentro la corrida quedaba bloqueada para siempre.
    sube = list(np.arange(100, 112.0))
    con_hueco = [100.0, 100.0, 100.0] + list(np.arange(101, 110.0))
    panel = _panel({"A": con_hueco, "B": con_hueco, "C": con_hueco})
    assert len(feed_detenido(panel)) == 0          # la última rueda está viva
    assert len(feed_detenido(panel, ruedas=0)) > 0  # revisando todo, sí aparece


def test_el_incidente_se_habria_detectado_la_primera_rueda():
    # El 20-07-2026, primera rueda tras el congelamiento, el 100% de las
    # acciones chilenas no movió su precio. La guardia lo dice ese día, no dos
    # meses después.
    incidente = _precios_del_incidente()
    locales = {"BCI", "PARAUCO", "ILC", "BSANTANDER", "LTM", "SQM-B"}
    fraccion = fraccion_sin_variacion(incidente, locales)
    assert fraccion.loc[pd.Timestamp("2026-07-20")] >= .9
    assert pd.Timestamp("2026-07-20") in set(feed_detenido(incidente, locales, ruedas=0))


def test_el_volumen_no_distingue_un_feed_muerto_de_un_papel_iliquido():
    # Parecía el discriminador natural y no lo es: durante el congelamiento el
    # proveedor entregó volumen cero en las 31 ruedas de todos los instrumentos
    # afectados, exactamente igual que un papel que no transó.
    locales = ["BCI", "PARAUCO", "ILC", "BSANTANDER", "LTM", "SQM-B"]
    congelado = _precios_del_incidente().query("date >= '2026-07-20' and alphadata_ticker in @locales")
    assert len(congelado) > 100
    assert (congelado.volume.fillna(0) == 0).all()
    # Los ADR, que sí operaban, traen volumen: el contraste es entre mercados,
    # no entre un papel con volumen y otro sin él.
    adr = _precios_del_incidente().query("date >= '2026-07-20' and alphadata_ticker == 'LTM-ADR'")
    assert (adr.volume.fillna(0) > 0).any()


# --- guardia 3: contraste entre fuentes ---------------------------------------------

def test_dos_fuentes_que_coinciden_no_generan_alarma():
    panel = _panel({"BCI": [100, 101, 102, 103]})
    assert contraste_entre_fuentes(panel, panel).empty


def test_dos_fuentes_que_discrepan_se_reportan_por_fecha():
    principal = _panel({"BCI": [100, 101, 102, 103]})
    contraste = _panel({"BCI": [100, 101, 120, 103]})
    alarma = contraste_entre_fuentes(principal, contraste)
    assert len(alarma) == 1
    assert alarma.iloc[0].alphadata_ticker == "BCI"
    assert alarma.iloc[0].desvio > .1


# --- guardia 4: ADR contra acción local ---------------------------------------------

def test_el_adr_delata_el_mercado_local_detenido_apenas_ocurre():
    quincena = _precios_del_incidente().query("'2026-07-18' <= date <= '2026-07-31'")
    alarma = adr_contra_local(quincena, ventana=10)
    assert "LTM" in set(alarma.local)
    assert alarma.loc[alarma.local == "LTM", "movimiento_local"].iloc[0] == 0.0


def test_el_adr_delata_los_dos_pares_en_agosto():
    agosto = _precios_del_incidente().query("'2026-08-01' <= date <= '2026-08-31'")
    alarma = adr_contra_local(agosto, ventana=20)
    assert set(alarma.local) == {"LTM", "SQM-B"}
    assert (alarma.movimiento_adr > .10).all()


def test_un_mercado_local_que_se_mueve_no_dispara_la_guardia():
    panel = _panel({"LTM-ADR": [10, 10.5, 11, 11.2], "LTM": [100, 104, 108, 110]})
    assert adr_contra_local(panel, ventana=4).empty
