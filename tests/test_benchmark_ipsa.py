from pathlib import Path

import pandas as pd
import pytest

from src.benchmark_ipsa import en_base_100, leer


def _archivo(tmp_path: Path) -> Path:
    ruta = tmp_path / "indice.csv"
    ruta.write_text(
        '"Fecha","Último","Apertura","Máximo","Mínimo","Vol.","% var."
'
        '"17.09.2026","11.381,18","11.250,40","11.394,40","11.250,40","","1,30%"
'
        '"16.09.2026","11.235,60","11.338,42","11.372,75","11.235,54","","-0,77%"
'
        '"08.07.2021","4.188,16","4.150,00","4.200,00","4.140,00","","0,50%"
',
        encoding="utf-8-sig",
    )
    return ruta


def test_el_formato_europeo_se_lee_sin_confundir_la_fecha_con_un_numero(tmp_path):
    # Con thousands="." pandas leería 17.09.2026 como el entero 17092026 y la
    # columna de fechas quedaría en NaT sin que nada avise.
    serie = leer(_archivo(tmp_path))
    assert list(serie.index) == [pd.Timestamp("2021-07-08"), pd.Timestamp("2026-09-16"), pd.Timestamp("2026-09-17")]
    assert serie.iloc[0] == pytest.approx(4188.16)
    assert serie.iloc[-1] == pytest.approx(11381.18)


def test_la_base_100_toma_la_ultima_rueda_disponible(tmp_path):
    serie = leer(_archivo(tmp_path))
    valor = en_base_100(serie, pd.Timestamp("2021-07-08"), pd.Timestamp("2026-09-17"))
    assert valor == pytest.approx(11381.18 / 4188.16 * 100, rel=1e-9)
    # Un fin de semana toma la rueda anterior, no falla ni interpola.
    assert en_base_100(serie, pd.Timestamp("2021-07-10"), pd.Timestamp("2026-09-19")) == pytest.approx(valor)


def test_una_ventana_fuera_del_indice_se_rechaza(tmp_path):
    serie = leer(_archivo(tmp_path))
    with pytest.raises(ValueError):
        en_base_100(serie, pd.Timestamp("2015-01-01"), pd.Timestamp("2026-09-17"))
