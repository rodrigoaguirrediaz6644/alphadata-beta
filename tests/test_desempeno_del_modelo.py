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


def _calcular(reparto=REPARTO, as_of=AS_OF, precios=None):
    vacio = pd.DataFrame(columns=["date", "alphadata_ticker", "adjusted_close"])
    return rp.desempeño_del_modelo(as_of, vacio if precios is None else precios, vacio, vacio, vacio,
                                   pd.DataFrame(columns=["cdv_ticker"]), reparto, .001785)


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


# --------------------------------------------------------------------------
# la línea del IPSA real en el gráfico
# --------------------------------------------------------------------------

def _ipsa(fechas, valores):
    return pd.DataFrame({"date": pd.to_datetime(fechas), "alphadata_ticker": "IPSA_TR",
                         "adjusted_close": valores})


def test_el_grafico_lleva_el_ipsa_real_en_base_100_desde_el_mismo_dia(series):
    """La serie del gráfico parte del último día que la tabla usa para los cinco años."""
    precios = _ipsa(FECHAS, [50., 100., 110., 150., 200., 210., 240.])
    s = _calcular(precios=precios)["serie"]
    assert "IPSA" in s.columns
    assert s["date"].iloc[0] == pd.Timestamp("2021-01-29")
    assert s["IPSA"].iloc[0] == 100. and s["IPSA"].iloc[-1] == pytest.approx(240.)


def test_los_dias_sin_dato_del_ipsa_no_se_consideran(monkeypatch):
    """Un hueco chico se arrastra; uno grande deja la línea terminar donde terminan los datos."""
    fechas = pd.to_datetime(["2021-01-05", "2021-01-06", "2025-12-30", *pd.bdate_range("2026-01-02", periods=12)])
    for nombre, funcion in (("Delta-12", "delta12_historical_nav"), ("Gamma-6", "gamma6_historical_nav"),
                            ("Oro", "oro_historical_nav")):
        monkeypatch.setattr(rp, funcion, lambda *a, _n=nombre, **k: _serie(_n, [100.] * len(fechas), fechas))
    conocidas = fechas[:7]                       # el IPSA llega hasta la 4ª rueda de 2026
    precios = _ipsa(conocidas, [100., 100., 150., 151., 152., 153., 154.])
    s = _calcular(as_of=fechas[-1], precios=precios)["serie"].set_index("date")["IPSA"]
    ultimo = s.loc[conocidas[-1]]
    # Cinco ruedas arrastradas con el último valor, y desde ahí sin línea: nunca inventado.
    assert (s.loc[fechas[7:12]] == ultimo).all()
    assert s.loc[fechas[12:]].isna().all() and len(s.loc[fechas[12:]]) == 3


def test_sin_ipsa_guardado_no_hay_linea_y_no_se_reemplaza_por_otra_cosa(series):
    """Antes que rotular «Ipsa» una canasta, no dibujar la línea."""
    s = _calcular()["serie"]
    assert "IPSA" not in s.columns and "Mercado chileno" not in s.columns
    assert {"Delta-12", "Gamma-6", "Oro", CONJUNTO} <= set(s.columns)


def test_el_almacen_con_otros_instrumentos_no_se_confunde_con_el_ipsa(series):
    precios = pd.concat([_ipsa(FECHAS, [50., 100., 110., 150., 200., 210., 240.]),
                         pd.DataFrame({"date": FECHAS, "alphadata_ticker": "COPEC", "adjusted_close": 6000.})])
    assert "IPSA" in _calcular(precios=precios)["serie"].columns
