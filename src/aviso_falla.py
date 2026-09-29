"""El aviso de que una corrida falló, el mismo día en que falla.

La captura diaria falló el 24 y el 25-09-2026 y la corrida oficial el 25, y
**nadie se enteró hasta que alguien miró**. Vigilancia avisa cuando el informe
lleva diez días sin salir: cubre que el informe no llegue, no que algo se haya
roto ayer. Y un cierre chileno que no se captura no se recupera después.

Esto corre como último paso de cada flujo de producción, sólo cuando algún paso
anterior falló, y manda un correo que dice qué flujo, qué paso y dónde mirar.

## Lo que no puede cubrir

**Que el correo mismo esté roto.** Si el servidor no responde o faltan los
secretos, este aviso tampoco sale. Por eso termina en error en vez de callar:
la corrida ya está en rojo y GitHub manda su propia notificación de flujo
fallido, que no depende de este correo.

Usa sólo biblioteca estándar, para poder avisar también cuando lo que falló fue
instalar las dependencias.
"""

from __future__ import annotations

import json
import os
import urllib.request

SECRETOS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REPORT_RECIPIENTS")

# Qué se pierde con cada falla, en el lenguaje del informe. Lo que no está acá
# avisa igual, sin esta línea.
CONSECUENCIA = {
    "Captura diaria del cierre chileno":
        "El cierre chileno de hoy no quedó guardado. Ese dato no se puede bajar después: "
        "el proveedor sólo publica el último.",
    "Ejecutar AlphaData":
        "El informe semanal no salió. Se reintenta solo cuando termine bien la próxima "
        "captura diaria, y si vuelve a fallar llega otro aviso como éste.",
    "Ahorro Generacional":
        "El registro previsional de hoy falló. Si había que avisar un cambio de fondo, "
        "ese aviso puede no haber salido.",
}


# Lo que se pierde con la falla de un paso puntual, cuando no es lo mismo que lo
# de todo el flujo: el atraso del IPSA no impide que el cierre chileno se guarde.
CONSECUENCIA_PASO = {
    "Vigilar el IPSA":
        "La línea del Ipsa del informe está atrasada: MSCI no ha entregado ruedas nuevas. "
        "El cierre chileno de hoy sí quedó guardado y el resto del informe no depende de esto.",
}


def pasos_fallidos(trabajos: list[dict]) -> list[str]:
    """«trabajo › paso» de cada paso que falló, sin contar este aviso."""
    return [f"{t.get('name', '?')} › {p.get('name', '?')}"
            for t in trabajos for p in t.get("steps", [])
            if p.get("conclusion") == "failure"]


def mensaje(flujo: str, fallidos: list[str], enlace: str, evento: str = "") -> tuple[str, str]:
    origen = {"schedule": "programada", "workflow_dispatch": "lanzada a mano",
              "workflow_run": "de recuperación, tras la captura diaria"}.get(evento)
    cuerpo = f"Falló la corrida {origen + ' ' if origen else ''}de «{flujo}».\n"
    if fallidos:
        cuerpo += "\nDónde falló:\n" + "".join(f"  - {f}\n" for f in fallidos)
    else:
        cuerpo += "\nNo se pudo leer qué paso falló; está en el enlace.\n"
    nombres = [f.split(" › ")[-1] for f in fallidos]
    solo_de_paso = bool(nombres) and all(n in CONSECUENCIA_PASO for n in nombres)
    if solo_de_paso:
        cuerpo += "\n" + "\n".join(dict.fromkeys(CONSECUENCIA_PASO[n] for n in nombres)) + "\n"
    elif flujo in CONSECUENCIA:
        cuerpo += "\n" + CONSECUENCIA[flujo] + "\n"
    cuerpo += f"\nLa corrida, con su log:\n{enlace}\n"
    asunto = ("AlphaData — el IPSA del informe está atrasado" if solo_de_paso and nombres == ["Vigilar el IPSA"]
              else f"AlphaData — falló «{flujo}»")
    return asunto, cuerpo


def _trabajos(servidor_api: str, repo: str, corrida: str, token: str) -> list[dict]:   # pragma: no cover - red
    pedido = urllib.request.Request(
        f"{servidor_api}/repos/{repo}/actions/runs/{corrida}/jobs",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "alphadata",
                 **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as respuesta:
            return json.load(respuesta).get("jobs", [])
    except Exception as exc:
        # El detalle es un adorno; el aviso es lo que importa y sale igual.
        print(f"No se pudo leer el detalle de la corrida: {exc}")
        return []


def main() -> None:                                             # pragma: no cover - entrada
    from email.message import EmailMessage
    import smtplib

    repo, corrida = os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GITHUB_RUN_ID", "")
    flujo = os.getenv("GITHUB_WORKFLOW", "un flujo de AlphaData")
    enlace = f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{corrida}"
    trabajos = _trabajos(os.getenv("GITHUB_API_URL", "https://api.github.com"), repo, corrida,
                         os.getenv("GITHUB_TOKEN", ""))
    asunto, cuerpo = mensaje(flujo, pasos_fallidos(trabajos), enlace, os.getenv("GITHUB_EVENT_NAME", ""))
    print(cuerpo)
    faltan = [n for n in SECRETOS if not os.getenv(n)]
    if faltan:
        raise SystemExit("No se pudo avisar; faltan secretos: " + ", ".join(faltan))
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = os.getenv("SMTP_FROM", os.environ["SMTP_USER"])
    msg["To"] = os.environ["REPORT_RECIPIENTS"]
    msg.set_content(cuerpo)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print("Aviso de falla enviado.")


if __name__ == "__main__":                                      # pragma: no cover
    main()
