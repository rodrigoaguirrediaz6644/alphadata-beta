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

from tools.construir_libro import CALENTAMIENTO, DESDE, DESDE_CALENTAMIENTO, ORO_FECHA_DECISION, SIN_REPARAR, _revisiones, recorrer

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


def test_el_tramo_de_calentamiento_se_conserva_y_no_se_publica():
    """El recorrido arranca un año antes del piso, y ese tramo no se muestra.

    Sin calentar, BCI quedaba con entrada el 16-01-2026; con el estado correcto
    al entrar a la ventana queda el 24-10-2025. Las filas del tramo previo
    sirven para auditar y para los contadores de tenencia, pero vienen de datos
    sin reparar: se conservan sin precio y no se publican nunca.
    """
    libro = ROOT / "data" / "libro_posiciones.csv"
    if not libro.exists():
        pytest.skip("todavía no se ha construido el libro")
    d = pd.read_csv(libro, parse_dates=["fecha_entrada", "fecha_salida"])
    assert DESDE_CALENTAMIENTO < DESDE
    antes = d.loc[d.fecha_entrada < DESDE]
    assert len(antes)
    # Las cerradas no se publican y no llevan precio.
    calienta = antes.loc[antes.fecha_salida.notna()]
    assert (calienta.origen == CALENTAMIENTO).all()
    assert calienta.precio_entrada.isna().all()
    # Pero una **abierta** sí se publica, con su precio y marcada: ocultarle la
    # fecha a una posición viva es peor que mostrar una del tramo sin reparar.
    # Es el caso de BCI, en cartera desde el 11-10-2024.
    vivas = antes.loc[antes.fecha_salida.isna()]
    assert (vivas.origen == SIN_REPARAR).all()
    assert vivas.precio_entrada.notna().all()
    # Y ninguna publicable queda sin precio.
    publicable = d.loc[(d.origen != CALENTAMIENTO) & (d.estrategia != "Oro")]
    assert publicable.precio_entrada.notna().all()
    assert (publicable.loc[publicable.origen != SIN_REPARAR, "fecha_entrada"] >= DESDE).all()


def test_el_libro_no_entrega_filas_de_calentamiento_a_quien_las_mostraria():
    from src.libro import abiertas, precios_de_entrada
    libro = pd.DataFrame([
        {"estrategia": "Sigma-6", "instrumento": "VIEJA", "fecha_entrada": pd.Timestamp("2024-03-01"),
         "precio_entrada": None, "fecha_salida": pd.NaT, "origen": CALENTAMIENTO},
        {"estrategia": "Sigma-6", "instrumento": "BCI", "fecha_entrada": pd.Timestamp("2025-10-24"),
         "precio_entrada": 46502., "fecha_salida": pd.NaT, "origen": "recorrido"},
    ])
    assert set(abiertas(libro, "Sigma-6")) == {"BCI"}
    assert precios_de_entrada(libro, "Sigma-6") == {"BCI": 46502.}


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
