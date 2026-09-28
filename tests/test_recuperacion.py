"""La recuperación automática de una corrida oficial que no salió.

Lo que duele, en orden: **que mande dos informes** por la misma semana, y que
no recupere cuando sí había una corrida pendiente.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from src import recuperacion as rec

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "update-prices.yml"


def _utc(texto):
    return datetime.fromisoformat(texto).replace(tzinfo=timezone.utc)


# El caso real: el último informe es del martes 22-09-2026, la corrida del
# viernes 25 falló, y la captura del lunes 28 termina pasadas las 23:00 UTC.
INFORME_VIEJO = _utc("2026-09-22T20:45:00")
LUNES_NOCHE = _utc("2026-09-28T23:10:00")


def test_la_ultima_corrida_programada_es_el_viernes_que_ya_paso():
    assert rec.ultima_corrida_programada(LUNES_NOCHE) == _utc("2026-09-25T20:30:00")
    # El viernes antes de la hora todavía manda el viernes anterior...
    assert rec.ultima_corrida_programada(_utc("2026-09-25T20:29:00")) == _utc("2026-09-18T20:30:00")
    # ...y desde la hora en punto, el mismo día.
    assert rec.ultima_corrida_programada(_utc("2026-09-25T20:30:00")) == _utc("2026-09-25T20:30:00")


def test_la_hora_programada_calza_con_el_cron_del_workflow():
    """El valor vive en el workflow y acá se repite: si se separan, recupera mal."""
    cron = re.search(r'schedule:\s*\n\s*- cron: "(\d+) (\d+) \* \* (\d)"', WORKFLOW.read_text(encoding="utf-8"))
    minuto, hora, dia = (int(x) for x in cron.groups())
    assert (hora, minuto) == (rec.HORA_DE_CORRIDA.hour, rec.HORA_DE_CORRIDA.minute)
    # cron cuenta desde el domingo y Python desde el lunes.
    assert (dia - 1) % 7 == rec.DIA_DE_CORRIDA


def test_el_viernes_que_fallo_se_recupera_tras_la_captura_del_lunes():
    correr, motivo = rec.decidir("workflow_run", "success", INFORME_VIEJO, LUNES_NOCHE)
    assert correr
    assert "25-09-2026" in motivo and "22-09-2026" in motivo


def test_un_informe_que_ya_salio_no_se_repite():
    """La captura corre todos los días; el informe sale una vez por semana."""
    viernes = _utc("2026-09-25T20:41:00")
    for captura in ("2026-09-25T23:10:00", "2026-09-28T23:10:00", "2026-10-01T23:10:00"):
        correr, _ = rec.decidir("workflow_run", "success", viernes, _utc(captura))
        assert not correr


def test_una_recuperacion_exitosa_cierra_el_pendiente():
    recuperado = _utc("2026-09-28T23:25:00")
    assert not rec.decidir("workflow_run", "success", recuperado, _utc("2026-09-29T23:10:00"))[0]
    # Hasta que el viernes siguiente vuelva a deber uno.
    assert rec.decidir("workflow_run", "success", recuperado, _utc("2026-10-02T23:10:00"))[0]


def test_sin_captura_buena_no_se_recupera():
    """Recuperar con los mismos datos viejos es repetir la falla, no arreglarla."""
    for captura in ("failure", "cancelled", "skipped", ""):
        correr, motivo = rec.decidir("workflow_run", captura, INFORME_VIEJO, LUNES_NOCHE)
        assert not correr and "captura" in motivo


def test_la_corrida_programada_y_la_manual_no_preguntan():
    """La regla de siempre no cambia: el viernes se calcula, haya o no informe reciente."""
    reciente = _utc("2026-09-28T23:25:00")
    for evento in ("schedule", "workflow_dispatch"):
        assert rec.decidir(evento, "", reciente, _utc("2026-10-02T20:31:00"))[0]
        assert rec.decidir(evento, "", None, LUNES_NOCHE)[0]


def test_sin_informe_nunca_tambien_es_pendiente():
    assert rec.hay_corrida_pendiente(None, LUNES_NOCHE)
    assert rec.decidir("workflow_run", "success", None, LUNES_NOCHE)[0]


def test_el_workflow_calcula_solo_si_la_decision_lo_dice():
    """Si el job de cálculo no dependiera de la decisión, cada captura mandaría un informe."""
    texto = WORKFLOW.read_text(encoding="utf-8")
    assert 'workflows: ["Captura diaria del cierre chileno"]' in texto
    assert "python -m src.recuperacion" in texto
    calculo = texto[texto.index("calculate-and-report:"):]
    assert "needs: decidir" in calculo
    assert "if: needs.decidir.outputs.correr == 'true'" in calculo
