import pandas as pd
import pytest

from src.reporting_public import BENCHMARK, _metrics, build_public_report, chart_frame


def test_metrics_do_not_invent_history_with_one_observation():
    result = _metrics(pd.Series([100.0]), pd.Series(["2026-07-16"]))
    assert result["return"] is None
    assert result["mdd"] is None


def _report(**kwargs):
    portfolio = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-06", "current_price": 31000.0, "open_return": .08}])
    moves = pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "previous_weight": 0.0, "target_weight": .1, "change": .1}])
    coverage = pd.DataFrame([{"status": "OK"}])
    history = pd.DataFrame([
        {"date": "2026-07-16", "Sigma-6": 100, "Delta-12": 100, "Gamma-6": 100, "IPSA TR": 100, "Conjunto AlphaData": 100},
        {"date": "2026-09-18", "Sigma-6": 110, "Delta-12": 105, "Gamma-6": 120, "IPSA TR": 102, "Conjunto AlphaData": 112},
    ])
    arguments = {"sigma": portfolio, "delta": portfolio, "sigma_moves": moves, "delta_moves": pd.DataFrame(columns=["ticker", "action", "target_weight"]),
                 "coverage": coverage, "errors": pd.DataFrame(), "history": history}
    arguments.update(kwargs)
    return build_public_report(pd.Timestamp("2026-09-18"), **arguments)


def test_public_report_hides_strategy_methodology():
    _, html = build_public_report(
        pd.Timestamp("2026-09-18"),
        pd.DataFrame([{"ticker": "BCI", "target_weight": .1}]),
        pd.DataFrame([{"ticker": "BCI", "target_weight": .1}]),
        pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "target_weight": .1, "change": .1}]),
        pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "target_weight": .1, "change": .1}]),
        pd.DataFrame([{"status": "OK"}]),
        pd.DataFrame(),
        pd.DataFrame([{"date": "2026-07-16", "Sigma-6": 100, "Delta-12": 100, "IPSA TR": 100}]),
    )
    assert "información reservada" in html
    for secret in ["momentum_12_1", "SMA200", "sma200", "RSI", "z-score", "score", "Credicorp", "252"]:
        assert secret not in html


def test_report_leads_with_the_combined_result_and_the_weekly_orders():
    markdown, html = _report(
        gamma=pd.DataFrame([{"ticker": "MRK", "target_weight": 1 / 6, "opened_at": "2026-08-03", "current_price": 146.87, "open_return": .15}]),
        gamma_moves=pd.DataFrame([{"ticker": "BAC", "action": "SALE", "previous_weight": 1 / 6, "target_weight": 0.0, "change": -1 / 6}]),
    )
    assert "Conjunto AlphaData" in html and "+12,0%" in html  # 100 -> 112
    assert "Comprar" in html and "Vender" in html and "toda la posición" in html
    assert "Gamma-6" in html and "MRK" in html
    assert "Comprar BCI (Sigma-6)" in markdown and "Vender BAC (Gamma-6)" in markdown


def test_report_says_plainly_when_there_is_nothing_to_do():
    _, html = _report(sigma_moves=pd.DataFrame([{"ticker": "BCI", "action": "MANTIENE", "previous_weight": .1, "target_weight": .1, "change": 0.0}]))
    assert "No hay nada que comprar ni vender" in html
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


def _historial(tmp_path):
    ruta = tmp_path / "historical_model_nav.csv"
    pd.DataFrame([
        {"date": "2021-07-08", "Sigma-6": 100.0, "Delta-12": 100.0, "IPSA Total Return": 100.0, "Conjunto AlphaData": 100.0},
        {"date": "2026-07-15", "Sigma-6": 300.0, "Delta-12": 400.0, "IPSA Total Return": 260.0, "Conjunto AlphaData": 350.0},
    ]).to_csv(ruta, index=False)
    return ruta


def _vivo():
    return pd.DataFrame([
        {"date": "2026-07-16", "Sigma-6": 100.0, "Delta-12": 100.0, "IPSA TR": 100.0, "Conjunto AlphaData": 100.0},
        {"date": "2026-09-18", "Sigma-6": 110.0, "Delta-12": 105.0, "IPSA TR": 102.0, "Conjunto AlphaData": 112.0},
    ])


def test_el_grafico_llega_hasta_la_fecha_de_la_corrida(tmp_path):
    # La reconstrucción histórica no crece: si el gráfico sólo la mira, se
    # queda donde terminó y se atrasa una semana por cada corrida.
    historial = _historial(tmp_path)
    data = chart_frame(_vivo(), historical_path=historial)
    assert data["date"].max() == pd.Timestamp("2026-09-18")


def test_el_grafico_encadena_la_serie_viva_en_vez_de_reiniciarla(tmp_path):
    historial = _historial(tmp_path)
    antes = historial.read_text(encoding="utf-8")
    data = chart_frame(_vivo(), historical_path=historial).set_index("date")
    assert data.loc[pd.Timestamp("2026-07-15"), "Sigma-6"] == pytest.approx(300.0)
    assert data.loc[pd.Timestamp("2026-07-16"), "Sigma-6"] == pytest.approx(300.0)  # sin desplome a 100
    assert data.loc[pd.Timestamp("2026-09-18"), "Sigma-6"] == pytest.approx(330.0)  # 300 x 110/100
    assert data.loc[pd.Timestamp("2026-09-18"), "Conjunto AlphaData"] == pytest.approx(392.0)
    assert historial.read_text(encoding="utf-8") == antes  # el historial publicado no se reescribe


def test_el_grafico_deja_fuera_el_benchmark_roto(tmp_path):
    historial = _historial(tmp_path)
    data = chart_frame(_vivo(), historical_path=historial, benchmark_usable=False)
    assert BENCHMARK not in data
    assert BENCHMARK in chart_frame(_vivo(), historical_path=historial)
