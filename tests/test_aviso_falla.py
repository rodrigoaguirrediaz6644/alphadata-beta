"""El aviso de que una corrida falló.

Lo que se prueba: que el correo diga qué falló y dónde mirar, que ningún flujo
de producción quede sin el aviso, y que un informe sin enviar no quede en verde.
"""

import re
from pathlib import Path

import pytest

from src import aviso_falla as av
from src import send_report

FLUJOS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
# Vigilancia queda fuera a propósito: cuando sale en rojo es porque ya avisó.
DE_PRODUCCION = ("capture-daily.yml", "update-prices.yml", "ahorro-generacional.yml")
ENLACE = "https://github.com/x/y/actions/runs/1"

# La forma en que la API de GitHub entrega una corrida a medio terminar: el
# paso del aviso todavía no tiene conclusión.
TRABAJOS = [{"name": "capturar", "steps": [
    {"name": "Instalar dependencias", "conclusion": "success"},
    {"name": "Validar código", "conclusion": "failure"},
    {"name": "Capturar el cierre del día", "conclusion": "skipped"},
    {"name": "Avisar por correo que la corrida falló", "conclusion": None},
]}]


def test_nombra_el_paso_que_fallo_y_solo_ese():
    assert av.pasos_fallidos(TRABAJOS) == ["capturar › Validar código"]
    assert av.pasos_fallidos([]) == []
    assert av.pasos_fallidos([{"name": "sin pasos"}]) == []


def test_el_correo_dice_que_fallo_donde_y_que_se_pierde():
    asunto, cuerpo = av.mensaje("Captura diaria del cierre chileno", av.pasos_fallidos(TRABAJOS), ENLACE, "schedule")
    assert asunto == "AlphaData — falló «Captura diaria del cierre chileno»"
    for dato in ("programada", "capturar › Validar código", "no se puede bajar después", ENLACE):
        assert dato in cuerpo


def test_sin_detalle_avisa_igual():
    """Leer el detalle puede fallar; el aviso no puede depender de eso."""
    asunto, cuerpo = av.mensaje("Un flujo nuevo", [], ENLACE)
    assert "Un flujo nuevo" in asunto
    assert "No se pudo leer qué paso falló" in cuerpo and ENLACE in cuerpo


def test_la_recuperacion_se_distingue_de_la_corrida_del_viernes():
    _, cuerpo = av.mensaje("Ejecutar AlphaData", ["x › y"], ENLACE, "workflow_run")
    assert "de recuperación" in cuerpo and "Se reintenta solo" in cuerpo


@pytest.mark.parametrize("archivo", DE_PRODUCCION)
def test_cada_trabajo_de_produccion_termina_avisando(archivo):
    """Un trabajo sin este paso falla callado, que es lo que esto viene a cerrar."""
    # Se lee como texto y no con un analizador de YAML: sería una dependencia
    # nueva sólo para las pruebas.
    texto = (FLUJOS / archivo).read_text(encoding="utf-8")
    assert re.match(r"name: (.+)\n", texto).group(1) in av.CONSECUENCIA
    assert "permissions:\n  contents: write\n" in texto and "\n  actions: read\n" in texto
    trabajos = re.split(r"\n  [\w-]+:\n    (?:needs|runs-on):", texto.split("\njobs:", 1)[1])[1:]
    assert trabajos
    for trabajo in trabajos:
        ultimo = trabajo.split("\n      - name: ")[-1]
        assert ultimo.startswith("Avisar por correo que la corrida falló\n        if: failure()\n"), archivo
        assert ultimo.rstrip().endswith("run: PYTHONPATH=. python3 -m src.aviso_falla")
        for secreto in av.SECRETOS:
            assert f"{secreto}: ${{{{ secrets.{secreto} }}}}" in ultimo


def test_en_github_un_informe_sin_enviar_queda_en_rojo(monkeypatch, capsys):
    for secreto in av.SECRETOS:
        monkeypatch.delenv(secreto, raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(SystemExit, match="El informe no se envió"):
        send_report.main()
    # En local los secretos no están y eso no es una falla.
    monkeypatch.delenv("GITHUB_ACTIONS")
    send_report.main()
    assert "Correo omitido" in capsys.readouterr().out
