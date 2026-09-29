"""Los números del titular y de la tabla de desempeño.

Las series de cada pieza se reemplazan por unas conocidas: acá se prueba desde
dónde se mide y cómo se pondera, no las reglas de cada estrategia.
"""

import pandas as pd
import pytest

from src import run_pipeline as rp

REPARTO = {"Delta-12": .375, "Gamma-6": .375, "Oro": .25}
CONJUNTO = "Conjunto AlphaData"
AS_OF = pd.Timestamp("2026-01-30")
# El último cierre de 2025 en 200 y el de hace cinco años en 100. Antes de cada
# uno va un valor distinto, para delatar una base mal elegida.
FECHAS = pd.to_datetime(["2021-01-28", "2021-01-29", "2023-06-30", "2025-12-29", "2025-12-30",
                         "2026-01-02", "2026-01-30"])
DATOS = {"Delta-12": [90., 100., 80., 150., 200., 210., 220.],
         "Gamma-6": [90., 100., 50., 150., 200., 190., 240.],
         "Oro": [90., 100., 100., 150., 200., 200., 200.]}


def _serie(nombre, valores, fechas=FECHAS):
    return pd.DataFrame({"date": fechas, nombre: valores})


@pytest.fixture
def series(monkeypatch):
    monkeypatch.setattr(rp, "delta12_historical_nav", lambda *a, **k: _serie("Delta-12", DATOS["Delta-12"]))
    monkeypatch.setattr(rp, "gamma6_historical_nav", lambda *a, **k: _serie("Gamma-6", DATOS["Gamma-6"]))
    monkeypatch.setattr(rp, "oro_historical_nav", lambda *a, **k: _serie("Oro", DATOS["Oro"]))


def _calcular(reparto=REPARTO, as_of=AS_OF):
    vacio = pd.DataFrame(columns=["date", "alphadata_ticker", "adjusted_close"])
    return rp.desempeño_del_modelo(as_of, vacio, vacio, vacio, vacio, pd.DataFrame(columns=["cdv_ticker"]),
                                   reparto, .001785)


def test_el_año_se_mide_desde_el_ultimo_cierre_del_año_anterior(series):
    r = _calcular()
    assert r["desde"] == pd.Timestamp("2026-01-01")
    assert {n: r["año"][n] for n in REPARTO} == pytest.approx({"Delta-12": .10, "Gamma-6": .20, "Oro": 0.})


def test_el_conjunto_pondera_con_el_reparto_vigente(series):
    """37,5% de 10%, 37,5% de 20% y 25% de 0%. En partes iguales daría 10,0%."""
    r = _calcular()
    assert r["año"][CONJUNTO] == pytest.approx(.375 * .10 + .375 * .20 + .25 * 0.)
    assert r["reparto"] == REPARTO


def test_los_cinco_años_se_miden_desde_el_ultimo_cierre_de_hace_cinco_años(series):
    """Desde el 100 del 29-01-2021, no desde el 90 de la víspera."""
    r = _calcular()
    assert {n: r["cinco_años"][n] for n in REPARTO} == pytest.approx({"Delta-12": 1.2, "Gamma-6": 1.4, "Oro": 1.0})


def test_el_maximo_retroceso_es_el_de_los_cinco_años(series):
    r = _calcular()
    assert {n: r["retroceso"][n] for n in REPARTO} == pytest.approx({"Delta-12": -.2, "Gamma-6": -.5, "Oro": 0.})
    assert -.5 < r["retroceso"][CONJUNTO] < 0


def test_el_conjunto_se_reequilibra_cada_mes(monkeypatch):
    """Dos meses de +10% en una pieza sola: reequilibrando se gana menos que dejándola correr."""
    fechas = pd.to_datetime(["2025-12-30", "2026-01-30", "2026-02-27"])
    monkeypatch.setattr(rp, "delta12_historical_nav", lambda *a, **k: _serie("Delta-12", [100., 110., 121.], fechas))
    monkeypatch.setattr(rp, "gamma6_historical_nav", lambda *a, **k: _serie("Gamma-6", [100., 100., 100.], fechas))
    monkeypatch.setattr(rp, "oro_historical_nav", lambda *a, **k: _serie("Oro", [100., 100., 100.], fechas))
    r = _calcular(as_of=pd.Timestamp("2026-02-27"))
    assert r["año"][CONJUNTO] == pytest.approx(1.0375 ** 2 - 1)
    assert r["año"][CONJUNTO] < .375 * .21


def test_sin_historia_para_cinco_años_el_año_sale_igual(monkeypatch):
    fechas = pd.to_datetime(["2025-12-30", "2026-01-30"])
    for nombre, funcion in (("Delta-12", "delta12_historical_nav"), ("Gamma-6", "gamma6_historical_nav"),
                            ("Oro", "oro_historical_nav")):
        monkeypatch.setattr(rp, funcion, lambda *a, _n=nombre, **k: _serie(_n, [100., 110.], fechas))
    r = _calcular()
    assert r["año"][CONJUNTO] == pytest.approx(.10)
    assert r["cinco_años"] is None and r["retroceso"] is None


def test_sin_el_cierre_del_año_anterior_no_hay_numero(series, monkeypatch):
    """Una pieza que parte en enero no tiene desde dónde medirse, y sin ella el número es otro."""
    monkeypatch.setattr(rp, "oro_historical_nav", lambda *a, **k: _serie("Oro", [200., 200.], FECHAS[5:]))
    assert _calcular() is None
    monkeypatch.setattr(rp, "oro_historical_nav", lambda *a, **k: pd.DataFrame(columns=["date", "Oro"]))
    assert _calcular() is None


def test_una_pieza_que_no_se_sabe_reconstruir_no_se_inventa(series):
    assert _calcular(reparto={"Delta-12": .5, "Otra": .5}) is None
    assert _calcular(reparto={}) is None
