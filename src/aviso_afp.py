"""El aviso de cambio de fondo, el mismo dia. Corre dentro del trabajo diario.

**Por que existe.** El informe semanal no sirve como instrumento: entre que la
senal habla un lunes y Rodrigo lo lee el viernes se pierden cuatro dias, y
sumados al rezago de ejecucion la proteccion medida se deteriora varios puntos.

**Que se opera: la votacion, no una media.** Operar exige una instruccion y no
cinco, y elegir una de las cinco medias seria justo la decision contaminada,
porque las elegimos mirando estos datos. La regla es la de
`registro_afp.posicion_por_voto`: al refugio cuando dos o mas de las cinco lo
indican, de vuelta al agresivo cuando menos de dos.

**Lo que decide si esto sirve no es que dispare: es que no falle callado.** Un
aviso que no llega es peor que no tener aviso, porque el va a estar confiando.
Por eso: si el correo falla la corrida sale en rojo y reintenta al dia
siguiente, el registro anota en la fila que hubo aviso y si salio, y el informe
del viernes muestra la posicion en vigor por si los tres correos se perdieron.

Y al reves: **la falta de aviso nunca puede tumbar el registro ni el informe.**
Es el defecto que ya nos costo un informe entero con FRED.

Solo biblioteca estandar, como el registro.
"""
from __future__ import annotations

import datetime as dt
import os
import smtplib
from email.message import EmailMessage

from src.registro_afp import (AFP, DENTRO, MEDIAS, REZAGO, VOTOS_PARA_SALIR,
                              transicion)

# Un correo se pierde; tres no. Y asi no hace falta que el sistema sepa en que
# fondo esta Rodrigo de verdad, que es una complicacion que no vale lo que
# cuesta.
DIAS_DE_AVISO = 3

SECRETOS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REPORT_RECIPIENTS")


def nombre_fondo(codigo: str) -> str:
    """«A» -> «Fondo A». El codigo sale del registro, nunca escrito aca.

    En abril de 2027 los multifondos desaparecen y quedan los generacionales.
    Si el nombre estuviera en el codigo del aviso, ese dia el correo diria
    «cambiar a Fondo E» sobre un fondo que ya no existe.
    """
    return f"Fondo {codigo}"


def habiles_adelante(fecha: str, n: int = REZAGO) -> dt.date:
    """La fecha en que quedaria materializado el cambio, contando dias habiles.

    Cuenta lunes a viernes y **no sabe de feriados chilenos**, asi que en una
    semana con feriado la fecha real cae un dia despues. Va dicho en el cuerpo
    del correo como aproximada en vez de fingir precision que no hay.
    """
    d = dt.date.fromisoformat(fecha)
    while n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def pendiente(filas: list[dict]) -> dict | None:
    """Si hoy corresponde avisar, con que decir. None si no.

    Dispara **solo en la transicion** y en los `DIAS_DE_AVISO` dias de
    cotizacion siguientes, no cada dia que la senal este en refugio. Y no dos
    veces por el mismo dia: si la fila de hoy ya quedo marcada como enviada, no
    se repite.
    """
    if not filas:
        return None
    t = transicion(filas)
    if t is None:
        return None
    idx, desde, hacia = t
    cual = len(filas) - 1 - idx
    if cual >= DIAS_DE_AVISO:
        return None
    hoy = filas[-1]
    if hoy.get("aviso_estado") == "enviado":
        return None
    return {"desde": desde, "hacia": hacia, "fecha": hoy["fecha"],
            "fecha_senal": filas[idx]["fecha"], "cual": cual + 1,
            "votos": hoy.get("votos") or filas[idx].get("votos") or "?",
            "cuota": hoy.get(f"vc_{hacia.lower()}", ""),
            "cuota_a": hoy.get(f"vc_{DENTRO.lower()}", "")}


def asunto(a: dict) -> str:
    """La instruccion completa en el asunto: se lee desde la pantalla bloqueada."""
    dia = dt.date.fromisoformat(a["fecha"]).strftime("%d-%m-%Y")
    return f"AFP: cambiar a {nombre_fondo(a['hacia'])}  —  solicitar hoy {dia}"


def cuerpo(a: dict) -> str:
    """Corto y sin adornos. No recomienda: dice que indica la regla y con que."""
    materializa = habiles_adelante(a["fecha"]).strftime("%d-%m-%Y")
    repeticion = ("" if a["cual"] == 1
                  else f"\n(Aviso {a['cual']} de {DIAS_DE_AVISO} por el mismo cambio.)")
    return (
        f"Cambiar a {nombre_fondo(a['hacia'])}, desde {nombre_fondo(a['desde'])}.\n"
        f"AFP {AFP.capitalize()}.\n\n"
        f"Lo indican {a['votos']} de las {len(MEDIAS)} medias de la grilla "
        f"(la regla sale con {VOTOS_PARA_SALIR} o mas).\n"
        f"La senal cambio el {dt.date.fromisoformat(a['fecha_senal']).strftime('%d-%m-%Y')}.\n\n"
        f"Valor cuota de hoy: {nombre_fondo(DENTRO)} {a['cuota_a']}, "
        f"{nombre_fondo(a['hacia'])} {a['cuota']}.\n"
        f"Solicitando hoy, el cambio quedaria materializado alrededor del "
        f"{materializa} ({REZAGO} dias habiles; un feriado lo corre un dia)."
        f"{repeticion}\n")


def enviar(a: dict) -> tuple[bool, str]:
    """Manda el correo. Devuelve si salio y por que no, si no salio."""
    faltan = [s for s in SECRETOS if not os.getenv(s)]
    if faltan:
        return False, "faltan secretos: " + ", ".join(faltan)
    msg = EmailMessage()
    msg["Subject"] = asunto(a)
    msg["From"] = os.getenv("SMTP_FROM", os.environ["SMTP_USER"])
    msg["To"] = os.environ["REPORT_RECIPIENTS"]
    msg.set_content(cuerpo(a))
    try:
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))) as smtp:
            smtp.starttls()
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(msg)
    except Exception as e:                       # noqa: BLE001 - cualquiera es fallo
        return False, f"{type(e).__name__}: {e}"
    return True, os.environ["REPORT_RECIPIENTS"]


def avisar(filas: list[dict], enviador=enviar) -> tuple[bool, str]:
    """Avisa si corresponde y **marca la fila de hoy**. Devuelve (todo bien, que paso).

    `enviador` se inyecta para poder probar el flujo completo sin correo. La
    fila queda marcada tanto si salio como si no: el historial tiene que
    mostrar los intentos fallidos, que son los que importan.
    """
    a = pendiente(filas)
    if a is None:
        return True, "sin transicion pendiente"
    ok, detalle = enviador(a)
    filas[-1]["aviso"] = f"a {a['hacia']} ({a['cual']}/{DIAS_DE_AVISO})"
    filas[-1]["aviso_estado"] = "enviado" if ok else "fallo"
    if ok:
        return True, f"aviso {a['cual']}/{DIAS_DE_AVISO}: cambiar a {nombre_fondo(a['hacia'])}"
    return False, (f"AVISO NO ENVIADO — cambiar a {nombre_fondo(a['hacia'])}; {detalle}")
