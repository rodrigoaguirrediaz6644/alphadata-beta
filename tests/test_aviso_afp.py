"""El aviso de cambio de fondo. Lo que se prueba es que no falle callado.

Un aviso que no llega es peor que no tener aviso, porque Rodrigo va a estar
confiando. Entonces las pruebas que importan no son las de que dispare: son
las de que cuando no dispara, se sepa.
"""

import datetime as dt

import pytest

from src import aviso_afp as av
from src import registro_afp as r


def _fila(fecha, posicion, votos, **extra):
    f = {c: "" for c in r.columnas()}
    f.update(fecha=fecha, posicion=posicion, votos=str(votos),
             vc_a="100.00", vc_e="50.00", vc_d="70.00")
    f.update(extra)
    return f


def _historia(*pares):
    """(posicion, votos) por dia, en dias habiles consecutivos."""
    d = dt.date(2026, 11, 2)                       # un lunes
    filas = []
    for pos, vot in pares:
        filas.append(_fila(d.isoformat(), pos, vot))
        d += dt.timedelta(days=1 if d.weekday() < 4 else 3)
    return filas


# --------------------------------------------------------------------------
# cuando dispara
# --------------------------------------------------------------------------

def test_dispara_en_la_transicion():
    filas = _historia(("A", 0), ("A", 1), ("E", 3))
    a = av.pendiente(filas)
    assert a and a["hacia"] == "E" and a["desde"] == "A" and a["cual"] == 1


def test_no_dispara_si_la_posicion_no_cambio():
    assert av.pendiente(_historia(("A", 0), ("A", 1), ("A", 1))) is None


def test_no_dispara_todos_los_dias_que_esta_en_refugio():
    """Sólo la transición. Si no, serían meses de correos diarios."""
    filas = _historia(("A", 0), ("E", 3), ("E", 3), ("E", 3), ("E", 4), ("E", 5))
    assert av.pendiente(filas) is None


def test_se_repite_tres_dias_y_despues_para():
    """Un correo se pierde; tres no."""
    base = [("A", 0), ("E", 3)]
    for extra, esperado in [([], 1), ([("E", 3)], 2), ([("E", 3)] * 2, 3)]:
        a = av.pendiente(_historia(*base, *extra))
        assert a and a["cual"] == esperado
    assert av.pendiente(_historia(*base, *[("E", 3)] * 3)) is None


def test_no_avisa_dos_veces_por_el_mismo_dia():
    filas = _historia(("A", 0), ("E", 3))
    filas[-1]["aviso_estado"] = "enviado"
    assert av.pendiente(filas) is None


def test_un_intento_fallido_no_bloquea_el_reintento_del_mismo_dia():
    """Si el correo falló, la fila queda marcada `fallo` y se puede reintentar."""
    filas = _historia(("A", 0), ("E", 3))
    filas[-1]["aviso_estado"] = "fallo"
    assert av.pendiente(filas) is not None


# --------------------------------------------------------------------------
# que dice
# --------------------------------------------------------------------------

def test_el_asunto_lleva_la_instruccion_completa():
    """Se lee desde la pantalla bloqueada del teléfono."""
    a = av.pendiente(_historia(("A", 0), ("E", 3)))
    s = av.asunto(a)
    assert s.startswith("AFP: cambiar a Fondo E")
    assert "solicitar hoy 03-11-2026" in s


def test_el_cuerpo_dice_cuantas_medias_y_cuando_se_materializa():
    a = av.pendiente(_historia(("A", 0), ("E", 3)))
    c = av.cuerpo(a)
    assert "3 de las 5 medias" in c
    assert f"sale con {r.VOTOS_PARA_SALIR} o mas" in c
    # 03-11-2026 es martes; cuatro habiles despues es el lunes 09.
    assert "09-11-2026" in c


def test_el_cuerpo_no_recomienda_nada():
    """Dice qué indica la regla. La decisión de operarla no es del aviso."""
    c = av.cuerpo(av.pendiente(_historia(("A", 0), ("E", 3)))).lower()
    for palabra in ("conviene", "recomend", "deberia", "urgente"):
        assert palabra not in c


def test_el_nombre_del_fondo_sale_del_registro_y_no_del_codigo():
    """En abril de 2027 los multifondos desaparecen.

    Si el nombre estuviera escrito acá, ese día el correo diría «cambiar a
    Fondo E» sobre un fondo que ya no existe.
    """
    filas = _historia(("A", 0), ("Consolidacion", 3))
    a = av.pendiente(filas)
    assert "Fondo Consolidacion" in av.asunto(a)


def test_los_dias_habiles_saltan_el_fin_de_semana():
    assert av.habiles_adelante("2026-11-05", 4) == dt.date(2026, 11, 11)


# --------------------------------------------------------------------------
# cuando falla
# --------------------------------------------------------------------------

def test_si_el_correo_falla_la_corrida_queda_en_rojo_y_la_fila_lo_dice():
    filas = _historia(("A", 0), ("E", 3))
    ok, dicho = av.avisar(filas, enviador=lambda a: (False, "SMTPAuthenticationError"))
    assert ok is False
    assert "AVISO NO ENVIADO" in dicho
    assert filas[-1]["aviso_estado"] == "fallo"
    assert filas[-1]["aviso"].startswith("a E")


def test_si_el_correo_sale_queda_anotado_en_la_misma_fila():
    filas = _historia(("A", 0), ("E", 3))
    ok, _ = av.avisar(filas, enviador=lambda a: (True, "alguien@ejemplo.cl"))
    assert ok and filas[-1]["aviso_estado"] == "enviado"


def test_sin_secretos_no_finge_que_salio(monkeypatch):
    for s in av.SECRETOS:
        monkeypatch.delenv(s, raising=False)
    ok, detalle = av.enviar(av.pendiente(_historia(("A", 0), ("E", 3))))
    assert ok is False and "faltan secretos" in detalle


def test_sin_transicion_no_toca_la_fila():
    filas = _historia(("A", 0), ("A", 0))
    ok, dicho = av.avisar(filas, enviador=lambda a: pytest.fail("no debio enviar"))
    assert ok and dicho == "sin transicion pendiente"
    assert filas[-1]["aviso"] == ""


# --------------------------------------------------------------------------
# el ensayo
# --------------------------------------------------------------------------

def test_el_ensayo_se_manda_cuando_no_hay_nada_que_avisar(monkeypatch):
    """El primer aviso real no puede ser la primera prueba del SMTP.

    Las pruebas unitarias cubren cuándo dispara y qué dice; lo que no pueden
    cubrir es si el correo sale desde el runner. Con FRED ya nos pasó que algo
    respondía en local y no en GitHub.
    """
    monkeypatch.setenv("SIMULAR_AVISO", "true")
    mandados = []
    ok, dicho = av.avisar(_historia(("A", 0), ("A", 0)),
                          enviador=lambda a: (mandados.append(a), (True, "ok"))[1])
    assert ok and dicho == "ensayo enviado"
    assert mandados and mandados[0]["ensayo"] is True


def test_el_ensayo_no_se_puede_confundir_con_una_instruccion_real():
    """Uno que se lea como aviso de verdad sería peor que no ensayar."""
    a = av.ensayo(_historia(("A", 0)))
    assert av.asunto(a).startswith("[ENSAYO]")
    assert av.cuerpo(a).startswith("ESTO ES UN ENSAYO")


def test_el_ensayo_no_marca_la_fila():
    """No pasó nada: el historial no debe decir que hubo un aviso."""
    import os
    os.environ["SIMULAR_AVISO"] = "1"
    try:
        filas = _historia(("A", 0), ("A", 0))
        av.avisar(filas, enviador=lambda a: (True, "ok"))
        assert filas[-1]["aviso"] == "" and filas[-1]["aviso_estado"] == ""
    finally:
        os.environ.pop("SIMULAR_AVISO", None)


def test_un_ensayo_que_no_sale_tambien_deja_rojo(monkeypatch):
    monkeypatch.setenv("SIMULAR_AVISO", "true")
    ok, dicho = av.avisar(_historia(("A", 0), ("A", 0)),
                          enviador=lambda a: (False, "sin red"))
    assert ok is False and "ENSAYO NO ENVIADO" in dicho
