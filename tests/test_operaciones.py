"""La cuenta real contra la cartera del modelo.

Desde que hay plata de verdad existe una falla que antes no podia: **tener
comprado algo que el modelo ya vendio**. Nada la detectaria sola, porque el
informe habla de la cartera del modelo y la cuenta habla de otra cosa, y las dos
se ven sanas por separado.
"""

import pandas as pd
import pytest

from src.operaciones import descalce, tenencias
from src.salud import revisar

CAMPOS = ["estrategia", "instrumento", "accion", "estado", "cantidad"]


def _ops(filas):
    return pd.DataFrame(filas, columns=CAMPOS)


def test_lo_que_el_modelo_ya_no_tiene_y_sigue_en_la_cuenta_se_avisa():
    ops = _ops([("Gamma-6", "TGT", "COMPRA", "EJECUTADA", 8),
                ("Gamma-6", "INTC", "COMPRA", "EJECUTADA", 12)])
    assert descalce(ops, {"Gamma-6": ["TGT"]}) == ["INTC"]


def test_una_orden_que_no_se_ejecuto_no_pone_nada_en_la_cuenta():
    ops = _ops([("Gamma-6", "INTC", "COMPRA", "NO_EJECUTADA", 0),
                ("Gamma-6", "TGT", "COMPRA", "ANULADA", 0)])
    assert tenencias(ops) == {}
    assert descalce(ops, {"Gamma-6": []}) == []


def test_una_posicion_vendida_entera_deja_de_estar_en_la_cuenta():
    ops = _ops([("Gamma-6", "INTC", "COMPRA", "EJECUTADA", 12),
                ("Gamma-6", "INTC", "VENTA", "EJECUTADA", 12)])
    assert tenencias(ops) == {}
    assert descalce(ops, {"Gamma-6": []}) == []


def test_una_venta_parcial_deja_el_resto_y_por_eso_sigue_contando():
    ops = _ops([("Gamma-6", "INTC", "COMPRA", "EJECUTADA", 12),
                ("Gamma-6", "INTC", "VENTA", "PARCIAL", 5)])
    assert tenencias(ops) == {"INTC": 7.}
    assert descalce(ops, {"Gamma-6": []}) == ["INTC"]


def test_las_cantidades_no_tienen_que_calzar_y_eso_no_es_una_alarma():
    """La primera compra real fue de 8 IAUCL contra 63 de referencia.

    Si la guardia mirara cantidades sonaria siempre, y una alarma que suena
    siempre deja de ser alarma. Mira instrumentos.
    """
    ops = _ops([("Oro", "IAU", "COMPRA", "EJECUTADA", 8)])
    assert descalce(ops, {"Oro": ["IAU"]}) == []


def test_sin_operaciones_registradas_el_panel_no_inventa_una_alarma():
    def revisa(d):
        return [c for c in revisar(
            as_of=pd.Timestamp("2026-09-22"), precios_al_dia=True, series_detenidas=set(),
            cobertura_incompleta=set(), series_recalculadas={"A"}, series_publicadas={"A"},
            carteras_reproducidas=True, dias_sin_recomendaciones=10, umbral_vigencia=90,
            dividendos_sin_respaldo=set(), suite_verde=True, descalce_real=d)[0]
            if c.nombre == "Cuenta real"][0]

    assert revisa(None).sano
    assert revisa([]).sano
    roto = revisa(["INTC"])
    assert not roto.sano and "INTC" in roto.detalle


def test_un_deslistado_y_uno_acumulando_no_son_fallas_de_cobertura():
    """Las dos alarmas que llevaban meses apartadas se cierran solas ahora.

    AESANDES dejo de cotizar el 14-04-2025 y eso es un hecho sabido, no un
    defecto. MULTIFOODS tiene historia corta porque se le corrigio el simbolo y
    suma una rueda por dia. Ninguna de las dos puede seguir encendiendo el
    panel: una alarma que suena siempre deja de ser alarma.
    """
    from src.run_pipeline import _incompletos
    cobertura = pd.DataFrame([
        {"alphadata_ticker": "AESANDES", "status": "DESLISTADO"},
        {"alphadata_ticker": "MULTIFOODS", "status": "ACUMULANDO"},
        {"alphadata_ticker": "CHILE", "status": "OK"},
        {"alphadata_ticker": "BCI", "status": "DETENIDO"},
    ])
    assert _incompletos(cobertura) == {"BCI"}


def test_lo_deslistado_no_entra_a_la_canasta_del_benchmark():
    """AESANDES arrastraba el benchmark **4,48%** hacia abajo.

    Su ultimo precio sigue en el almacen y la canasta lo leia como un retorno
    de 0% todos los dias. Un benchmark mas bajo es una vara mas facil, o sea el
    error apuntaba en la direccion que halaga a las estrategias, y no se veia
    como una falla: se veia como una accion que no se mueve.
    """
    from src.run_pipeline import canasta_chilena
    dias = pd.bdate_range("2026-01-01", periods=30)
    filas = []
    for i, d in enumerate(dias):
        filas.append({"date": d, "alphadata_ticker": "VIVA", "adjusted_close": 100. * 1.01 ** i})
        filas.append({"date": d, "alphadata_ticker": "MUERTA", "adjusted_close": 50.})
    p = pd.DataFrame(filas)
    con = canasta_chilena(p)
    sin = canasta_chilena(p, fuera={"MUERTA"})
    assert sin.iloc[-1] > con.iloc[-1], "la serie congelada tiene que estar diluyendo"
    assert sin.iloc[-1] == pytest.approx(100 * 1.01 ** 29)
