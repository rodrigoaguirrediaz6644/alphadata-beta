"""El IPSA real, una rueda por día.

Lo que se prueba, en orden de cuánto duele que falle: que **no se grabe un dato
malo** —el almacén no permite corregir—, que no se empalme otra serie, y que un
día sin dato no rompa nada.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src import indice_ipsa as ii

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "capture-daily.yml"


def _guardado(ultimo="2026-09-17", nivel=11381.18):
    fechas = pd.to_datetime(["2026-09-14", "2026-09-15", "2026-09-16", ultimo])
    valores = [11342.39, 11322.60, 11235.60, nivel]
    ipsa = pd.DataFrame({"date": fechas, "alphadata_ticker": "IPSA_TR", "yahoo_ticker": "MSCI_IPSA_GROSS",
                         "open": 1., "high": 1., "low": 1., "close": valores, "adjusted_close": valores,
                         "volume": 0.})
    otra = pd.DataFrame({"date": fechas, "alphadata_ticker": "COPEC", "yahoo_ticker": "COPEC.SN",
                         "open": 1., "high": 1., "low": 1., "close": 6000., "adjusted_close": 6000., "volume": 1.})
    return pd.concat([ipsa, otra], ignore_index=True)


def _cuerpo(niveles, moneda="CLP", variante="GRTR", codigo="767564"):
    return {"msci_index_code": codigo, "index_variant_type": variante, "ISO_currency_symbol": moneda,
            "indexes": {"INDEX_LEVELS": [{"level_eod": v, "calc_date": int(d)} for d, v in niveles]}}


# Lo que MSCI devolvió de verdad el 29-09-2026: el 17 y el 18 con el mismo nivel
# salvo por la última cifra, porque el 18 fue feriado.
REAL = [("20260914", 11342.387717253094), ("20260915", 11322.595236087142), ("20260916", 11235.604059562234),
        ("20260917", 11381.183653564593), ("20260918", 11381.183653564589), ("20260921", 11357.824655526565),
        ("20260922", 11426.75385058773), ("20260923", 11449.630449297509), ("20260924", 11299.821617406817),
        ("20260925", 11256.802128444906), ("20260928", 11137.22575894797)]


def test_agrega_solo_las_ruedas_posteriores_y_salta_el_feriado():
    r, n = ii.actualizar(_guardado(), descargar=lambda d, h: _cuerpo(REAL), hoy=date(2026, 9, 29))
    ipsa = r[r.alphadata_ticker == "IPSA_TR"].set_index("date").adjusted_close
    assert n == 6
    assert list(ipsa.index.strftime("%m-%d"))[-6:] == ["09-21", "09-22", "09-23", "09-24", "09-25", "09-28"]
    assert pd.Timestamp("2026-09-18") not in ipsa.index          # el feriado repite el 17
    assert ipsa.loc["2026-09-28"] == pytest.approx(11137.23) and ipsa.loc["2026-09-21"] == 11357.82


def test_lo_ya_grabado_no_se_toca_y_una_segunda_corrida_no_agrega_nada():
    g = _guardado()
    r, _ = ii.actualizar(g, descargar=lambda d, h: _cuerpo(REAL), hoy=date(2026, 9, 29))
    viejo = r.merge(g, on=["alphadata_ticker", "date"], suffixes=("", "_g"))
    assert (viejo.adjusted_close == viejo.adjusted_close_g).all() and len(viejo) == len(g)
    r2, n2 = ii.actualizar(r, descargar=lambda d, h: _cuerpo(REAL), hoy=date(2026, 9, 29))
    assert n2 == 0 and len(r2) == len(r)


def test_las_otras_series_del_almacen_no_se_tocan():
    g = _guardado()
    r, _ = ii.actualizar(g, descargar=lambda d, h: _cuerpo(REAL), hoy=date(2026, 9, 29))
    columnas = list(g.columns)
    assert r.loc[r.alphadata_ticker == "COPEC", columnas].reset_index(drop=True).equals(
        g.loc[g.alphadata_ticker == "COPEC", columnas].reset_index(drop=True))


def test_las_filas_nuevas_llevan_el_mismo_formato_que_las_guardadas():
    r, _ = ii.actualizar(_guardado(), descargar=lambda d, h: _cuerpo(REAL), hoy=date(2026, 9, 29))
    nueva = r[(r.alphadata_ticker == "IPSA_TR") & (r.date == "2026-09-22")].iloc[0]
    assert nueva.yahoo_ticker == "MSCI_IPSA_GROSS" and nueva.close == nueva.adjusted_close == 11426.75
    assert pd.isna(nueva.open) and pd.isna(nueva.volume)


def test_sin_dias_nuevos_no_agrega_nada():
    hasta_el_17 = [x for x in REAL if x[0] <= "20260917"]
    _, n = ii.actualizar(_guardado(), descargar=lambda d, h: _cuerpo(hasta_el_17), hoy=date(2026, 9, 18))
    assert n == 0


def test_pide_con_solape_para_poder_comparar():
    pedido = {}

    def falso(desde, hasta):
        pedido.update(desde=desde, hasta=hasta)
        return _cuerpo(REAL)

    ii.actualizar(_guardado(), descargar=falso, hoy=date(2026, 9, 29))
    assert pedido["desde"] == date(2026, 9, 7) and pedido["hasta"] == date(2026, 9, 29)


# --------------------------------------------------------------------------
# lo que NO se agrega
# --------------------------------------------------------------------------

def test_si_los_niveles_ya_no_calzan_con_lo_guardado_no_se_agrega_nada():
    """Es el empalme de dos series: ya produjo un salto de 100 a 212 en el NAV."""
    en_dolares = [(d, v * .975) for d, v in REAL]
    with pytest.raises(ValueError, match="ya no calzan"):
        ii.actualizar(_guardado(), descargar=lambda d, h: _cuerpo(en_dolares), hoy=date(2026, 9, 29))


@pytest.mark.parametrize("kwargs", [{"moneda": "USD"}, {"variante": "NETR"}, {"codigo": "990300"}])
def test_otra_moneda_variante_o_indice_se_rechaza(kwargs):
    with pytest.raises(ValueError, match="otra serie"):
        ii.actualizar(_guardado(), descargar=lambda d, h: _cuerpo(REAL, **kwargs), hoy=date(2026, 9, 29))


def test_un_salto_imposible_no_se_graba():
    """El almacén no permite corregir: un valor malo quedaría fijo para siempre."""
    malo = REAL[:6] + [("20260922", 11426.75 * 1.5)]
    with pytest.raises(ValueError, match="no es creíble"):
        ii.actualizar(_guardado(), descargar=lambda d, h: _cuerpo(malo), hoy=date(2026, 9, 29))


def test_un_error_de_msci_no_se_confunde_con_datos():
    error = {"error_code": "  300", "error_message": " Invalid Parameter currency : 'X'"}
    with pytest.raises(ValueError, match="MSCI respondió con error"):
        ii.actualizar(_guardado(), descargar=lambda d, h: error, hoy=date(2026, 9, 29))


def test_niveles_vacios_o_no_positivos_se_rechazan():
    with pytest.raises(ValueError, match="no positivos"):
        ii.niveles(_cuerpo([("20260921", 0.), ("20260922", 11400.)]))
    assert ii.niveles(_cuerpo([])).empty


def test_sin_historial_no_se_empalma_una_serie_en_el_aire():
    sin_ipsa = _guardado().query("alphadata_ticker != 'IPSA_TR'")
    with pytest.raises(ValueError, match="No hay historial"):
        ii.actualizar(sin_ipsa, descargar=lambda d, h: _cuerpo(REAL), hoy=date(2026, 9, 29))


def test_un_solape_sin_coincidencias_no_se_da_por_bueno():
    lejano = [("20260101", 10000.), ("20260102", 10010.)]
    with pytest.raises(ValueError, match="Ningún día del solape"):
        ii.actualizar(_guardado(), descargar=lambda d, h: _cuerpo(lejano), hoy=date(2026, 9, 29))


def test_los_niveles_repetidos_se_reconocen_aunque_difieran_en_la_cifra_doce():
    serie = pd.Series([11381.183653564593, 11381.183653564589, 11357.82],
                      index=pd.to_datetime(["2026-09-17", "2026-09-18", "2026-09-21"]))
    assert list(ii.sin_repetidos(serie).index.strftime("%m-%d")) == ["09-17", "09-21"]


# --------------------------------------------------------------------------
# el flujo
# --------------------------------------------------------------------------

def test_la_captura_diaria_trae_el_ipsa_sin_que_una_falla_detenga_el_cierre_chileno():
    texto = WORKFLOW.read_text(encoding="utf-8")
    paso = texto[texto.index("- name: Capturar el IPSA"):texto.index("- name: Guardar el cierre capturado")]
    assert "continue-on-error: true" in paso and "python -m src.indice_ipsa" in paso
    # Corre antes de guardar, para que la fila nueva entre al mismo commit.
    assert texto.index("Capturar el IPSA") < texto.index("Guardar el cierre capturado")
    assert "data/market_prices_daily.csv" in texto[texto.index("Guardar el cierre capturado"):]


# --------------------------------------------------------------------------
# la alerta de atraso
# --------------------------------------------------------------------------

LOCALES = {"COPEC"}


def _mercado(hasta, ipsa_hasta):
    """COPEC diaria hasta `hasta` y el IPSA hasta `ipsa_hasta`, ambos en días hábiles."""
    def serie(ticker, fin):
        fechas = pd.bdate_range("2026-08-03", fin)
        return pd.DataFrame({"date": fechas, "alphadata_ticker": ticker, "adjusted_close": 100.})
    return pd.concat([serie("COPEC", hasta), serie("IPSA_TR", ipsa_hasta)], ignore_index=True)


def test_al_dia_o_con_el_atraso_normal_no_avisa():
    # MSCI publica con un día de atraso: el lunes trae hasta el viernes.
    assert ii.vigilar(_mercado("2026-09-28", "2026-09-28"), LOCALES) is None
    assert ii.vigilar(_mercado("2026-09-28", "2026-09-25"), LOCALES) is None
    assert ii.atraso(_mercado("2026-09-28", "2026-09-24"), LOCALES)[1] == 2


def test_justo_en_el_limite_no_avisa_y_un_dia_mas_si():
    assert ii.MAX_ATRASO_HABILES == 4
    assert ii.vigilar(_mercado("2026-09-28", "2026-09-22"), LOCALES) is None        # 4 ruedas hábiles
    mensaje = ii.vigilar(_mercado("2026-09-28", "2026-09-21"), LOCALES)             # 5
    assert mensaje and "5 ruedas hábiles" in mensaje and "21-09-2026" in mensaje


def test_se_mide_contra_el_mercado_chileno_y_no_contra_el_calendario():
    """Si toda la captura está detenida, el problema es otro y ya lo avisan otras guardias."""
    detenido = _mercado("2026-09-01", "2026-09-01")
    assert ii.atraso(detenido, LOCALES)[1] == 0 and ii.vigilar(detenido, LOCALES) is None


def test_el_fin_de_semana_no_cuenta_como_atraso():
    assert ii.atraso(_mercado("2026-09-28", "2026-09-25"), LOCALES)[1] == 1         # viernes a lunes


def test_sin_historial_o_sin_mercado_no_se_da_por_al_dia():
    """Que no se pueda medir no puede leerse como que está al día."""
    sin_ipsa = _mercado("2026-09-28", "2026-09-28").query("alphadata_ticker != 'IPSA_TR'")
    assert "No se pudo medir" in ii.vigilar(sin_ipsa, LOCALES)
    assert "No se pudo medir" in ii.vigilar(_mercado("2026-09-28", "2026-09-28"), {"OTRA"})


def test_la_vigilancia_va_despues_de_guardar_y_no_puede_impedir_el_guardado():
    texto = WORKFLOW.read_text(encoding="utf-8")
    paso = texto[texto.index("- name: Vigilar el IPSA"):texto.index("- name: Avisar por correo")]
    assert "python -m src.indice_ipsa vigilar" in paso and "continue-on-error" not in paso
    # El cierre chileno se commitea antes: una falla de MSCI no lo pierde.
    assert texto.index("Guardar el cierre capturado") < texto.index("Vigilar el IPSA") < texto.index("Avisar por correo")


def test_el_aviso_de_atraso_no_dice_que_se_perdio_el_cierre_chileno():
    from src import aviso_falla as av
    asunto, cuerpo = av.mensaje("Captura diaria del cierre chileno", ["capturar › Vigilar el IPSA"],
                                "https://github.com/x/y/actions/runs/1", "schedule")
    assert asunto == "AlphaData — el IPSA del informe está atrasado"
    assert "sí quedó guardado" in cuerpo and "no se puede bajar después" not in cuerpo
    # Si además falló otra cosa, se dice lo de todo el flujo.
    _, ambos = av.mensaje("Captura diaria del cierre chileno",
                          ["capturar › Capturar el cierre del día", "capturar › Vigilar el IPSA"], "u", "schedule")
    assert "no se puede bajar después" in ambos
