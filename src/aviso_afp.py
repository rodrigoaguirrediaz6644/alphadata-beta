"""El aviso de cambio de fondo, el mismo dia. Corre dentro del trabajo diario.

**Por que existe.** El informe semanal no sirve como instrumento: entre que la
senal habla un lunes y Rodrigo lo lee el viernes se pierden cuatro dias, y
sumados al rezago de ejecucion la proteccion medida se deteriora varios puntos.

**Que se opera: la votacion, no una media.** La regla es la de
`registro_afp.posicion_por_voto`: al refugio cuando dos o mas de las cinco lo
indican, de vuelta al agresivo cuando menos de dos.

**Las dos fechas son distintas y las dos tienen que estar.** El dia del envio
manda —de ahi salen «solicitar hoy» y la fecha de materializacion— y la fecha
del valor cuota dice que tan viejo es el dato con el que se decidio. Las tuve
confundidas: la materializacion salia del ultimo dia con dato, asi que despues
de Fiestas Patrias el aviso habria dicho «materializado el 23» cuando pidiendolo
ese dia se materializa cerca del 29.

**Lo que decide si esto sirve no es que dispare: es que no falle callado.** Un
aviso que no llega es peor que no tener aviso. Y uno que llega a tiempo y manda
al fondo equivocado es peor todavia, asi que hay una prueba dedicada a lo unico
que este correo tiene que acertar: el nombre del fondo destino.

Y al reves: **la falta de aviso nunca puede tumbar el registro ni el informe.**
Es el defecto que ya nos costo un informe entero con FRED.

Solo biblioteca estandar, como el registro.
"""
from __future__ import annotations

import datetime as dt
import os
import smtplib
from email.message import EmailMessage
from html import escape

from src.registro_afp import (AFP, BANDA, CONGELADO, DENTRO, FUERA, MEDIAS,
                              REFUGIO, REZAGO, VOTOS_PARA_SALIR, transicion)

# Un correo se pierde; tres no. Y asi no hace falta que el sistema sepa en que
# fondo esta Rodrigo de verdad, que es una complicacion que no vale lo que
# cuesta.
DIAS_DE_AVISO = 3

# El ahorro voluntario, que es el unico que se puede traspasar libremente. Va
# en el aviso porque es lo que evita la duda de un segundo al leerlo apurado.
CUENTA = "Cuenta 2"

SECRETOS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REPORT_RECIPIENTS")

DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def nombre_fondo(codigo: str) -> str:
    """«A» -> «Fondo A». El codigo sale del registro, nunca escrito aca.

    En abril de 2027 los multifondos desaparecen y quedan los generacionales.
    Si el nombre estuviera en el codigo del aviso, ese dia el correo diria
    «cambiar a Fondo E» sobre un fondo que ya no existe.
    """
    return f"Fondo {codigo}"


def _fecha(d: dt.date) -> str:
    return d.strftime("%d-%m-%Y")


def _largo(d: dt.date) -> str:
    """«martes 23 de septiembre». Sin `locale`, que en un runner no esta puesto."""
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def _miles(valor: str) -> str:
    try:
        return f"{float(valor):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    except (TypeError, ValueError):
        return valor or "—"


def habiles_adelante(fecha, n: int = REZAGO) -> dt.date:
    """La fecha en que quedaria materializado el cambio, contando dias habiles.

    Cuenta lunes a viernes y **no sabe de feriados chilenos**, asi que en una
    semana con feriado la fecha real cae un dia despues. Va dicho como
    aproximada en vez de fingir precision que no hay.
    """
    d = dt.date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
    while n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _desde_cuando(filas: list[dict], idx: int) -> str:
    """Desde que fecha venia la posicion anterior. Para el bloque de contexto."""
    previa = filas[idx - 1]["posicion"] if idx else None
    i = idx - 1
    while i > 0 and filas[i - 1]["posicion"] == previa:
        i -= 1
    return filas[i]["fecha"] if previa else filas[0]["fecha"]


def _detalle(filas: list[dict], idx: int, hacia: str, ensayo: bool = False) -> dict:
    """Lo que el correo necesita, con las dos fechas separadas y nombradas."""
    hoy = filas[-1]
    envio = dt.date.today()
    medias = [(m, hoy[f"pos_{m}"], float(hoy[f"razon_{m}"]) if hoy[f"razon_{m}"] else None)
              for m in MEDIAS]
    dato = dt.date.fromisoformat(hoy["fecha"])
    return {
        "hacia": hacia,
        "desde": filas[idx - 1]["posicion"] if idx else DENTRO,
        # **La fecha que manda.** De aca salen «solicitar hoy» y la de
        # materializacion: es cuando se puede pedir, no cuando se midio.
        "fecha_envio": envio,
        # **La otra.** Dice que tan viejo es el dato con el que se decidio: el
        # valor cuota se publica con rezago y un feriado largo lo estira.
        "fecha_dato": dato,
        "dias_de_dato": (envio - dato).days,
        "materializa": habiles_adelante(envio),
        "medias": medias,
        "votos": sum(1 for _, p, _ in medias if p == FUERA),
        "cuota_a": hoy.get(f"vc_{DENTRO.lower()}", ""),
        "cuota_destino": hoy.get(f"vc_{hacia.lower()}", ""),
        "desde_cuando": _desde_cuando(filas, idx),
        "cual": len(filas) - 1 - idx + 1,
        "ensayo": ensayo,
    }


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
    idx, _, hacia = t
    if len(filas) - 1 - idx >= DIAS_DE_AVISO:
        return None
    if filas[-1].get("aviso_estado") == "enviado":
        return None
    return _detalle(filas, idx, hacia)


def ensayo(filas: list[dict]) -> dict:
    """Un aviso de mentira **con forma de aviso real**, para comprobar el correo.

    Existe por la misma razon que el ensayo de Vigilancia: el primer aviso real
    no puede ser tambien la primera prueba del SMTP desde este flujo. Con FRED
    ya nos paso que algo respondia en local y no en GitHub.

    **Y tiene que mover de fondo de verdad.** El primero que mande usaba la
    posicion de hoy como destino, asi que el correo decia «Fondo A» dos veces y
    no demostraba nada: un ensayo que no se parece al aviso real no prueba lo
    que uno cree que prueba. Ahora sale siempre hacia el otro lado.
    """
    hoy = filas[-1] if filas else {}
    actual = hoy.get("posicion") or DENTRO
    hacia = REFUGIO if actual == DENTRO else DENTRO
    return _detalle(filas, len(filas) - 1, hacia, ensayo=True) if filas else {}


# --------------------------------------------------------------------------
# la forma
# --------------------------------------------------------------------------

def asunto(a: dict) -> str:
    """La instruccion completa en el asunto: se lee desde la pantalla bloqueada."""
    dia = _fecha(a["fecha_envio"])
    if a.get("ensayo"):
        return f"[ENSAYO] AFP: cambiar a {nombre_fondo(a['hacia'])}  —  {dia}"
    return f"AFP: cambiar a {nombre_fondo(a['hacia'])}  —  solicitar hoy {dia}"


def _pie(a: dict) -> str:
    return (f"Regla de votacion sobre {len(MEDIAS)} medias de "
            f"{', '.join(str(m) for m in MEDIAS)} dias de cotizacion, banda de "
            f"{BANDA:.0%}, ejecucion a {REZAGO} dias habiles. "
            f"Congelada el {_fecha(dt.date.fromisoformat(CONGELADO))}.")


def texto(a: dict) -> str:
    """La misma instruccion y las mismas dos fechas, sin HTML.

    No es un respaldo de segunda: hay clientes que no muestran HTML y el aviso
    no se puede perder por eso.
    """
    lineas = []
    if a.get("ensayo"):
        lineas += ["ESTO ES UN ENSAYO. No hay nada que solicitar.",
                   "Sirve para comprobar que el aviso llega.", ""]
    lineas += [
        f"CAMBIAR A {nombre_fondo(a['hacia']).upper()}",
        f"AFP {AFP.capitalize()} · {CUENTA}",
        "",
        f"Solicitar hoy, {_largo(a['fecha_envio'])}.",
        f"Quedaria materializado alrededor del {_largo(a['materializa'])}.",
        "",
        "La senal:",
    ]
    for m, pos, razon in a["medias"]:
        indica = "refugio" if pos == FUERA else "agresivo"
        marca = "  <-" if pos == FUERA else ""
        r = "—" if razon is None else f"{razon:+.1%}".replace(".", ",")
        lineas.append(f"  {m:>3} d   {indica:<9} {r:>7}{marca}")
    lineas += [
        "",
        f"{a['votos']} de {len(MEDIAS)} indican refugio. "
        f"La regla sale con {VOTOS_PARA_SALIR} o mas.",
        "",
        f"Valor cuota del {_fecha(a['fecha_dato'])} "
        f"({a['dias_de_dato']} dias) — {nombre_fondo(DENTRO)} {_miles(a['cuota_a'])} · "
        f"{nombre_fondo(a['hacia'])} {_miles(a['cuota_destino'])}",
        f"Venias en {nombre_fondo(a['desde'])} desde el "
        f"{_fecha(dt.date.fromisoformat(a['desde_cuando']))}.",
        f"Aviso {a['cual']} de {DIAS_DE_AVISO}.",
        "",
        _pie(a),
    ]
    return "\n".join(lineas) + "\n"


# Misma tipografia y misma paleta que el informe del viernes. No un estilo
# nuevo: el correo tiene que reconocerse como parte de lo mismo. Sin logos, sin
# imagenes y sin colores de semaforo — las imagenes se bloquean por defecto en
# la mitad de los clientes y un aviso que depende de una imagen es un aviso
# roto.
ESTILO = """
body{margin:0;background:#f2f4f7;font:15px/1.5 -apple-system,Segoe UI,Arial,sans-serif;color:#1d2939}
.wrap{max-width:560px;margin:auto;background:#fff}
.head{padding:20px 24px;background:#101828;color:#fff}
.brand{font-size:20px;font-weight:700}.sub{margin-top:2px;color:#c8cfda;font-size:13px}
section{padding:20px 24px;border-bottom:1px solid #eaecf0}
h1{margin:0 0 2px;font-size:26px;line-height:1.15;color:#101828}
.donde{color:#475467;font-size:14px;margin:0 0 14px}
.cuando{font-size:16px;font-weight:700;color:#101828;margin:0}
.luego{color:#475467;font-size:14px;margin:2px 0 0}
table{width:100%;border-collapse:collapse;margin:0}
th,td{padding:8px 6px;border-bottom:1px solid #eaecf0;text-align:right;font-size:14px}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{background:#f9fafb;color:#475467;font-weight:600}
tr.sale td{font-weight:700;background:#f8fafc}
.cuenta{margin:12px 0 0;color:#101828;font-size:14px}
.ctx{margin:0;color:#475467;font-size:14px}
.foot{padding:16px 24px;color:#667085;font-size:12px}
.ensayo{padding:14px 24px;background:#fffaeb;border-bottom:4px solid #f79009;color:#93370d;font-size:14px}
@media(max-width:640px){.head,section,.foot,.ensayo{padding-left:16px;padding-right:16px}h1{font-size:23px}}
"""


def html(a: dict) -> str:
    filas = []
    for m, pos, razon in a["medias"]:
        sale = pos == FUERA
        r = "—" if razon is None else f"{razon:+.1%}".replace(".", ",")
        filas.append(f'<tr class="{"sale" if sale else ""}"><td>{m} d</td>'
                     f'<td>{"refugio" if sale else "agresivo"}</td><td>{r}</td></tr>')
    # La franja del ensayo va **arriba del todo**, antes del bloque de
    # instruccion. Un ensayo con la misma forma que uno real es una trampa
    # esperando si el aviso de que lo es aparece despues de la instruccion.
    franja = ('<div class="ensayo"><strong>Esto es un ensayo.</strong> No hay nada '
              'que solicitar; sirve para comprobar que el aviso llega.</div>'
              if a.get("ensayo") else "")
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{ESTILO}</style></head><body><div class="wrap">
{franja}<div class="head"><div class="brand">AlphaData</div>
<div class="sub">Aviso de cambio de fondo</div></div>

<section>
<h1>Cambiar a {escape(nombre_fondo(a['hacia']))}</h1>
<p class="donde">AFP {escape(AFP.capitalize())} · {escape(CUENTA)}</p>
<p class="cuando">Solicitar hoy, {_largo(a['fecha_envio'])}</p>
<p class="luego">Quedaría materializado alrededor del {_largo(a['materializa'])}</p>
</section>

<section>
<table><thead><tr><th>media</th><th>indica</th><th>razón</th></tr></thead>
<tbody>{''.join(filas)}</tbody></table>
<p class="cuenta"><strong>{a['votos']} de {len(MEDIAS)} indican refugio.</strong>
La regla sale con {VOTOS_PARA_SALIR} o más.</p>
</section>

<section>
<p class="ctx">Valor cuota del {_fecha(a['fecha_dato'])} ({a['dias_de_dato']} días) —
{escape(nombre_fondo(DENTRO))} {_miles(a['cuota_a'])} ·
{escape(nombre_fondo(a['hacia']))} {_miles(a['cuota_destino'])}</p>
<p class="ctx">Venías en {escape(nombre_fondo(a['desde']))} desde el
{_fecha(dt.date.fromisoformat(a['desde_cuando']))}.</p>
<p class="ctx">Aviso {a['cual']} de {DIAS_DE_AVISO}.</p>
</section>

<div class="foot">{_pie(a)}</div>
</div></body></html>"""


# --------------------------------------------------------------------------
# el envio
# --------------------------------------------------------------------------

def enviar(a: dict) -> tuple[bool, str]:
    """Manda el correo en HTML y en texto plano. Devuelve si salio y por que no."""
    faltan = [s for s in SECRETOS if not os.getenv(s)]
    if faltan:
        return False, "faltan secretos: " + ", ".join(faltan)
    msg = EmailMessage()
    msg["Subject"] = asunto(a)
    msg["From"] = os.getenv("SMTP_FROM", os.environ["SMTP_USER"])
    msg["To"] = os.environ["REPORT_RECIPIENTS"]
    msg.set_content(texto(a))
    msg.add_alternative(html(a), subtype="html")
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
        if os.getenv("SIMULAR_AVISO", "").lower() in ("1", "true", "yes"):
            ok, detalle = enviador(ensayo(filas))
            return ok, ("ensayo enviado" if ok else f"ENSAYO NO ENVIADO — {detalle}")
        return True, "sin transicion pendiente"
    ok, detalle = enviador(a)
    filas[-1]["aviso"] = f"a {a['hacia']} ({a['cual']}/{DIAS_DE_AVISO})"
    filas[-1]["aviso_estado"] = "enviado" if ok else "fallo"
    if ok:
        return True, f"aviso {a['cual']}/{DIAS_DE_AVISO}: cambiar a {nombre_fondo(a['hacia'])}"
    return False, (f"AVISO NO ENVIADO — cambiar a {nombre_fondo(a['hacia'])}; {detalle}")
