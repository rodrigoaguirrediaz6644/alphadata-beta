from pathlib import Path

import pandas as pd
import pytest

from src.benchmark_ipsa import en_base_100, leer

FILAS = [
    '"Fecha","Último","Apertura","Máximo","Mínimo","Vol.","% var."',
    '"17.09.2026","11.381,18","11.250,40","11.394,40","11.250,40","","1,30%"',
    '"16.09.2026","11.235,60","11.338,42","11.372,75","11.235,54","","-0,77%"',
    '"08.07.2021","4.188,16","4.150,00","4.200,00","4.140,00","","0,50%"',
]


def _archivo(tmp_path: Path) -> Path:
    ruta = tmp_path / "indice.csv"
    ruta.write_text("\n".join(FILAS) + "\n", encoding="utf-8-sig")
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


# --- La canasta que reemplaza al indice manual -----------------------------

def _panel():
    """Dos acciones, una de las cuales se lista tarde, mas IPSA_TR y un ADR."""
    filas = []
    for i, f in enumerate(["2026-01-05", "2026-01-06", "2026-01-07"]):
        filas.append({"date": f, "alphadata_ticker": "AAA", "adjusted_close": 100. * (1.10 ** i)})
        filas.append({"date": f, "alphadata_ticker": "IPSA_TR", "adjusted_close": 5000.})
        filas.append({"date": f, "alphadata_ticker": "LTM-ADR", "adjusted_close": 9.})
    # BBB se lista el segundo dia: no puede inventar retorno el primero.
    filas.append({"date": "2026-01-06", "alphadata_ticker": "BBB", "adjusted_close": 50.})
    filas.append({"date": "2026-01-07", "alphadata_ticker": "BBB", "adjusted_close": 60.})
    return pd.DataFrame(filas).assign(date=lambda d: pd.to_datetime(d.date))


def test_la_canasta_no_mira_el_indice_manual_ni_los_adr():
    """El punto de todo el cambio: el benchmark deja de depender de una descarga.

    Si borrar `IPSA_TR` del almacen moviera la canasta, la dependencia seguiria
    ahi disfrazada.
    """
    from src.run_pipeline import canasta_chilena
    p = _panel()
    con = canasta_chilena(p)
    sin = canasta_chilena(p[~p.alphadata_ticker.isin(["IPSA_TR", "LTM-ADR", "SQM-ADR"])])
    assert list(con.round(9)) == list(sin.round(9))


def test_una_accion_que_se_lista_tarde_entra_sin_inventar_retorno():
    """El primer dia de BBB no tiene rueda anterior: se promedia sobre AAA sola.

    Sin esto, una accion nueva entraria con un retorno de la nada y la canasta
    saltaria el dia de cada listado.
    """
    from src.run_pipeline import canasta_chilena
    c = canasta_chilena(_panel())
    assert c.iloc[0] == pytest.approx(100.)
    assert c.iloc[1] == pytest.approx(110.)            # solo AAA, +10%
    assert c.iloc[2] == pytest.approx(110. * 1.15)     # AAA +10% y BBB +20%, partes iguales
