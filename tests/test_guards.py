from pathlib import Path

import pandas as pd

from src.guards import adr_contra_local, contraste_entre_fuentes, ruedas_sin_variacion, series_detenidas

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


def _panel(valores: dict[str, list[float]], inicio="2026-08-03") -> pd.DataFrame:
    fechas = pd.bdate_range(inicio, periods=max(len(v) for v in valores.values()))
    filas = []
    for ticker, serie in valores.items():
        for fecha, valor in zip(fechas, serie):
            filas.append({"date": fecha, "alphadata_ticker": ticker, "close": valor, "adjusted_close": valor})
    return pd.DataFrame(filas)


# --- guardia 1: serie sin variación -------------------------------------------------

def test_cuenta_las_ruedas_que_un_precio_lleva_sin_moverse():
    panel = _panel({"VIVO": [100, 101, 102, 103, 104, 105], "MUERTO": [100, 100, 100, 100, 100, 100]})
    cuenta = ruedas_sin_variacion(panel)
    assert cuenta["VIVO"] == 0
    assert cuenta["MUERTO"] == 5
    assert list(series_detenidas(panel)) == ["MUERTO"]


def test_una_serie_quieta_pocos_dias_no_se_marca_detenida():
    panel = _panel({"PAUSADO": [100, 100, 100, 101, 102, 103]})
    assert len(series_detenidas(panel)) == 0


def test_el_incidente_de_2026_aparece_como_series_detenidas():
    # Regresión con datos reales: entre julio y agosto de 2026 estos papeles
    # repetían el mismo cierre y coverage_report.csv seguía diciendo OK.
    detenidas = set(series_detenidas(_precios_del_incidente()))
    assert {"BCI", "PARAUCO", "ILC", "BSANTANDER"} <= detenidas


# --- guardia 2: contraste entre fuentes ---------------------------------------------

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


# --- guardia 3: ADR contra acción local ---------------------------------------------

def test_el_adr_delata_el_mercado_local_detenido_apenas_ocurre():
    # Con los datos reales del incidente: en las dos semanas siguientes al
    # congelamiento del 17-07-2026, LTM-ADR se movió en Nueva York mientras
    # LTM no se movió nada en Santiago. Esta guardia lo habría dicho entonces,
    # no dos meses después.
    quincena = _precios_del_incidente().query("'2026-07-18' <= date <= '2026-07-31'")
    alarma = adr_contra_local(quincena, ventana=10)
    assert "LTM" in set(alarma.local)
    assert alarma.loc[alarma.local == "LTM", "movimiento_local"].iloc[0] == 0.0


def test_el_adr_delata_los_dos_pares_en_agosto():
    agosto = _precios_del_incidente().query("'2026-08-01' <= date <= '2026-08-31'")
    alarma = adr_contra_local(agosto, ventana=20)
    assert set(alarma.local) == {"LTM", "SQM-B"}
    assert (alarma.movimiento_adr > .10).all()  # los ADR se movieron más de 10%


def test_un_mercado_local_que_se_mueve_no_dispara_la_guardia():
    panel = _panel({"LTM-ADR": [10, 10.5, 11, 11.2], "LTM": [100, 104, 108, 110]})
    assert adr_contra_local(panel, ventana=4).empty
