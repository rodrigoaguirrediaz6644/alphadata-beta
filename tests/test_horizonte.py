import pandas as pd

from src import horizonte
from src.horizonte import backtest, monthly_features


def test_five_signals_are_boolean_and_threshold_selects_a():
    dates = pd.date_range("2020-01-01", periods=800, freq="D")
    cuotas = pd.DataFrame(
        {
            "date": dates,
            "a": [100 + i * .20 for i in range(len(dates))],
            "e": [100 + i * .02 for i in range(len(dates))],
        }
    )
    external = pd.DataFrame(
        {
            "date": dates,
            "nasdaq": [100 + i * .10 for i in range(len(dates))],
            "vix": [20.0] * len(dates),
        }
    )
    features = monthly_features(cuotas, external)
    latest = features.dropna(subset=["recommendation"]).iloc[-1]
    assert latest["score"] == 5
    assert latest["recommendation"] == "A"
    for column in [
        "relative_momentum",
        "absolute_momentum",
        "cuprum_a_trend",
        "nasdaq_trend",
        "vix_below_30",
    ]:
        assert bool(latest[column]) is True


def test_switch_executes_on_fourth_subsequent_quote():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    cuotas = pd.DataFrame({"date": dates, "a": range(100, 200), "e": range(200, 300)})
    signal_date = dates[30]
    features = pd.DataFrame({"recommendation": ["A"]}, index=[signal_date])
    _, trades = backtest(cuotas, features)
    assert trades.iloc[0]["execution_date"] == dates[34].date().isoformat()


def test_download_retries_before_succeeding(monkeypatch):
    attempts = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"ok"

    def fake_urlopen(request, timeout):
        attempts.append(timeout)
        if len(attempts) < 3:
            raise TimeoutError("temporary")
        return Response()

    monkeypatch.setattr(horizonte, "urlopen", fake_urlopen)
    monkeypatch.setattr(horizonte.time, "sleep", lambda _: None)
    assert horizonte._download("https://example.test", attempts=3, timeout=5) == "ok"
    assert attempts == [5, 5, 5]


def test_external_uses_cache_when_both_sources_fail(monkeypatch, tmp_path):
    cache = tmp_path / "external.csv"
    expected = pd.DataFrame(
        {"date": pd.to_datetime(["2026-07-24"]), "nasdaq": [23000.0], "vix": [17.0]}
    )
    expected.to_csv(cache, index=False)
    monkeypatch.setattr(horizonte, "DATA", tmp_path)
    monkeypatch.setattr(horizonte, "EXTERNAL_CACHE", cache)
    monkeypatch.setattr(horizonte, "_download", lambda _: (_ for _ in ()).throw(TimeoutError()))
    monkeypatch.setattr(
        horizonte, "_fetch_external_secondary", lambda: (_ for _ in ()).throw(RuntimeError())
    )
    result = horizonte._fetch_external()
    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


def test_la_completitud_de_los_insumos_se_verifica():
    """Una corrida anterior tenía huecos en 2012 y nadie se enteró.

    Eran treinta y cuatro días —332 datos donde el recálculo encontró 366— y
    que el resumen publicado no se moviera con eso fue suerte, no control. El
    valor cuota se publica todos los días calendario, así que un día ausente en
    el rango es un hueco y no un feriado.
    """
    import pandas as pd
    from src.horizonte import verificar_completitud
    dias = pd.date_range("2026-01-01", "2026-09-16", freq="D")
    cuotas = pd.DataFrame({"date": dias, "a": 1.0, "e": 1.0})
    externas = pd.DataFrame({"date": pd.bdate_range("2026-01-01", "2026-09-18"),
                             "nasdaq": 1.0, "vix": 1.0})
    ahora = pd.Timestamp("2026-09-21")
    assert verificar_completitud(cuotas, externas, ahora) == []

    con_hueco = cuotas[~cuotas.date.isin(pd.date_range("2026-05-04", "2026-05-08"))]
    assert "faltan 5 dias calendario" in verificar_completitud(con_hueco, externas, ahora)[0]

    con_nulo = cuotas.copy(); con_nulo.loc[con_nulo.index[10], "a"] = None
    assert "nulos" in " ".join(verificar_completitud(con_nulo, externas, ahora))

    viejas = cuotas[cuotas.date <= "2026-08-01"]
    assert "sin actualizarse" in " ".join(verificar_completitud(viejas, externas, ahora))
