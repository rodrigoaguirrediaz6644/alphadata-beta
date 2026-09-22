"""El aviso de que no llegó nada, que es el único modo de falla que importa.

Hasta ahora **un informe que no sale se veía igual que una semana tranquila.**
El panel de salud vive dentro del informe, así que una corrida que nunca ocurre
no produce ni informe ni alarma: el silencio es ambiguo. Para quien está encima
todos los días no importa; para quien se va a ocupar de otra cosa, es lo único
que importa.

Esto es la señal **afuera** del informe: llega cuando no llegó nada.

## Los dos modos de falla, que no son el mismo

**Uno: la corrida se rompe o deja de ocurrir.** Lo cubre el aviso por antigüedad
del informe, que corre a diario y manda un correo si `reports/latest_report.md`
lleva más de `DIAS_SIN_INFORME` días sin actualizarse.

**Dos: GitHub apaga los cron.** «En un repositorio público, los flujos
programados se desactivan automáticamente cuando no ha habido actividad en el
repositorio durante 60 días» —documentación de GitHub Actions—. Y lo que
reinicia ese reloj son **commits**, no corridas programadas. O sea: cuanto mejor
funcione el sistema solo, más cerca está de apagarse. Es la falla más probable
justo en el escenario de dejar de mirar, y se apaga en silencio: sin error, sin
informe.

Lo cubre `necesita_latido`, que escribe un commit de marca cuando el
repositorio lleva `DIAS_PARA_LATIR` días quieto. Son 45 y no 59 a propósito: si
el flujo de vigilancia falla dos semanas seguidas, todavía queda margen.

**El orden entre los dos importa.** El aviso por antigüedad es él mismo un flujo
programado, así que si GitHub apaga los cron el aviso también se calla. Por eso
el latido no es un adorno: es lo que mantiene vivo al que avisa.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFORME = ROOT / "reports" / "latest_report.md"
MARCA = ROOT / ".github" / "ultimo_latido"

# La corrida oficial es semanal, los viernes. Diez días deja pasar una semana
# entera más el fin de semana siguiente sin avisar por un atraso de un día, y
# no llega a dejar pasar dos corridas sin decir nada.
DIAS_SIN_INFORME = 10
# El reloj de GitHub es de 60 días. Con 45 caben dos semanas de fallas del
# propio flujo de vigilancia antes de que el margen se acabe.
DIAS_PARA_LATIR = 45


def _dias_desde(fecha: datetime | None, ahora: datetime | None = None) -> float | None:
    if fecha is None:
        return None
    ahora = ahora or datetime.now(timezone.utc)
    return (ahora - fecha).total_seconds() / 86400


def fecha_del_ultimo_commit(ruta: Path | None = None, repo: Path | None = None) -> datetime | None:
    """Cuándo se tocó por última vez un archivo, según el historial.

    Se lee del historial y no de la fecha del archivo en disco: al clonar, todo
    queda con la fecha del clon y el aviso no sonaría nunca.
    """
    orden = ["git", "log", "-1", "--format=%cI"]
    if ruta is not None:
        orden += ["--", str(ruta)]
    try:
        salida = subprocess.run(orden, cwd=repo or ROOT, capture_output=True,
                                text=True, timeout=60).stdout.strip()
    except Exception:                                           # pragma: no cover - entorno
        return None
    if not salida:
        return None
    try:
        return datetime.fromisoformat(salida)
    except ValueError:                                          # pragma: no cover - formato
        return None


def antiguedad_del_informe(ahora: datetime | None = None, repo: Path | None = None) -> float | None:
    return _dias_desde(fecha_del_ultimo_commit(INFORME.relative_to(ROOT), repo), ahora)


def hay_que_avisar(dias: float | None, umbral: int = DIAS_SIN_INFORME) -> bool:
    """Sin informe **nunca** también es motivo de aviso, no de silencio.

    `None` es el caso de un repositorio recién clonado o de un informe que no
    existe; tratarlo como «no hay nada que avisar» sería exactamente el mismo
    silencio ambiguo que esto viene a cerrar.
    """
    return dias is None or dias > umbral


def mensaje(dias: float | None) -> tuple[str, str]:
    """Asunto y cuerpo del aviso, en el mismo lenguaje que el informe."""
    if dias is None:
        cuerpo = ("No hay ningún informe publicado en el repositorio, o no se pudo leer su "
                  "fecha.\n")
    else:
        cuerpo = (f"El último informe publicado tiene {dias:.0f} días. La corrida oficial es "
                  f"semanal, así que más de {DIAS_SIN_INFORME} días significa que **al menos una "
                  "corrida no ocurrió**.\n")
    cuerpo += (
        "\nEsto no es una alarma del informe: es la señal de que el informe no llegó. "
        "El panel de salud vive dentro del informe, así que una corrida que nunca ocurre "
        "no produce ni informe ni alarma.\n"
        "\nQué mirar, en orden:\n"
        "\n1. Si el flujo «Ejecutar AlphaData» aparece desactivado en la pestaña Actions. "
        "GitHub apaga los flujos programados de un repositorio público tras 60 días sin "
        "actividad, y se vuelve a encender con un botón.\n"
        "2. Si la última corrida falló, y en qué paso.\n"
        "3. Si el feed de precios está detenido: eso lo diría el informe, pero sólo si el "
        "informe sale.\n")
    return "AlphaData — no ha salido el informe", cuerpo


def necesita_latido(dias: float | None, umbral: int = DIAS_PARA_LATIR) -> bool:
    """¿Hay que escribir un commit de marca para que GitHub no apague los cron?

    Sin commits en 60 días GitHub desactiva los flujos programados de un
    repositorio público, y **las corridas programadas no cuentan como
    actividad**: sólo los commits. O sea que el sistema se apaga justo cuando
    empieza a funcionar solo sin que nadie lo toque.
    """
    return dias is None or dias > umbral


def escribir_marca(ahora: datetime | None = None) -> Path:
    ahora = ahora or datetime.now(timezone.utc)
    MARCA.parent.mkdir(parents=True, exist_ok=True)
    MARCA.write_text(
        f"{ahora.date().isoformat()}\n"
        "\n"
        "Marca de actividad. Existe por una sola razon: GitHub desactiva los\n"
        "flujos programados de un repositorio publico cuando no hay actividad en\n"
        "60 dias, y lo que cuenta como actividad son commits, no corridas.\n"
        "Sin esto, cuanto mejor funcione el sistema solo, mas cerca esta de\n"
        "apagarse en silencio. Ver src/vigilancia.py.\n",
        encoding="utf-8", newline="\n")
    return MARCA


def main() -> None:                                             # pragma: no cover - entrada
    import os

    dias = antiguedad_del_informe()
    edad = "desconocida" if dias is None else f"{dias:.1f} días"
    print(f"Antigüedad del último informe: {edad}.")

    if necesita_latido(dias if dias is None else _dias_desde(fecha_del_ultimo_commit())):
        escribir_marca()
        print("Marca de actividad escrita: el repositorio llevaba demasiado tiempo quieto.")

    if not hay_que_avisar(dias):
        print("El informe está al día; no se avisa nada.")
        return
    asunto, cuerpo = mensaje(dias)
    faltan = [n for n in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REPORT_RECIPIENTS")
              if not os.getenv(n)]
    if faltan:
        # Sin correo no se puede avisar, pero el flujo **tiene que fallar** para
        # que quede rojo en Actions. Salir en silencio sería reproducir el
        # problema que esto viene a cerrar.
        raise SystemExit(f"{asunto}: {cuerpo}\nNo se pudo avisar; faltan secretos: "
                         + ", ".join(faltan))
    from email.message import EmailMessage
    import smtplib

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = os.getenv("SMTP_FROM", os.environ["SMTP_USER"])
    msg["To"] = os.environ["REPORT_RECIPIENTS"]
    msg.set_content(cuerpo)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print("Aviso enviado a " + os.environ["REPORT_RECIPIENTS"])
    # Y además se deja rojo en Actions: el correo se puede perder.
    raise SystemExit(asunto)


if __name__ == "__main__":                                      # pragma: no cover
    main()
