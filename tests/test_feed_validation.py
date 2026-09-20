import pandas as pd

from src.feed_validation import aprueba, comparar, serie_guardada


def _serie(valores, inicio="2026-01-05"):
    fechas = pd.bdate_range(inicio, periods=len(valores))
    return pd.Series(valores, index=fechas, dtype=float)


def test_una_fuente_identica_calza_en_todos_los_dias():
    base = _serie([100 + i for i in range(60)])
    r = comparar(base, base)
    assert r["razon_mediana"] == 1.0 and r["exactos"] == 1.0 and r["desvio_p95"] == 0.0
    assert aprueba(r)


def test_una_serie_ajustada_por_dividendos_no_es_la_misma_convencion():
    # El caso SALFACORP: el candidato publica la serie ajustada y la guardada es
    # cruda. La razón mediana se va de 1 y no se están comparando los mismos
    # números, aunque la forma de la curva sea idéntica.
    base = _serie([100 + i for i in range(60)])
    r = comparar(base * .958, base)
    assert abs(r["razon_mediana"] - .958) < 1e-9
    assert not aprueba(r)


def test_una_serie_congelada_no_pasa():
    # El defecto que originó todo esto: el proveedor repite el último cierre.
    base = _serie([100 + i for i in range(60)])
    congelada = base.copy()
    congelada.iloc[30:] = congelada.iloc[29]
    r = comparar(congelada, base)
    assert not aprueba(r)


def test_un_ajuste_por_dividendo_aparece_como_bloque_y_no_como_ruido():
    base = _serie([100 + i for i in range(60)])
    candidato = base.copy()
    candidato.iloc[:20] = candidato.iloc[:20] * .97  # días previos al ex-dividendo
    r = comparar(candidato, base)
    assert len(r["bloques"]) == 1
    bloque = r["bloques"][0]
    assert bloque["dias"] == 20 and abs(bloque["factor"] - .97) < 1e-6


def test_sin_tramo_comun_no_se_aprueba_nada():
    a = _serie([1, 2, 3], inicio="2026-01-05")
    b = _serie([1, 2, 3], inicio="2026-06-01")
    r = comparar(a, b)
    assert r["dias"] == 0 and not aprueba(r)


def test_la_serie_guardada_sale_del_panel_por_ticker():
    panel = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-05"), "alphadata_ticker": "BCI", "close": 100.0},
        {"date": pd.Timestamp("2026-01-06"), "alphadata_ticker": "BCI", "close": 101.0},
        {"date": pd.Timestamp("2026-01-05"), "alphadata_ticker": "ILC", "close": 50.0},
    ])
    serie = serie_guardada(panel, "BCI")
    assert list(serie) == [100.0, 101.0]
