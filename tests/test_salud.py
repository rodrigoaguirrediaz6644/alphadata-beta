"""El panel de salud: una línea cuando todo está bien.

El criterio de qué entra es que su falla pueda ensuciar un número publicado sin
avisar. Y la regla que ya aprendimos: una alarma que siempre está roja por una
razón conocida deja de ser una alarma.
"""

import pandas as pd

from src import salud
from src.salud import CONOCIDOS, html, markdown, revisar

SANO = dict(
    as_of=pd.Timestamp("2026-09-17"), precios_al_dia=True, series_detenidas=set(),
    cobertura_incompleta=set(), series_recalculadas={"Sigma-6", "Delta-12"},
    series_publicadas={"Sigma-6", "Delta-12"}, carteras_reproducidas=True,
    dias_sin_recomendaciones=57, umbral_vigencia=90, dividendos_sin_respaldo=set(),
    suite_verde=True)


def test_cuando_todo_esta_bien_es_una_sola_linea():
    chequeos, conocidos = revisar(**SANO)
    assert all(c.sano for c in chequeos) and conocidos == []
    texto = html(chequeos, conocidos)
    assert "Los datos están sanos y los cálculos cuadran" in texto
    assert "<li>" not in texto          # nada de listas cuando no hay nada que decir
    assert "asuntos conocidos" not in texto


def test_cuando_algo_falla_dice_que_y_no_lo_demas():
    chequeos, _ = revisar(**{**SANO, "carteras_reproducidas": False,
                             "series_recalculadas": {"Sigma-6"}})
    texto = html(chequeos)
    assert "2 verificaciones que no pasaron" in texto
    assert "no reproducen lo que publican las reglas" in texto
    assert "sin recalcular: Delta-12" in texto
    # Lo que sí pasó no aparece: un panel con filas verdes no se lee.
    assert "la suite pasó" not in texto


def test_hoy_no_hay_ninguna_alarma_apartada():
    """La meta era que `CONOCIDOS` quedara vacío, y quedó.

    Cada uno se cerró en su lugar en vez de quedar suprimido para siempre:
    AESANDES pasó a `deslistado`, MULTIFOODS a `ACUMULANDO` y el dividendo de
    MALLPLAZA quedó aceptado con la base que tiene. **Una alarma suprimida es
    una alarma que dejó de significar algo**, así que ninguna es el estado
    correcto. Ver PENDIENTES.md.

    El mecanismo se conserva, y las dos pruebas de abajo lo verifican, porque
    va a volver a hacer falta.
    """
    assert CONOCIDOS == {}


def test_lo_conocido_se_aparta_y_no_se_esconde(monkeypatch):
    """Lo anotado no puede aparecer en rojo todas las semanas.

    Si saliera cada corrida, el panel dejaría de leerse, que es peor que no
    tenerlo. Se inyecta el diccionario en vez de usar el real: la prueba es del
    mecanismo, y atarla al contenido la rompía cada vez que algo se cerraba.
    """
    monkeypatch.setattr(salud, "CONOCIDOS",
                        {"AESANDES": "congelado", "MULTIFOODS": "una rueda",
                         "MALLPLAZA 2026-09-03": "dividendo sin respaldo"})
    chequeos, conocidos = revisar(**{**SANO,
                                     "cobertura_incompleta": {"AESANDES", "MULTIFOODS"},
                                     "dividendos_sin_respaldo": {"MALLPLAZA 2026-09-03"}})
    assert all(c.sano for c in chequeos)
    assert conocidos == ["AESANDES", "MALLPLAZA 2026-09-03", "MULTIFOODS"]
    texto = html(chequeos, conocidos)
    assert "3 asuntos conocidos apartados" in texto or "3 asuntos conocidos" in texto
    assert "AESANDES" in texto          # apartado, no escondido
    assert "AESANDES" in markdown(chequeos, conocidos)


def test_uno_nuevo_si_enciende_el_panel(monkeypatch):
    monkeypatch.setattr(salud, "CONOCIDOS", {"AESANDES": "congelado"})
    chequeos, conocidos = revisar(**{**SANO, "cobertura_incompleta": {"AESANDES", "CHILE"}})
    assert conocidos == ["AESANDES"]
    cobertura = [c for c in chequeos if c.nombre == "Cobertura"][0]
    assert not cobertura.sano and "CHILE" in cobertura.detalle and "AESANDES" not in cobertura.detalle


def test_la_vigencia_cuenta_los_dias_que_quedan():
    chequeos, _ = revisar(**{**SANO, "dias_sin_recomendaciones": 91})
    reco = [c for c in chequeos if c.nombre == "Recomendaciones"][0]
    assert not reco.sano and "no abre" in reco.detalle
    chequeos, _ = revisar(**SANO)
    reco = [c for c in chequeos if c.nombre == "Recomendaciones"][0]
    assert reco.sano and "quedan 33" in reco.detalle


def test_todo_lo_conocido_esta_anotado_en_pendientes():
    """Apartar algo exige que su razón esté escrita, o se vuelve una forma de esconder."""
    from pathlib import Path
    texto = (Path(__file__).resolve().parents[1] / "PENDIENTES.md").read_text(encoding="utf-8")
    for clave in CONOCIDOS:
        assert clave.split()[0] in texto, f"{clave} se aparta del panel y no está en PENDIENTES.md"


# --------------------------------------------------------------------------
# El registro AFP: que se note si deja de crecer
# --------------------------------------------------------------------------

def test_el_registro_se_muestra_aunque_este_sano():
    """Acá el número es la información, no el semáforo.

    Casi todo lo sano se calla porque un panel de veinte filas verdes no se
    lee. Esta es la excepción: si el registro no aparece, nadie va a abrir el
    CSV para contarle las filas.
    """
    chequeos, conocidos = revisar(**SANO, registro_afp=(5993, "2026-09-17"))
    assert all(c.sano for c in chequeos)
    for texto in (html(chequeos, conocidos), markdown(chequeos, conocidos)):
        assert "5.993" in texto and "17-09-2026" in texto


def test_si_el_registro_dejo_de_crecer_enciende_el_panel():
    """El cron se apaga en silencio; esto es lo que lo vuelve ruidoso."""
    viejo = dict(SANO, as_of=pd.Timestamp("2026-10-15"))
    chequeos, _ = revisar(**viejo, registro_afp=(5993, "2026-09-17"))
    malos = [c for c in chequeos if not c.sano]
    assert [c.nombre for c in malos] == ["Registro AFP"]
    assert "dejó de crecer" in malos[0].detalle


def test_el_umbral_del_registro_no_suena_por_fiestas_patrias():
    """El hueco más largo medido desde 2021 son seis días: 17 al 23-09-2024.

    Con el umbral natural de tres días la alarma estaría roja cada septiembre,
    y una alarma que suena por el calendario deja de ser una alarma.
    """
    assert salud.DIAS_REGISTRO >= 6
    chequeos, _ = revisar(**dict(SANO, as_of=pd.Timestamp("2024-09-23")),
                          registro_afp=(5000, "2024-09-17"))
    assert all(c.sano for c in chequeos)


def test_sin_registro_lo_dice_en_vez_de_callarse():
    chequeos, conocidos = revisar(**SANO, registro_afp=None)
    assert all(c.sano for c in chequeos)
    assert "todavía no hay registro" in markdown(chequeos, conocidos)
