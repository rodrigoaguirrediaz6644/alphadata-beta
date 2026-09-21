"""La tabla de dividendos se propone, se verifica y recién entonces se registra.

El riesgo aquí no es dejar un dividendo fuera: es anotar uno que no existió.
Una fila inventada en la tabla apaga la alarma por salto justo en la fecha en
que debía sonar.
"""

import numpy as np
import pandas as pd
import pytest

from src.dividendos import alarma_por_salto, proponer

DIAS = pd.bdate_range("2026-01-05", periods=60)
EX = DIAS[30]


def _cruda() -> pd.Series:
    """Serie cruda que cae 5% el día ex y sigue su camino."""
    serie = pd.Series(np.linspace(100, 118, len(DIAS)), index=DIAS)
    serie.loc[DIAS[30:]] = serie.loc[DIAS[30:]] * .95
    return serie


def _ajustada(cruda: pd.Series, factor: float = .95) -> pd.Series:
    """La misma serie vista por una fuente que ajusta hacia atrás."""
    ajustada = cruda.copy()
    ajustada.loc[DIAS[:30]] = ajustada.loc[DIAS[:30]] * factor
    return ajustada


def test_un_dividendo_real_se_propone_con_su_fecha_y_su_factor():
    cruda = _cruda()
    propuesta = proponer(_ajustada(cruda), cruda, "BCI")
    aceptadas = propuesta[propuesta.veredicto == "dividendo"]
    assert len(aceptadas) == 1
    fila = aceptadas.iloc[0]
    assert fila.fecha_ex == EX
    assert fila.factor == pytest.approx(.95, abs=1e-3)
    assert fila.dividendo_pct == pytest.approx(.05, abs=1e-3)


def test_un_escalon_sin_caida_en_la_serie_cruda_no_se_registra():
    # La fuente ajustada dice que hubo reparto, pero el precio crudo no cayó.
    # Sin respaldo no entra: puede ser un defecto de la fuente.
    cruda = pd.Series(np.linspace(100, 118, len(DIAS)), index=DIAS)  # sin caída
    propuesta = proponer(_ajustada(cruda), cruda, "BCI")
    assert "dividendo" not in set(propuesta.veredicto)
    assert "sin_respaldo" in set(propuesta.veredicto)


def test_un_bache_que_revierte_no_es_un_dividendo():
    # Las dos fuentes discrepan una semana y vuelven a coincidir. Es un defecto
    # de datos: CHILE marcó esto entre el 17 y el 21 de marzo de 2025, con
    # nuestra serie 8% arriba, y después volvió a cuadrar.
    cruda = pd.Series(np.linspace(100, 118, len(DIAS)), index=DIAS)
    ajustada = cruda.copy()
    ajustada.loc[DIAS[30:35]] = ajustada.loc[DIAS[30:35]] * .92
    propuesta = proponer(ajustada, cruda, "CHILE")
    assert "dividendo" not in set(propuesta.veredicto)
    assert "bache_transitorio" in set(propuesta.veredicto)


def test_dos_series_identicas_no_proponen_nada():
    cruda = pd.Series(np.linspace(100, 118, len(DIAS)), index=DIAS)
    assert proponer(cruda, cruda, "BCI").empty


# --- la alarma, que es la parte que sí queda operando ------------------------

def _panel(valores: dict[str, list[float]]) -> pd.DataFrame:
    fechas = pd.bdate_range("2026-05-04", periods=max(len(v) for v in valores.values()))
    filas = [{"date": f, "alphadata_ticker": t, "close": v}
             for t, serie in valores.items() for f, v in zip(fechas, serie)]
    return pd.DataFrame(filas)


def test_una_caida_fuerte_sin_dividendo_registrado_suena():
    panel = _panel({"ILC": [100, 100, 93, 93]})
    alarma = alarma_por_salto(panel)
    assert len(alarma) == 1
    assert alarma.iloc[0].alphadata_ticker == "ILC"
    assert alarma.iloc[0].retorno == pytest.approx(-.07)


def test_la_misma_caida_con_dividendo_registrado_no_suena():
    panel = _panel({"ILC": [100, 100, 93, 93]})
    tabla = pd.DataFrame([{"alphadata_ticker": "ILC", "fecha_ex": pd.Timestamp("2026-05-06")}])
    assert alarma_por_salto(panel, tabla).empty


def test_una_caida_moderada_no_suena():
    panel = _panel({"ILC": [100, 100, 97, 97]})
    assert alarma_por_salto(panel).empty


def test_los_dividendos_de_las_posiciones_vivas_estan_confirmados():
    """Envejecen fuera de la señal, no fuera de la pantalla.

    Los 127 fechados por convención se dejaron así porque salen de la ventana
    del momentum 12-1 en un año. Eso vale para la señal, no para el número
    publicado: la variación se calcula desde la entrada hasta hoy, y sin tope de
    tenencia esa ventana crece con la posición.

    El alcance se define solo: los que caen dentro de la ventana de tenencia de
    una posición viva. Si aparece uno nuevo sin confirmar, esta prueba lo dice.
    """
    import pandas as pd
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    libro_csv, dividendos_csv = raiz / "data" / "libro_posiciones.csv", raiz / "data" / "dividendos.csv"
    if not (libro_csv.exists() and dividendos_csv.exists()):
        import pytest
        pytest.skip("sin libro o sin tabla de dividendos")
    libro = pd.read_csv(libro_csv, parse_dates=["fecha_entrada", "fecha_salida"])
    d = pd.read_csv(dividendos_csv, parse_dates=["fecha_ex"])
    vivas = libro[libro.fecha_salida.isna() & (libro.origen != "calentamiento")]
    sin_confirmar = []
    for fila in vivas.itertuples():
        dentro = d[(d.alphadata_ticker == fila.instrumento) & (d.fecha_ex > fila.fecha_entrada)]
        sin_confirmar += [f"{fila.instrumento} {x.fecha_ex.date()}"
                          for x in dentro.itertuples()
                          if pd.isna(x.caida_observada) and pd.isna(x.caida_por_contraste)]
    # De todo lo que sostiene una cifra publicada hoy, queda **un solo dato sin
    # respaldo de precio**: MALLPLAZA del 03-09-2026, cuya ventana cae dentro
    # del tramo del feed congelado. Está identificado, corroborado en magnitud
    # y calendario contra la fuente primaria, y documentado en
    # research/dividendos/CONFIRMACION_POR_CONTRASTE.md.
    conocidos = {"MALLPLAZA 2026-09-03"}
    assert set(sin_confirmar) <= conocidos, f"sin confirmar y sin documentar: {sorted(set(sin_confirmar) - conocidos)}"
