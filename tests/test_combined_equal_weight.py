"""El conjunto cae menos que todas sus piezas. Estas pruebas exigen que sea real.

Una caída combinada por debajo de la de cada componente es la firma de la
diversificación, pero también la de un error de suavizado: si se promediaran
los niveles de NAV en vez de componer los retornos con rebalanceo mensual, la
curva saldría artificialmente lisa y el retroceso quedaría subestimado. Los
casos de abajo se pueden calcular a mano, así que distinguen una cosa de la
otra sin ambigüedad.
"""

import numpy as np
import pandas as pd
import pytest

from src.strategy_engine import combined_equal_weight

DIAS = pd.bdate_range("2026-01-02", "2026-03-31")
FEBRERO = DIAS[DIAS.to_period("M") == pd.Period("2026-02")]
MARZO = DIAS[DIAS.to_period("M") == pd.Period("2026-03")]


def _caida_en(mes) -> pd.Series:
    """Una serie que vale 100, cae 20% a lo largo de `mes` y se queda ahí."""
    serie = pd.Series(100.0, index=DIAS)
    serie.loc[mes] = np.linspace(100, 80, len(mes))
    serie.loc[DIAS[DIAS > mes[-1]]] = 80.0
    return serie


def _combinar(**series) -> pd.Series:
    frame = pd.DataFrame({"date": DIAS, **{k: v.to_numpy() for k, v in series.items()}})
    return combined_equal_weight(frame, list(series))


def _caida(serie: pd.Series) -> float:
    return float((serie / serie.cummax() - 1).min())


def test_dos_caidas_en_meses_distintos_dan_el_retroceso_calculado_a_mano():
    # A cae 20% en febrero, B cae 20% en marzo. Con rebalanceo a partes iguales
    # al cierre de cada mes:
    #   fin de febrero: 100 x (0,8 + 1,0)/2 = 90
    #   fin de marzo:    90 x (1,0 + 0,8)/2 = 81
    # El retroceso es -19%, menor que el -20% de cada pieza. Promediar niveles
    # daría 80 y un retroceso de -20%.
    combinada = _combinar(A=_caida_en(FEBRERO), B=_caida_en(MARZO))
    assert combinada.iloc[-1] == pytest.approx(81.0)
    assert _caida(combinada) == pytest.approx(-.19)


def test_dos_caidas_en_el_mismo_mes_no_dan_ningun_beneficio():
    # Control: si las dos caen a la vez, no hay nada que diversificar y el
    # retroceso combinado tiene que ser el mismo de las piezas.
    combinada = _combinar(A=_caida_en(FEBRERO), B=_caida_en(FEBRERO))
    assert _caida(combinada) == pytest.approx(-.20)


def test_una_pieza_plana_amortigua_exactamente_a_la_mitad():
    plana = pd.Series(100.0, index=DIAS)
    combinada = _combinar(A=_caida_en(FEBRERO), B=plana)
    assert _caida(combinada) == pytest.approx(-.10)


def test_el_rebalanceo_ocurre_de_verdad_al_cambiar_de_mes():
    # Sin rebalanceo, la pieza que cayó pesaría menos al empezar marzo y el
    # resultado final sería distinto de 81.
    combinada = _combinar(A=_caida_en(FEBRERO), B=_caida_en(MARZO))
    sin_rebalanceo = (_caida_en(FEBRERO) + _caida_en(MARZO)) / 2
    assert sin_rebalanceo.iloc[-1] == pytest.approx(80.0)
    assert combinada.iloc[-1] != pytest.approx(sin_rebalanceo.iloc[-1])


def test_una_pieza_que_todavia_no_existe_no_entra_al_promedio():
    # Gamma-6 y el oro empiezan después que las chilenas: mientras no tienen
    # dato, el conjunto reparte entre las que sí lo tienen.
    tardia = pd.Series(np.nan, index=DIAS)
    tardia.loc[MARZO] = 100.0
    combinada = _combinar(A=_caida_en(FEBRERO), B=tardia)
    # Durante febrero el conjunto es sólo A, así que cae lo mismo que A.
    hasta_febrero = combinada.loc[combinada.index <= FEBRERO[-1]]
    assert _caida(hasta_febrero) == pytest.approx(-.20)
