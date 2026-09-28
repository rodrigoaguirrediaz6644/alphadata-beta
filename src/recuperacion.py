"""Si una corrida oficial no salió, que salga sola apenas haya datos frescos.

La corrida oficial es semanal. Cuando la del viernes 25-09-2026 falló, lo único
que quedaba era esperar al viernes siguiente o que alguien la lanzara a mano, y
**un sistema que necesita que alguien lo empuje no opera solo**.

Esto decide, cada vez que termina la captura diaria, si hay una corrida
pendiente. La hay cuando el último informe publicado es anterior a la última
corrida programada: ese viernes debió salir uno y no salió.

## Lo que no hace

**No decide si los datos sirven.** Eso es de las guardias de `fetch_prices`, que
corren igual en una recuperación que en una corrida normal. Acá sólo se decide
si toca intentar.

**No repite un informe que ya salió.** El informe se commitea al final de la
corrida, así que una recuperación exitosa deja el informe más nuevo que la
corrida programada y la captura del día siguiente ya no encuentra nada
pendiente.
"""

from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone

from src.vigilancia import INFORME, ROOT, fecha_del_ultimo_commit

# Tiene que calzar con el cron de `.github/workflows/update-prices.yml`:
# "30 20 * * 5", viernes a las 20:30 UTC.
DIA_DE_CORRIDA = 4
HORA_DE_CORRIDA = time(20, 30, tzinfo=timezone.utc)


def ultima_corrida_programada(ahora: datetime) -> datetime:
    """El último viernes a las 20:30 UTC que ya pasó."""
    ahora = ahora.astimezone(timezone.utc)
    dia = ahora.date() - timedelta(days=(ahora.weekday() - DIA_DE_CORRIDA) % 7)
    corrida = datetime.combine(dia, HORA_DE_CORRIDA)
    return corrida if corrida <= ahora else corrida - timedelta(days=7)


def hay_corrida_pendiente(informe: datetime | None, ahora: datetime) -> bool:
    """Sin informe **nunca** también es pendiente, igual que en la vigilancia."""
    return informe is None or informe < ultima_corrida_programada(ahora)


def decidir(evento: str, captura: str, informe: datetime | None, ahora: datetime) -> tuple[bool, str]:
    """Si esta corrida debe calcular, y por qué, para que quede en el log."""
    if evento != "workflow_run":
        return True, "Corrida programada o lanzada a mano: se calcula."
    if captura != "success":
        return False, f"La captura diaria terminó en «{captura or 'desconocido'}»: no hay datos frescos con que recuperar."
    programada = ultima_corrida_programada(ahora)
    if not hay_corrida_pendiente(informe, ahora):
        return False, f"El informe del {informe:%d-%m-%Y} es posterior a la corrida del {programada:%d-%m-%Y}: no hay nada pendiente."
    ultimo = "no hay informe publicado" if informe is None else f"el último informe es del {informe:%d-%m-%Y}"
    return True, f"La corrida del {programada:%d-%m-%Y} no publicó informe ({ultimo}): se recupera."


def main() -> None:                                             # pragma: no cover - entrada
    correr, motivo = decidir(
        os.getenv("EVENTO", ""), os.getenv("CAPTURA", ""),
        fecha_del_ultimo_commit(INFORME.relative_to(ROOT)), datetime.now(timezone.utc))
    print(motivo)
    salida = os.getenv("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"correr={'true' if correr else 'false'}\n")


if __name__ == "__main__":                                      # pragma: no cover
    main()
