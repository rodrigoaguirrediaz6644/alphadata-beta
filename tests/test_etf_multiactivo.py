"""Tests de las funciones puras del análisis de candidatos ETF. No requieren red."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.etf_multiactivo.analisis import a_pesos, clasificar, correlaciones, metricas_por_instrumento, selector_rotacion, serie_fx


def _panel(n: int = 400, seed: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fechas = pd.bdate_range("2024-01-01", periods=n)
    base = rng.normal(0.0004, 0.01, n)
    return pd.DataFrame({
        "COPIA": 100 * np.cumprod(1 + base),                                  # igual a la estrategia
        "OPUESTO": 100 * np.cumprod(1 - base),                                # espejo
        "AJENO": 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, n)),           # independiente
    }, index=fechas)


def _navs(panel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"Conjunto AlphaData": panel["COPIA"]}, index=panel.index)


def test_serie_fx_toma_solo_el_tipo_de_cambio():
    precios = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-05"]),
        "alphadata_ticker": ["USDCLP", "USDCLP", "BCI"],
        "adjusted_close": [900.0, 910.0, 31000.0],
    })
    fx = serie_fx(precios)
    assert list(fx) == [900.0, 910.0]
    assert serie_fx(precios[precios.alphadata_ticker == "BCI"]).empty


def test_a_pesos_convierte_solo_lo_que_esta_en_dolares_y_arrastra_el_ultimo_valor():
    panel = pd.DataFrame({"TLT": [100.0, 100.0, 100.0], "CFILOCAL": [1000.0, 1000.0, 1000.0]},
                         index=pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"]))
    fx = pd.Series([900.0, 950.0], index=pd.to_datetime(["2026-01-05", "2026-01-06"]))
    convertido = a_pesos(panel, fx, ["TLT"])
    assert convertido["TLT"].tolist() == [90000.0, 95000.0, 95000.0]   # el último día arrastra 950
    assert convertido["CFILOCAL"].tolist() == [1000.0, 1000.0, 1000.0]  # el local no se toca
    assert a_pesos(panel, pd.Series(dtype=float), ["TLT"]).equals(panel)


def test_correlaciones_distinguen_copia_espejo_e_independiente():
    panel = _panel()
    tabla = correlaciones(panel, _navs(panel))
    assert tabla.loc["COPIA", "Conjunto AlphaData"] == pytest.approx(1.0, abs=1e-6)
    assert tabla.loc["OPUESTO", "Conjunto AlphaData"] < -0.9
    assert abs(tabla.loc["AJENO", "Conjunto AlphaData"]) < 0.5
    assert tabla.loc["COPIA", "meses_comunes"] >= 12


def test_correlaciones_no_inventan_con_pocos_datos():
    panel = _panel(n=40)   # menos de 12 meses
    tabla = correlaciones(panel, _navs(panel))
    assert tabla["Conjunto AlphaData"].isna().all()


def test_clasificar_etiqueta_por_cuanto_aporta():
    tabla = pd.DataFrame({"Conjunto AlphaData": [0.95, 0.60, 0.30, 0.05, np.nan]},
                         index=["REDUNDANTE", "POCO", "APORTA", "DIVERSIFICA", "NUEVO"])
    etiquetas = clasificar(tabla)
    assert etiquetas["REDUNDANTE"] == "redundante"
    assert etiquetas["POCO"] == "aporta poco"
    assert etiquetas["APORTA"] == "aporta"
    assert etiquetas["DIVERSIFICA"] == "diversifica"
    assert etiquetas["NUEVO"] == "sin historia suficiente"


def test_metricas_por_instrumento_reportan_historia_y_riesgo():
    panel = _panel()
    panel.loc[panel.index[:200], "AJENO"] = np.nan   # historia corta
    tabla = metricas_por_instrumento(panel)
    assert tabla.loc["AJENO", "sesiones"] == 200
    assert tabla.loc["COPIA", "sesiones"] == len(panel)
    assert tabla.loc["COPIA", "mdd"] <= 0


def test_selector_rotacion_exige_historia_y_respeta_el_filtro_de_tendencia():
    n = 400
    fechas = pd.bdate_range("2024-01-01", periods=n)
    panel = pd.DataFrame({
        "SUBE": 100 * np.exp(np.linspace(0, .8, n)),
        "BAJA": 100 * np.exp(np.linspace(0, -.6, n)),
        "NUEVO": [np.nan] * (n - 50) + list(100 * np.exp(np.linspace(0, .9, 50))),
    }, index=fechas)
    pesos, elegibles = selector_rotacion(2, solo_tendencia=True)(panel, fechas[-1])
    assert "NUEVO" not in pesos.index     # sin 252 sesiones no entra
    assert "BAJA" not in pesos.index      # bajo su SMA200 no entra
    assert pesos.sum() == pytest.approx(1.0) and elegibles >= 1
    pesos_corto, _ = selector_rotacion(2)(panel.iloc[:100], panel.index[99])
    assert pesos_corto.empty
