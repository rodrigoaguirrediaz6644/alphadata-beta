"""La guardia de vigencia del benchmark mira la canasta, no `IPSA_TR`.

El benchmark publicado es la canasta igual peso y `IPSA_TR` es la serie manual
que reemplazó. La guardia seguía exigiéndole vigencia a la serie vieja y abortó
la corrida oficial por un dato que el cálculo ya no lee.

Entra el almacén por un lado y el calendario por el otro: medida contra su
propia última fecha, una serie detenida siempre tiene rezago cero.
"""

import pandas as pd
import pytest

from src.fetch_prices import MAX_BENCHMARK_LAG_BUSINESS_DAYS, exigir_canasta_fresca, frescura_de_la_canasta

# Lunes 28-09-2026. Tres días hábiles atrás es el miércoles 23.
HOY = pd.Timestamp("2026-09-28")


def _universo(*filas):
    return pd.DataFrame(
        [{"alphadata_ticker": t, "yahoo_ticker": t, "nombre": t, "tipo": tipo, "moneda": "CLP", "estado": estado}
         for t, tipo, estado in filas]
    )


def _precios(**ultima_fecha):
    return pd.DataFrame(
        [{"date": pd.Timestamp(fecha), "alphadata_ticker": t, "close": 100.0, "adjusted_close": 100.0}
         for t, fecha in ultima_fecha.items()]
    )


CHILENAS = _universo(("AAA", "accion_local", "activo"), ("BBB", "accion_sigma", "activo"),
                     ("CCC", "accion_local", "activo"), ("IPSA_TR", "benchmark", "manual"))


def test_ipsa_tr_atrasado_no_detiene_la_corrida_si_la_canasta_esta_al_dia():
    """El caso que abortó la corrida del 27-09-2026."""
    precios = _precios(AAA="2026-09-28", BBB="2026-09-28", CCC="2026-09-28", IPSA_TR="2026-09-17")
    exigir_canasta_fresca(precios, CHILENAS, HOY)
    assert frescura_de_la_canasta(precios, CHILENAS, HOY) == (pd.Timestamp("2026-09-28"), 0)


def test_ipsa_tr_al_dia_no_salva_una_canasta_atrasada():
    """La vigencia de la serie manual ya no dice nada del benchmark publicado."""
    precios = _precios(AAA="2026-09-22", BBB="2026-09-22", CCC="2026-09-22", IPSA_TR="2026-09-28")
    with pytest.raises(SystemExit, match="canasta del benchmark no está vigente.*2026-09-22.*rezago_hábil=4"):
        exigir_canasta_fresca(precios, CHILENAS, HOY)


def test_el_umbral_es_el_mismo_de_antes():
    """Tres días hábiles pasan y cuatro no: la regla no cambió, cambió a quién se le aplica."""
    assert MAX_BENCHMARK_LAG_BUSINESS_DAYS == 3
    justo = _precios(AAA="2026-09-23", BBB="2026-09-23", CCC="2026-09-23")
    assert frescura_de_la_canasta(justo, CHILENAS, HOY)[1] == 3
    exigir_canasta_fresca(justo, CHILENAS, HOY)
    pasado = _precios(AAA="2026-09-22", BBB="2026-09-22", CCC="2026-09-22")
    with pytest.raises(SystemExit):
        exigir_canasta_fresca(pasado, CHILENAS, HOY)


def test_un_papel_al_dia_no_declara_fresca_a_la_canasta():
    """Con el máximo bastaría uno. La fecha es la que alcanza al menos la mitad."""
    precios = _precios(AAA="2026-09-28", BBB="2026-09-18", CCC="2026-09-18")
    fecha, rezago = frescura_de_la_canasta(precios, CHILENAS, HOY)
    assert fecha == pd.Timestamp("2026-09-18") and rezago == 6
    with pytest.raises(SystemExit):
        exigir_canasta_fresca(precios, CHILENAS, HOY)


def test_un_rezagado_no_detiene_a_la_mayoria():
    precios = _precios(AAA="2026-09-28", BBB="2026-09-28", CCC="2026-09-10")
    assert frescura_de_la_canasta(precios, CHILENAS, HOY) == (pd.Timestamp("2026-09-28"), 0)


def test_solo_cuentan_los_integrantes_de_la_canasta():
    """Nueva York y el dólar operan en feriados chilenos, y lo deslistado no cotiza."""
    universo = _universo(("AAA", "accion_local", "activo"), ("BBB", "accion_local", "activo"),
                         ("VIEJA", "accion_local", "deslistado"), ("LTM-ADR", "adr", "activo"),
                         ("AAPL", "accion_us", "activo"), ("USDCLP", "divisa", "activo"))
    precios = _precios(**{"AAA": "2026-09-18", "BBB": "2026-09-18", "VIEJA": "2026-09-28",
                          "LTM-ADR": "2026-09-28", "AAPL": "2026-09-28", "USDCLP": "2026-09-28"})
    assert frescura_de_la_canasta(precios, universo, HOY) == (pd.Timestamp("2026-09-18"), 6)


def test_el_fin_de_semana_no_cuenta_como_atraso():
    precios = _precios(AAA="2026-09-25", BBB="2026-09-25", CCC="2026-09-25")
    assert frescura_de_la_canasta(precios, CHILENAS, pd.Timestamp("2026-09-27"))[1] == 0
    assert frescura_de_la_canasta(precios, CHILENAS, HOY)[1] == 1


def test_sin_precios_chilenos_no_hay_corrida():
    """Que falte el dato no puede leerse como que está al día."""
    with pytest.raises(SystemExit, match="sin datos"):
        exigir_canasta_fresca(_precios(IPSA_TR="2026-09-28"), CHILENAS, HOY)
    with pytest.raises(SystemExit, match="sin datos"):
        exigir_canasta_fresca(_precios(AAA="2026-09-28"), CHILENAS, HOY)
