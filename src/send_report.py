from __future__ import annotations

from email.message import EmailMessage
import os
import smtplib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAFICOS = ("seguimiento_vivo.png", "reconstruccion.png")


def main() -> None:
    required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REPORT_RECIPIENTS"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Correo omitido; faltan secretos: " + ", ".join(missing))
        return
    html = (ROOT / "reports" / "latest_report.html").read_text(encoding="utf-8")
    # En el archivo los gráficos apuntan al PNG para que se vea fuera del
    # correo; acá se reescriben a `cid:`, que es la forma que entiende el
    # cliente de correo al recibirlos adjuntos.
    for nombre in GRAFICOS:
        html = html.replace(f'src="{nombre}"', f'src="cid:{Path(nombre).stem}"')
    md = (ROOT / "reports" / "latest_report.md").read_text(encoding="utf-8")
    msg = EmailMessage()
    msg["Subject"] = os.getenv("REPORT_SUBJECT", "AlphaData — informe Sigma-6 y Delta-12")
    msg["From"] = os.getenv("SMTP_FROM", os.environ["SMTP_USER"])
    msg["To"] = os.environ["REPORT_RECIPIENTS"]
    msg.set_content(md)
    msg.add_alternative(html, subtype="html")
    html_part = msg.get_payload()[-1]
    # El informe lleva dos gráficos separados: el seguimiento en vivo y la
    # reconstrucción. Son series distintas y van como imágenes distintas.
    for nombre in GRAFICOS:
        grafico = ROOT / "reports" / nombre
        if grafico.exists():
            html_part.add_related(grafico.read_bytes(), maintype="image", subtype="png",
                                  cid=f"<{Path(nombre).stem}>", filename=nombre)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print("Informe enviado a " + os.environ["REPORT_RECIPIENTS"])


if __name__ == "__main__":
    main()
