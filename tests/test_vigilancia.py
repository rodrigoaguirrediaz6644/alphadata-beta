"""El aviso de que no llego nada.

Es el unico modo de falla que importa para quien deja de mirar: hasta ahora
**un informe que no sale se veia igual que una semana tranquila**, porque el
panel de salud vive dentro del informe y una corrida que nunca ocurre no
produce ni informe ni alarma.
"""

import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from src import vigilancia
from src.vigilancia import (DIAS_PARA_LATIR, DIAS_SIN_INFORME, escribir_marca,
                            fecha_del_ultimo_commit, hay_que_avisar, mensaje,
                            necesita_latido)

AHORA = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def test_un_informe_al_dia_no_avisa_nada():
    assert not hay_que_avisar(1.)
    assert not hay_que_avisar(float(DIAS_SIN_INFORME))


def test_una_corrida_que_no_ocurrio_avisa():
    """La corrida es semanal: mas de diez dias es al menos una que falto."""
    assert hay_que_avisar(DIAS_SIN_INFORME + .5)
    assert hay_que_avisar(30.)


def test_sin_informe_ninguno_tambien_avisa_en_vez_de_callarse():
    """`None` no puede leerse como «no hay nada que avisar».

    Seria exactamente el mismo silencio ambiguo que esto viene a cerrar: un
    repositorio sin informe es el caso mas grave, no el mas tranquilo.
    """
    assert hay_que_avisar(None)
    asunto, cuerpo = mensaje(None)
    assert "no ha salido el informe" in asunto
    assert "No hay ningun informe" in cuerpo.replace("ú", "u").replace("í", "i")


def test_el_aviso_dice_donde_mirar_y_nombra_la_falla_mas_probable():
    """Un aviso que solo dice «algo pasa» obliga a investigar desde cero."""
    _, cuerpo = mensaje(21.)
    assert "21 dias" in cuerpo.replace("í", "i")
    assert "Actions" in cuerpo and "60 d" in cuerpo


def test_el_latido_existe_porque_el_exito_apaga_los_cron():
    """GitHub desactiva los flujos programados tras 60 dias sin **commits**.

    Las corridas programadas no cuentan como actividad, asi que cuanto mejor
    funcione el sistema solo, mas cerca esta de apagarse. El margen es 45 y no
    59 a proposito: deja dos semanas de fallas del propio flujo de vigilancia.
    """
    assert DIAS_PARA_LATIR < 60 - 14
    assert not necesita_latido(1.)
    assert not necesita_latido(float(DIAS_PARA_LATIR))
    assert necesita_latido(DIAS_PARA_LATIR + .5)
    assert necesita_latido(None)


def test_la_marca_se_escribe_con_su_razon_adentro(monkeypatch, tmp_path):
    """Quien la encuentre en un diff tiene que entender por que existe."""
    monkeypatch.setattr(vigilancia, "MARCA", tmp_path / ".github" / "ultimo_latido")
    ruta = escribir_marca(AHORA)
    texto = ruta.read_text(encoding="utf-8")
    assert texto.startswith("2026-09-22")
    assert "60 dias" in texto and "commits" in texto


def test_la_antiguedad_se_lee_del_historial_y_no_del_disco(tmp_path):
    """Al clonar, todo queda con la fecha del clon y el aviso no sonaria nunca.

    Es una trampa que se ve sana: el archivo existe, tiene fecha de hoy, y la
    fecha es la del `git clone`.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    correr = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, check=True)
    correr("init", "-q")
    correr("config", "user.email", "t@t")
    correr("config", "user.name", "t")
    (repo / "informe.md").write_text("hola", encoding="utf-8")
    correr("add", "-A")
    antiguo = "2026-01-05T12:00:00+00:00"
    subprocess.run(["git", "commit", "-q", "-m", "x", "--date", antiguo],
                   cwd=repo, capture_output=True, check=True,
                   env={**__import__("os").environ, "GIT_COMMITTER_DATE": antiguo})

    fecha = fecha_del_ultimo_commit("informe.md", repo=repo)
    assert fecha is not None
    assert fecha.date().isoformat() == "2026-01-05"
    dias = (AHORA - fecha).total_seconds() / 86400
    assert dias == pytest.approx(260, abs=1)
    assert hay_que_avisar(dias), "un informe de enero no puede pasar por al dia"


def test_un_archivo_que_no_existe_no_finge_estar_al_dia(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, capture_output=True, check=True)
    assert fecha_del_ultimo_commit("no_existe.md", repo=repo) is None
    assert hay_que_avisar(None)


def test_el_ensayo_del_aviso_se_distingue_de_uno_de_verdad():
    """Un aviso que nunca se disparo no esta probado.

    Es el mismo argumento que obligo a preguntar si la corrida semanal se habia
    disparado sola alguna vez: un mecanismo que nadie vio funcionar es una
    promesa. Pero el ensayo no puede parecerse a la cosa real, o la primera
    alarma de verdad se lee como otra prueba.
    """
    asunto, cuerpo = mensaje(1., simulado=True)
    assert "ENSAYO" in asunto and "no ha salido" not in asunto
    assert "no hay" in cuerpo and "problema" in cuerpo
    real, _ = mensaje(30.)
    assert "ENSAYO" not in real and "no ha salido el informe" in real


def test_horizonte_viejo_enciende_el_panel_pero_no_detiene_el_informe():
    """Una pieza secundaria no puede callar a la principal.

    El insumo de Horizonte viene de FRED, que **no responde desde los runners
    de GitHub** aunque responda en local. Cuando fallaba se llevaba por delante
    el informe completo y el correo: la cartera, el panel de salud y la guia de
    ingreso no salian por un problema de otra cosa.

    Ahora el paso sigue en rojo pero no detiene el resto, y esto es lo que
    impide que salir igual se vuelva salir en silencio con una seccion
    congelada.
    """
    from src.salud import DIAS_HORIZONTE, revisar

    def revisa(dias):
        return [c for c in revisar(
            as_of=AHORA, precios_al_dia=True, series_detenidas=set(),
            cobertura_incompleta=set(), series_recalculadas={"A"}, series_publicadas={"A"},
            carteras_reproducidas=True, dias_sin_recomendaciones=10, umbral_vigencia=90,
            dividendos_sin_respaldo=set(), suite_verde=True, dias_horizonte=dias)[0]
            if c.nombre == "Horizonte"][0]

    assert revisa(2.).sano
    assert revisa(float(DIAS_HORIZONTE)).sano
    viejo = revisa(DIAS_HORIZONTE + 1.)
    assert not viejo.sano and "congelada" in viejo.detalle
    assert revisa(None).sano      # sin estado todavia no es una falla
