"""El libro de posiciones: cuándo entró cada una y a qué precio.

El riesgo de un recorrido histórico no es que falle: es que produzca un libro
perfectamente verosímil y equivocado. Por eso lo que se prueba acá es el
calendario, el ciclo de vida de una posición y el borde de la ventana; la
prueba que de verdad decide —reproducir las carteras publicadas— vive dentro
del propio comando y lo detiene si no calza.
"""

from pathlib import Path

import pandas as pd
import pytest

from tools.construir_libro import DESDE, ORO_FECHA_DECISION, _revisiones, recorrer

ROOT = Path(__file__).resolve().parents[1]
SESIONES = pd.DatetimeIndex(pd.bdate_range("2026-01-01", "2026-09-17"))


def test_la_revision_mensual_descarta_el_mes_en_curso():
    # Es la regla de producción: el corte es `as_of.to_period('M') - 1`, o sea
    # el último día del mes anterior. Tomar el 17-09 como revisión daba una
    # cartera distinta de la publicada, porque septiembre no ha terminado.
    revisiones = _revisiones(SESIONES, "M", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-09-17"))
    assert max(revisiones) < pd.Timestamp("2026-09-01")
    assert max(revisiones).month == 8


def test_la_revision_semanal_si_llega_hasta_el_final():
    revisiones = _revisiones(SESIONES, "W-FRI", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-09-17"))
    assert max(revisiones) >= pd.Timestamp("2026-09-11")


def test_una_posicion_que_entra_y_sigue_abierta_queda_sin_fecha_de_salida():
    fechas = [pd.Timestamp(f) for f in ["2026-01-30", "2026-02-27", "2026-03-31"]]
    carteras = {fechas[0]: ["BCI"], fechas[1]: ["BCI", "CHILE"], fechas[2]: ["BCI", "CHILE"]}
    movimientos, abiertas = recorrer("Delta-12", fechas, lambda f: carteras[f])
    assert abiertas == {"BCI", "CHILE"}
    por_ticker = {m["instrumento"]: m for m in movimientos}
    assert por_ticker["BCI"]["fecha_entrada"] == fechas[0]
    assert pd.isna(por_ticker["BCI"]["fecha_salida"])
    assert por_ticker["CHILE"]["fecha_entrada"] == fechas[1]


def test_una_posicion_que_sale_queda_con_la_fecha_de_la_revision_que_la_soltó():
    fechas = [pd.Timestamp(f) for f in ["2026-01-30", "2026-02-27", "2026-03-31"]]
    carteras = {fechas[0]: ["BCI"], fechas[1]: [], fechas[2]: []}
    movimientos, abiertas = recorrer("Delta-12", fechas, lambda f: carteras[f])
    assert abiertas == set()
    assert movimientos[0]["fecha_entrada"] == fechas[0]
    assert movimientos[0]["fecha_salida"] == fechas[1]


def test_una_posicion_que_vuelve_a_entrar_abre_de_nuevo():
    fechas = [pd.Timestamp(f) for f in ["2026-01-30", "2026-02-27", "2026-03-31"]]
    carteras = {fechas[0]: ["BCI"], fechas[1]: [], fechas[2]: ["BCI"]}
    movimientos, abiertas = recorrer("Delta-12", fechas, lambda f: carteras[f])
    assert len(movimientos) == 2
    assert abiertas == {"BCI"}
    cerrada = [m for m in movimientos if pd.notna(m["fecha_salida"])][0]
    reabierta = [m for m in movimientos if pd.isna(m["fecha_salida"])][0]
    assert cerrada["fecha_salida"] == fechas[1]
    assert reabierta["fecha_entrada"] == fechas[2]


def test_el_libro_publicado_marca_el_borde_y_no_inventa_fechas():
    """Una entrada en la primera fecha del recorrido no tiene fecha real."""
    libro = ROOT / "data" / "libro_posiciones.csv"
    if not libro.exists():
        pytest.skip("todavía no se ha construido el libro")
    d = pd.read_csv(libro, parse_dates=["fecha_entrada", "fecha_salida"])
    borde = d.loc[d.fecha_entrada <= DESDE]
    assert (borde.origen.str.contains("borde")).all()
    assert borde.precio_entrada.isna().all()
    # Y ninguna posición del interior queda sin precio.
    interior = d.loc[(d.fecha_entrada > DESDE) & (d.estrategia != "Oro")]
    assert interior.precio_entrada.notna().all()


def test_el_oro_entra_por_decision_y_no_por_senal():
    libro = ROOT / "data" / "libro_posiciones.csv"
    if not libro.exists():
        pytest.skip("todavía no se ha construido el libro")
    d = pd.read_csv(libro, parse_dates=["fecha_entrada"])
    oro = d.loc[d.estrategia == "Oro"]
    assert len(oro) == 1
    # 01-01-2026 es feriado: la fecha es la de la decisión y el precio, el de la
    # primera rueda del año. No es un error que corregir.
    assert oro.fecha_entrada.iloc[0] == ORO_FECHA_DECISION
    assert oro.precio_entrada.iloc[0] > 0


def test_el_libro_no_contiene_ninguna_columna_de_nav():
    """La línea que no se cruza: el libro no habla de rendimiento de cartera."""
    libro = ROOT / "data" / "libro_posiciones.csv"
    if not libro.exists():
        pytest.skip("todavía no se ha construido el libro")
    columnas = set(pd.read_csv(libro, nrows=1).columns)
    assert not (columnas & {"nav", "NAV", "retorno", "rendimiento", "Conjunto AlphaData"})
