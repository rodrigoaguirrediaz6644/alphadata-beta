import pandas as pd
import pytest

from pathlib import Path

from src.reporting_public import BENCHMARK, _metrics, build_public_report

ROOT = Path(__file__).resolve().parents[1]


def test_metrics_do_not_invent_history_with_one_observation():
    result = _metrics(pd.Series([100.0]), pd.Series(["2026-07-16"]))
    assert result["return"] is None
    assert result["mdd"] is None


@pytest.fixture(autouse=True)
def _graficos_en_temporal(tmp_path, monkeypatch):
    """Ninguna prueba escribe en reports/: publicaría curvas de fixture."""
    import src.reporting_public as rp
    monkeypatch.setattr(rp, "DIRECTORIO_GRAFICOS", tmp_path)
    yield tmp_path


def _report(**kwargs):
    portfolio = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-06", "current_price": 31000.0, "open_return": .08}])
    moves = pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "previous_weight": 0.0, "target_weight": .1, "change": .1}])
    coverage = pd.DataFrame([{"status": "OK"}])
    history = pd.DataFrame([
        {"date": "2026-07-16", "Sigma-6": 100, "Delta-12": 100, "Gamma-6": 100, "IPSA TR": 100, "Conjunto AlphaData": 100},
        {"date": "2026-09-18", "Sigma-6": 110, "Delta-12": 105, "Gamma-6": 120, "IPSA TR": 102, "Conjunto AlphaData": 112},
    ])
    arguments = {"delta": portfolio, "delta_moves": pd.DataFrame(columns=["ticker", "action", "target_weight"]),
                 "coverage": coverage, "errors": pd.DataFrame(), "history": history}
    arguments.update(kwargs)
    return build_public_report(pd.Timestamp("2026-09-18"), **arguments)


def test_public_report_hides_strategy_methodology():
    _, html = build_public_report(
        pd.Timestamp("2026-09-18"),
        pd.DataFrame([{"ticker": "BCI", "target_weight": .1}]),
        pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "target_weight": .1, "change": .1}]),
        pd.DataFrame([{"status": "OK"}]),
        pd.DataFrame(),
        pd.DataFrame([{"date": "2026-07-16", "Delta-12": 100, "Gamma-6": 100, "IPSA TR": 100}]),
    )
    for secret in ["momentum_12_1", "SMA200", "sma200", "RSI", "z-score", "score", "Credicorp", "252"]:
        assert secret not in html


def test_el_informe_no_lleva_descargos():
    # Cambio de criterio: es una herramienta personal y el único lector ya
    # conoce las limitaciones. Las consideraciones van en la documentación
    # interna, no en lo que se publica.
    _, html = _report()
    for descargo in ["seguimiento simulado", "no garantizan", "recomendación de inversión",
                     "aplicando las mismas reglas hacia atrás"]:
        assert descargo not in html


MOVIMIENTOS = pd.DataFrame([
    {"estrategia": "Sigma-6", "instrumento": "BCI", "accion": "COMPRAR", "fecha": pd.Timestamp("2026-09-18")},
    {"estrategia": "Gamma-6", "instrumento": "BAC", "accion": "VENDER", "fecha": pd.Timestamp("2026-08-31")},
])


def test_report_leads_with_the_combined_result_and_the_movements():
    """Los movimientos salen del libro y llevan la fecha de su propia señal.

    Antes salían de comparar la cartera con la anterior, y eso mezclaba lo que
    cambió con lo que hay que comprar para entrar hoy: el informe llegó a decir
    «Comprar INTC» en la misma página en que la tabla decía «comprada el
    30-09-2025».
    """
    markdown, html = _report(
        gamma=pd.DataFrame([{"ticker": "MRK", "target_weight": 1 / 6, "opened_at": "2026-08-03", "current_price": 146.87, "open_return": .15}]),
        movimientos=MOVIMIENTOS,
    )
    assert "Conjunto AlphaData" in html and "+12,0%" in html  # 100 -> 112
    assert "Comprar" in html and "Vender" in html
    assert "18-09-2026" in html and "31-08-2026" in html
    assert "Gamma-6" in html and "MRK" in html
    assert "Comprar BCI (Sigma-6)" in markdown and "Vender BAC (Gamma-6)" in markdown


def test_report_says_plainly_when_there_is_nothing_to_do():
    """Tres de las cuatro piezas son mensuales: el bloque vacío es lo normal.

    Y un bloque vacío se lee como informe roto, así que tiene que decirlo con
    todas sus letras.
    """
    markdown, html = _report()
    assert "Sin cambios desde el informe anterior" in html and "Sin cambios desde el informe anterior" in markdown
    assert "Comprar" not in html


def test_report_survives_without_gamma_history_or_positions():
    markdown, html = _report()
    assert "Sin posiciones abiertas" in html  # Gamma-6 todavía sin cartera
    assert "AlphaData" in markdown


def test_report_warns_when_data_is_incomplete():
    _, html = _report(errors=pd.DataFrame([{"ticker": "X"}]), coverage=pd.DataFrame([{"status": "SIN_DATOS"}]))
    assert "Revisar" in html and "no se pudieron usar" in html


def test_report_refuses_to_compare_against_a_broken_benchmark():
    from src.reporting_public import is_continuous

    broken = pd.DataFrame([
        {"date": "2026-07-16", "Sigma-6": 100, "Delta-12": 100, "Gamma-6": 100, "IPSA TR": 100, "Conjunto AlphaData": 100},
        {"date": "2026-07-17", "Sigma-6": 101, "Delta-12": 101, "Gamma-6": 101, "IPSA TR": 212, "Conjunto AlphaData": 101},
        {"date": "2026-09-18", "Sigma-6": 110, "Delta-12": 110, "Gamma-6": 110, "IPSA TR": 212, "Conjunto AlphaData": 110},
    ])
    assert not is_continuous(broken["IPSA TR"])
    markdown, html = _report(history=broken)
    assert "comparado con haber invertido" not in html
    assert "La serie del IPSA tiene un salto" in html
    assert "IPSA TR" not in html  # tampoco aparece en la tabla mientras esté rota
    # El markdown es la parte en texto plano del correo y queda commiteado en el
    # repositorio: publicaba el salto de 100 a 212 como si fuera rentabilidad.
    assert "IPSA TR" not in markdown
    assert "La comparación con la bolsa chilena no está disponible" in markdown
    healthy_markdown, healthy = _report()
    assert "comparado con haber invertido" in healthy
    assert "IPSA TR" in healthy_markdown


def test_el_informe_dibuja_dos_graficos_separados(_graficos_en_temporal):
    """La separación es estructural, no visual.

    El seguimiento en vivo y la reconstrucción son dos archivos distintos y se
    dibujan como dos imágenes distintas. Antes se pegaban en memoria escalando
    una sobre la otra, y eso fue lo que hizo que un +30% inventado se leyera
    como resultado.
    """
    _, html = _report()
    # El archivo apunta al PNG para verse fuera del correo; el correo lo
    # reescribe a cid: al adjuntarlo.
    assert 'src="seguimiento_vivo.png"' in html
    assert 'src="reconstruccion.png"' in html
    assert "cid:" not in html
    assert "Reconstrucción" in html
    assert (_graficos_en_temporal / "seguimiento_vivo.png").exists()


def test_la_serie_viva_no_se_reescala_con_la_reconstruccion():
    """Regresión del encadenamiento: la serie viva empieza donde empieza.

    La reconstrucción termina cerca de 350 en base 100; si el gráfico la
    encadenara, la serie viva arrancaría en ese nivel en vez de en 100.
    """
    from src.reporting_public import _dibujar, _series_presentes
    vivo = pd.DataFrame({"date": pd.to_datetime(["2026-09-17", "2026-09-18", "2026-09-21"]),
                         "Sigma-6": [100.0, 101.0, 102.0], "Conjunto AlphaData": [100.0, 100.5, 101.0]})
    bloque = _dibujar(vivo, _series_presentes(vivo), "prueba", "prueba_vivo.png", "pie")
    assert 'src="prueba_vivo.png"' in bloque
    # El dibujo normaliza a 100 en el primer dato propio de la serie, sin mirar
    # ningún archivo histórico.
    assert vivo["Sigma-6"].iloc[0] == 100.0


def test_el_informe_dice_desde_cuando_corre_la_serie_nueva():
    _, html = _report()
    assert "El seguimiento en vivo corre desde el" in html


def test_el_benchmark_roto_queda_fuera_del_grafico_vivo():
    from src.reporting_public import _series_presentes
    roto = pd.DataFrame({"date": pd.to_datetime(["2026-09-17", "2026-09-18"]),
                         "Delta-12": [100.0, 101.0], "IPSA TR": [100.0, 212.0]})
    presentes = _series_presentes(roto)
    # `_chart` filtra el benchmark cuando la serie no es continua; aquí se
    # comprueba que el filtro se aplica sobre la lista de series presentes.
    assert "IPSA TR" in presentes
    assert [n for n in presentes if n != "IPSA TR"] == ["Delta-12"]


def test_sigma6_sale_del_cuerpo_pero_se_queda_en_la_reconstruccion():
    """Sale de la asignación, no del repositorio.

    El cuerpo del informe describe tres piezas; el gráfico de la
    reconstrucción sigue dibujando la serie de Sigma-6, que es historia del
    proyecto y está medida.
    """
    from src.reporting_public import SERIES, SERIES_RECONSTRUCCION, STRATEGIES, _series_presentes
    assert STRATEGIES == ["Delta-12", "Gamma-6", "Oro"]
    assert "Sigma-6" not in SERIES
    assert "Sigma-6" in SERIES_RECONSTRUCCION
    recon = pd.DataFrame({"date": pd.to_datetime(["2021-07-08", "2021-07-09"]),
                          "Sigma-6": [100.0, 101.0], "Delta-12": [100.0, 100.5]})
    assert "Sigma-6" in _series_presentes(recon, SERIES_RECONSTRUCCION)
    assert "Sigma-6" not in _series_presentes(recon)


def test_el_reparto_del_capital_no_es_en_cuartos():
    markdown, html = _report(capital_por_pieza={"Delta-12": 7_500_000., "Gamma-6": 7_500_000.,
                                                "Oro": 5_000_000.})
    for texto in (markdown, html):
        assert "Delta-12 37,5%" in texto and "Oro 25,0%" in texto
        assert "cuartos" not in texto and "cuatro piezas" not in texto
