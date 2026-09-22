"""El premio del CDV sobre su valor teorico, y lo que lo hace medible.

Lo que se prueba aca es sobre todo **el filtro**: sin el, la medicion no mide un
premio, mide que el precio del CDV esta rancio. El 96% de las ruedas repite el
cierre anterior y ABTCL estuvo 453 ruedas seguidas en el mismo precio.
"""

import pandas as pd
import pytest

from src.cdv import BANDA, cdvs, frescas, premio
from src.salud import revisar


def _precios(fechas, usd, fx=1000.):
    filas = []
    for f, u in zip(fechas, usd):
        filas.append({"date": f, "alphadata_ticker": "ABT", "close": u})
        filas.append({"date": f, "alphadata_ticker": "USDCLP", "close": fx})
    return pd.DataFrame(filas).assign(date=lambda d: pd.to_datetime(d.date))


def _cdv(fechas, clp, volumen):
    return pd.DataFrame({"date": pd.to_datetime(list(fechas)), "cdv": "ABTCL.SN",
                         "subyacente": "ABT", "cdv_clp": list(clp), "volumen": list(volumen)})


FECHAS = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]


def test_un_precio_rancio_no_cuenta_aunque_tenga_volumen():
    """El volumen solo no alcanza: hay ruedas con volumen que repiten el cierre.

    Sin este filtro se estaria dividiendo un precio de hace semanas por un
    subyacente que si se movio, y el resultado mide el rancio y no el premio.
    """
    p = _precios(FECHAS, [100., 110., 120., 130.])
    c = _cdv(FECHAS, [100_000., 100_000., 100_000., 131_000.], [5, 5, 5, 5])
    f = frescas(c, p)
    assert list(f.date.dt.strftime("%Y-%m-%d")) == ["2026-01-08"]


def test_sin_volumen_tampoco_cuenta():
    p = _precios(FECHAS, [100., 110., 120., 130.])
    c = _cdv(FECHAS, [100_000., 111_000., 121_000., 131_000.], [0, 0, 0, 7])
    assert list(frescas(c, p).date.dt.strftime("%Y-%m-%d")) == ["2026-01-08"]


def test_el_premio_es_el_desvio_contra_el_subyacente_por_el_tipo_de_cambio():
    fechas = [f"2026-02-{d:02d}" for d in range(1, 41 + 1) if d <= 28] + \
             [f"2026-03-{d:02d}" for d in range(1, 13)]
    usd = [100. + i for i in range(len(fechas))]
    p = _precios(fechas, usd)
    # El CDV cotiza siempre 1% sobre su teorico, y siempre fresco.
    c = _cdv(fechas, [u * 1000. * 1.01 for u in usd], [3] * len(fechas))
    x = premio(c, p)
    assert x is not None
    assert x.medio == pytest.approx(.01, abs=1e-9)
    assert x.ruedas == len(fechas) - 1      # la primera no tiene rueda anterior


def test_con_pocas_ruedas_frescas_no_se_afirma_nada():
    """Es la diferencia entre no saber y decir cero."""
    p = _precios(FECHAS, [100., 110., 120., 130.])
    c = _cdv(FECHAS, [100_000., 111_000., 121_000., 131_000.], [1, 1, 1, 1])
    assert premio(c, p) is None


def test_una_razon_muy_lejos_de_uno_se_descarta_por_ser_otro_instrumento():
    """Asi se descubrio que el simbolo anotado para Bank of America era Boeing.

    BACL.SN cotizaba a 3,6 veces el teorico de BAC, de forma consistente. Eso no
    es un premio: es otra empresa. El simbolo correcto es BACCL.
    """
    p = _precios(FECHAS, [100., 110., 120., 130.])
    c = _cdv(FECHAS, [360_000., 400_000., 430_000., 470_000.], [3, 3, 3, 3])
    assert frescas(c, p).empty


def test_exxon_queda_fuera_en_vez_de_adivinarle_un_simbolo():
    u = pd.DataFrame([
        {"alphadata_ticker": "BAC", "tipo": "accion_us", "cdv_ticker": "BACCL"},
        {"alphadata_ticker": "XOM", "tipo": "accion_us", "cdv_ticker": None},
        {"alphadata_ticker": "IAU", "tipo": "etf_us", "cdv_ticker": "IAUCL"},
        {"alphadata_ticker": "BCI", "tipo": "accion_local", "cdv_ticker": None},
    ])
    assert cdvs(u) == {"BAC": "BACCL.SN", "IAU": "IAUCL.SN"}


def _revisar(premio_cdv):
    return revisar(as_of=pd.Timestamp("2026-09-18"), precios_al_dia=True, series_detenidas=set(),
                   cobertura_incompleta=set(), series_recalculadas={"A"}, series_publicadas={"A"},
                   carteras_reproducidas=True, dias_sin_recomendaciones=10, umbral_vigencia=90,
                   dividendos_sin_respaldo=set(), suite_verde=True, premio_cdv=premio_cdv)[0]


def test_el_panel_avisa_solo_si_el_premio_sale_de_la_banda():
    """Una alarma que suena por ruido deja de ser alarma.

    El premio medido tiene un error estandar de 0,05% sobre dos anios, asi que
    una banda estrecha sonaria sola todas las semanas.
    """
    class P:
        medio, error, ruedas, nombres = BANDA / 2, .0005, 700, 14
        distinguible, dentro_de_la_banda = True, True

    class Fuera(P):
        medio, dentro_de_la_banda = BANDA * 2, False

    fila = [c for c in _revisar(P()) if c.nombre == "Premio del CDV"][0]
    assert fila.sano
    fila = [c for c in _revisar(Fuera()) if c.nombre == "Premio del CDV"][0]
    assert not fila.sano and "fuera de la banda" in fila.detalle


def test_sin_medicion_el_panel_lo_dice_y_no_inventa_un_cero():
    fila = [c for c in _revisar(None) if c.nombre == "Premio del CDV"][0]
    assert fila.sano and "sin ruedas frescas suficientes" in fila.detalle
