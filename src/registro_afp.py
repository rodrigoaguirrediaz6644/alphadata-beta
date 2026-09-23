"""Registro hacia adelante de la grilla de parametros AFP. No opera nada.

**Por que existe.** El backtest ya no puede discriminar entre estos parametros.
La banda de 2% se eligio despues de ver los datos; el largo de la media se
eligio despues de ver donde estaba el salto; las siete AFP son la misma prueba
repetida siete veces, y los episodios son siete en veintitres anios. Lo ultimo
que aprendimos es que sigue apareciendo estructura que **es de la ventana y no
de la regla**: el precipicio del largo de la media aparece en 2011-2026 y no
existe en 2004-2019.

Seguir barriendo parametros sobre siete crisis es arqueologia, no medicion.

**Entonces no se registra un punto: se registra la grilla.** Cada dia se guarda
la posicion que indicaria cada configuracion, junto con el valor cuota del
Fondo A y de los dos refugios. Con datos que nadie miro antes de elegir los
parametros, el registro puede hacer lo que el backtest ya no puede.

**Y hay que decirlo ahora, no despues: sobre la proteccion esto no va a decir
nada hasta que haya una caida, y eso puede tardar anios.** Escrito de antemano
para que a nadie se le ocurra leer una racha tranquila como confirmacion.

**Pero sobre el costo si dice algo desde el primer mes.** El trato tiene dos
mitades: cuanto ahorra en las caidas y cuanto cuesta en los anios tranquilos,
que se paga en latigazos cada vez que la senal sale y vuelve sin que pasara
nada. Esa segunda mitad no necesita ninguna crisis, y por eso el archivo lleva
el retorno acumulado de cada configuracion contra el de quedarse en el Fondo A.

No escribe en `data/` ni en `reports/` ni toca el pipeline. El informe del
viernes **si lo lee**, para decir cuantas filas lleva y avisar si dejo de
crecer: un cron que se apaga no hace ruido, y ese es justo el modo de falla que
este proyecto vino a eliminar.

Solo biblioteca estandar, a proposito: el trabajo diario no deberia caerse
porque un paquete cambio de version.
"""
from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# La grilla congelada. Una sola casa, y `tests/test_registro_afp.py` la fija.
#
# Cambiar cualquiera de estos numeros **es recalibrar**, que es exactamente lo
# que este registro existe para no hacer. La prueba falla si se tocan; si
# alguna vez hay que cambiarlos, que sea un commit que lo diga en voz alta y
# que reinicie el registro, no una edicion silenciosa.
# --------------------------------------------------------------------------

BANDA = .02

# En **dias de cotizacion**, no corridos ni de calendario. Esta distincion nos
# costo dos corridas y una discrepancia entera entre sesiones: «126 dias» eran
# 126 corridos para una y 126 de cotizacion para la otra, que son 90 contra 126
# de ventana efectiva, y el resultado cambia seis puntos.
MEDIAS = (45, 64, 90, 105, 126)

# 4 dias habiles desde el dia habil siguiente a la solicitud. Es el numero
# documentado; el real lo tiene que confirmar la AFP por escrito.
REZAGO = 4

# El refugio se guarda como dato, no como eleccion: la columna de senal dice si
# estar en el Fondo A o fuera, y quien lea decide con cual refugio valorizarlo.
# El D va al lado del E porque en abril de 2027 los dos desaparecen del menu y
# no sabemos todavia cual de los generacionales ocupa ese lugar.
REFUGIOS = ("E", "D")

# **El refugio que se opera.** El registro guarda los dos; esto dice cual se
# avisa. La medicion recomienda el E en todas las ventanas comparables, y no
# por ser mas tranquilo sino por correlacion: el E se mueve distinto del A
# (+0,136) y el D se mueve parecido (+0,809), y eso es lo que importa cuando
# uno llega tarde al refugio, que es siempre.
#
# Es una sola casa a proposito: el aviso y el informe leen de aca, y en abril
# de 2027, cuando A y E dejen de existir, se cambia en un lugar.
REFUGIO = "E"

# **Cuantas de las cinco medias tienen que indicar salida para salir.**
#
# Operar exige una instruccion, no cinco, y elegir una de las cinco medias es
# justo la decision contaminada: las elegimos mirando estos datos. La salida es
# no elegir y que voten.
#
# Dos, y no tres ni cinco. Esto tambien se eligio mirando la tabla —es
# seleccion posterior como todo lo demas— pero lo que la hace defendible es que
# 2 de 5 y 3 de 5 dan casi lo mismo en las tres ventanas medidas, asi que la
# eleccion entre ellas no es la que decide. **La que decide es no esperar a la
# unanimidad: esperar a las cinco cuesta siete puntos de caida.**
VOTOS_PARA_SALIR = 2

# Si el valor cuota del fondo agresivo se mueve mas que esto en un dia, el
# aviso no dispara y la corrida sale en rojo. Nunca paso en 24 anios: el peor
# dia del Fondo A esta muy por debajo. Si pasa, es dato malo antes que mercado,
# y un aviso falso es peor que ningun aviso porque Rodrigo va a estar
# confiando.
SALTO_IMPOSIBLE = .08

AFP = "CUPRUM"
FUENTE = "https://raw.githubusercontent.com/collabmarket/data_afp/master/data/VC-{}.csv"

# **La fecha desde la cual esto vale como evidencia.**
#
# El archivo trae la historia completa porque la senal de histeresis depende de
# todo lo anterior y no se puede empezar en el aire. Pero esa historia es la
# misma sobre la que se eligieron la banda y el largo de la media, asi que **no
# discrimina nada**: ya la miramos antes de elegir.
#
# Solo las filas con fecha posterior a esta cuentan. Si alguna vez alguien
# calcula un rendimiento sobre el archivo entero y lo presenta como validacion,
# esta linea es la que dice que no lo es.
CONGELADO = "2026-09-23"

# Absoluta y no relativa al directorio de trabajo: el informe del viernes la
# lee desde el pipeline, que corre desde otra parte, y una ruta relativa
# devolveria "no hay registro" en vez de fallar. Eso convertiria la alarma en
# lo contrario de una alarma.
SALIDA = Path(__file__).resolve().parents[1] / "registro" / "afp_senales.csv"

DENTRO, FUERA = "A", "fuera"


# --------------------------------------------------------------------------
# datos
# --------------------------------------------------------------------------

def bajar(afp: str = AFP, url: str | None = None) -> list[tuple[str, dict[str, float]]]:
    """Valor cuota diario de la Superintendencia, via el espejo de collabmarket.

    El archivo viene con `;` de separador y `,` de decimal, y arranca en 1981
    con casi todas las columnas vacias: los multifondos A, B, D y E nacen en
    2002 y el C es el fondo unico anterior. Se devuelven solo las fechas que
    tienen los tres fondos que nos interesan.
    """
    req = urllib.request.Request(url or FUENTE.format(afp),
                                 headers={"User-Agent": "AlphaData/2.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        crudo = r.read().decode("utf-8")

    filas = []
    lineas = crudo.strip().split("\n")
    cabecera = [c.strip() for c in lineas[0].split(";")]
    for linea in lineas[1:]:
        campos = dict(zip(cabecera, (c.strip() for c in linea.split(";"))))
        try:
            valores = {f: float(campos[f].replace(",", ".")) for f in ("A", "D", "E")}
        except (KeyError, ValueError):
            continue           # alguna de las tres columnas no existe todavia
        filas.append((campos["Fecha"], valores))
    filas.sort()
    return filas


def de_cotizacion(filas):
    """Se queda con los dias en que el valor cuota **se movio**.

    La serie es de calendario corrido: sabado y domingo repiten el viernes
    porque la cuota no devenga fin de semana, y los feriados repiten el dia
    anterior. Filtrar por «el valor cambio» deja los dias de cotizacion sin
    tener que mantener un calendario de feriados chilenos.

    La contra, dicha: un dia de rueda en que la cuota quede exactamente igual
    al dia anterior se pierde. Es raro y no mueve una media movil, pero el
    metodo no distingue ese caso de un feriado.
    """
    salida, previo = [], None
    for fecha, v in filas:
        if previo is None or v["A"] != previo:
            salida.append((fecha, v))
            previo = v["A"]
    return salida


# --------------------------------------------------------------------------
# la regla
# --------------------------------------------------------------------------

def razones(precios: list[float], media: int) -> list[float | None]:
    """precio / media movil de `media` dias - 1, o None mientras no alcanza."""
    out, suma = [], 0.
    for i, p in enumerate(precios):
        suma += p
        if i >= media:
            suma -= precios[i - media]
        out.append(p / (suma / media) - 1 if i >= media - 1 else None)
    return out


def histeresis(razones_: list[float | None], banda: float = BANDA) -> list[str | None]:
    """Sale del Fondo A cuando la razon baja de -banda; vuelve cuando sube de +banda.

    Entre los dos umbrales **se mantiene la posicion**: es histeresis, no una
    zona neutra. Ahi esta el ahorro de rotacion, y es lo unico de toda esta
    linea que resulto ser mecanico y no un parametro afortunado: la meseta
    aparece igual en las siete AFP, con dispersion de un punto.

    Arranca dentro del Fondo A, que es la posicion por defecto de quien no hace
    nada.
    """
    out, cur = [], DENTRO
    for x in razones_:
        if x is None:
            out.append(None)
            continue
        if cur == DENTRO and x < -banda:
            cur = FUERA
        elif cur == FUERA and x > banda:
            cur = DENTRO
        out.append(cur)
    return out


def ejecutada(senales: list[str | None], rezago: int = REZAGO) -> list[str | None]:
    """La posicion **en vigor** hoy es la senal de hace `rezago` dias de cotizacion.

    Teorica: nadie esta operando esto. Es la columna que hay que mirar cuando
    algun dia se compare contra lo que hizo el Fondo A, porque la senal del dia
    no se puede materializar el dia.
    """
    return [None] * rezago + senales[:-rezago] if rezago else list(senales)


# --------------------------------------------------------------------------
# el archivo
# --------------------------------------------------------------------------

# Las columnas de evento **no se recalculan**: son el registro de algo que pasó
# una vez —que salió un aviso y si llegó— y no una funcion de la serie. Se
# arrastran del archivo anterior y quedan fuera de la guardia de alteraciones,
# que compara lo determinista. Mezclar las dos clases en la misma tabla es
# comodo para leerlas juntas y peligroso si se tratan igual.
COLUMNAS_EVENTO = ("aviso", "aviso_estado")


def columnas() -> list[str]:
    cols = ["fecha"] + [f"vc_{f.lower()}" for f in (DENTRO, *REFUGIOS)]
    for m in MEDIAS:
        cols += [f"razon_{m}", f"senal_{m}", f"pos_{m}"]
    cols += ["votos", "posicion", "acum_a", "acum_voto"]
    for m in MEDIAS:
        cols += [f"acum_{m}_{r.lower()}" for r in REFUGIOS]
    return cols + list(COLUMNAS_EVENTO)


def votos(grilla, i: int) -> int | None:
    """Cuantas de las cinco configuraciones estarian fuera del Fondo A hoy.

    Sobre la posicion **en vigor**, no sobre la senal del dia: lo que se vota
    es lo que se puede materializar.
    """
    ps = [grilla[m][2][i] for m in MEDIAS]
    if any(p is None for p in ps):
        return None
    return sum(1 for p in ps if p == FUERA)


def posicion_por_voto(n: int | None, refugio: str | None = None) -> str | None:
    """La instruccion unica: al refugio con `VOTOS_PARA_SALIR` o mas, si no al A."""
    if n is None:
        return None
    return (refugio or REFUGIO) if n >= VOTOS_PARA_SALIR else DENTRO


def _base(fechas: list[str], congelado: str | None = None) -> int:
    """El ultimo dia anterior o igual al congelamiento. Desde ahi se acumula.

    `congelado` se resuelve adentro y no como valor por defecto: un valor por
    defecto captura la constante en el momento de definir la funcion, y
    entonces CONGELADO pasa a tener dos casas que pueden discrepar. Lo
    descubri probando, cuando el peaje salio vacio con una fecha movida.
    """
    congelado = congelado or CONGELADO
    base = 0
    for i, f in enumerate(fechas):
        if f <= congelado:
            base = i
    return base


def acumulados(coti, grilla, congelado: str | None = None,
               pos_voto: list[str | None] | None = None) -> dict[str, list[str]]:
    """Retorno acumulado desde el congelamiento: el de cada configuracion y el del Fondo A.

    **Esta es la mitad del trato que si se puede medir sin esperar una crisis.**
    La estrategia tiene dos mitades: cuanto ahorra en las caidas, que no se
    sabra hasta que haya una, y **cuanto cuesta en los anios tranquilos**, que
    se paga en latigazos cada vez que la senal sale y vuelve sin que pasara
    nada. Esa segunda mitad empieza a medirse el primer mes.

    Y da una pregunta que el archivo puede contestar mucho antes que la otra:
    **de las cinco medias, cual paga menos peaje en calma.** Si una se despega
    hacia abajo en dos anios de mercado tranquilo, queda descartada sin esperar
    el desplome.

    Queda guardado y no derivado a mano despues: si hay que reconstruirlo,
    alguien va a reconstruirlo distinto.
    """
    congelado = congelado or CONGELADO
    fechas = [f for f, _ in coti]
    base = _base(fechas, congelado)
    n = len(coti)

    def acumular(fondo_por_dia) -> list[str]:
        out, acc = [""] * n, 1.
        for i in range(base + 1, n):
            f = fondo_por_dia(i)
            if f is None:
                out[i] = ""
                continue
            acc *= coti[i][1][f] / coti[i - 1][1][f]
            out[i] = f"{acc - 1:.6f}"
        return out

    cols = {"acum_a": acumular(lambda i: DENTRO)}
    # La del voto es la que de verdad se opera, asi que es la que dira si la
    # votacion fue la eleccion correcta. Eso solo se sabe hacia adelante.
    if pos_voto is not None:
        cols["acum_voto"] = acumular(lambda i: pos_voto[i])
    for m in MEDIAS:
        pos = grilla[m][2]
        for ref in REFUGIOS:
            cols[f"acum_{m}_{ref.lower()}"] = acumular(
                lambda i, _p=pos, _r=ref: DENTRO if _p[i] == DENTRO else (
                    _r if _p[i] == FUERA else None))
    return cols


def construir(filas=None) -> list[dict]:
    """Recalcula la grilla entera desde la fuente. **Nada se guarda incremental.**

    Es la norma del censo de series aplicada aca: todo lo publicado se vuelve a
    calcular en cada corrida. Una senal de histeresis depende de todo lo
    anterior, asi que guardar el estado e ir agregando es justo la forma de que
    se quede atras sin que nadie lo note.
    """
    coti = de_cotizacion(filas if filas is not None else bajar())
    fechas = [f for f, _ in coti]
    precios = [v[DENTRO] for _, v in coti]

    grilla = {}
    for m in MEDIAS:
        r = razones(precios, m)
        s = histeresis(r)
        grilla[m] = (r, s, ejecutada(s))

    voto = [votos(grilla, i) for i in range(len(coti))]
    pos_voto = [posicion_por_voto(n) for n in voto]
    acum = acumulados(coti, grilla, pos_voto=pos_voto)

    salida = []
    for i, (fecha, v) in enumerate(coti):
        fila = {"fecha": fecha}
        for f in (DENTRO, *REFUGIOS):
            fila[f"vc_{f.lower()}"] = f"{v[f]:.2f}"
        for m in MEDIAS:
            r, s, p = grilla[m]
            fila[f"razon_{m}"] = "" if r[i] is None else f"{r[i]:.6f}"
            fila[f"senal_{m}"] = s[i] or ""
            fila[f"pos_{m}"] = p[i] or ""
        fila["votos"] = "" if voto[i] is None else str(voto[i])
        fila["posicion"] = pos_voto[i] or ""
        for c, vals in acum.items():
            fila[c] = vals[i]
        for c in COLUMNAS_EVENTO:
            fila[c] = ""
        salida.append(fila)
    return salida


def leer(ruta: Path = SALIDA) -> list[dict]:
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def alteraciones(viejo: list[dict], nuevo: list[dict]) -> list[str]:
    """Filas ya registradas cuyo contenido cambio. **Eso no deberia pasar nunca.**

    El calculo es determinista sobre una serie publica, asi que si una fila
    vieja cambia es porque la fuente revise su historia. Es exactamente lo que
    hay que saber: un registro hacia adelante cuyo pasado se reescribe solo no
    sirve para nada, y peor, no se nota.
    """
    por_fecha = {f["fecha"]: f for f in nuevo}
    malas = []
    # Solo las columnas que existen en los dos archivos. Si el esquema cambio
    # —porque alguien agrego una columna— las nuevas no estan en el viejo y
    # compararlas diria «la fuente reescribio el pasado» sobre algo que no
    # tiene nada que ver con la fuente. Son dos fallas distintas y hay que
    # poder distinguirlas: `cambio_de_esquema` reporta la otra.
    previas = set(viejo[0]) if viejo else set()
    deterministas = [c for c in columnas()
                     if c not in COLUMNAS_EVENTO and c in previas]
    for f in viejo:
        n = por_fecha.get(f["fecha"])
        if n is None:
            malas.append(f"{f['fecha']}: desaparecio de la fuente")
            continue
        for c in deterministas:
            if (f.get(c) or "") != (n.get(c) or ""):
                malas.append(f"{f['fecha']}: {c} era {f.get(c)!r} y ahora es {n.get(c)!r}")
    return malas


def cambio_de_esquema(viejo: list[dict]) -> tuple[list[str], list[str]]:
    """Columnas que aparecen y que desaparecen respecto del archivo commiteado.

    Un cambio de esquema es un cambio de codigo, no una falla de datos: se
    anuncia y se sigue. Lo que no puede pasar es que se confunda con que la
    fuente reescribio la historia, que si es grave.
    """
    if not viejo:
        return [], []
    previas, ahora = set(viejo[0]), set(columnas())
    return sorted(ahora - previas), sorted(previas - ahora)


def arrastrar(viejo: list[dict], nuevo: list[dict]) -> list[dict]:
    """Conserva las columnas de evento del archivo anterior.

    Todo lo demas se recalcula; esto no puede. Que salio un aviso el 12 de
    noviembre y llego es un hecho, no una funcion de la serie: si se
    recalculara, el historial de notificaciones se borraria solo cada dia.
    """
    previo = {f["fecha"]: f for f in viejo}
    for f in nuevo:
        v = previo.get(f["fecha"])
        if v:
            for c in COLUMNAS_EVENTO:
                f[c] = v.get(c) or ""
    return nuevo


def salto_imposible(filas: list[dict]) -> str | None:
    """Un movimiento diario del fondo agresivo que no puede ser mercado.

    Se mira solo el ultimo dia: la historia ya esta validada y revisarla entera
    en cada corrida convertiria un dato viejo y raro en una alarma diaria.
    """
    if len(filas) < 2:
        return None
    hoy, ayer = float(filas[-1]["vc_a"]), float(filas[-2]["vc_a"])
    cambio = hoy / ayer - 1
    if abs(cambio) > SALTO_IMPOSIBLE:
        return (f"{filas[-1]['fecha']}: el Fondo A se movio {cambio:+.2%} en un dia, "
                f"sobre el limite de {SALTO_IMPOSIBLE:.0%}")
    return None


def transicion(filas: list[dict]) -> tuple[int, str, str] | None:
    """El ultimo cambio de la posicion en vigor: (indice, desde, hacia).

    Sobre `posicion`, que es la instruccion unica por votacion, no sobre las
    cinco senales sueltas. Devuelve None si nunca cambio.
    """
    con = [f for f in filas if f["posicion"]]
    for i in range(len(con) - 1, 0, -1):
        if con[i]["posicion"] != con[i - 1]["posicion"]:
            return filas.index(con[i]), con[i - 1]["posicion"], con[i]["posicion"]
    return None


def guardar(filas: list[dict], ruta: Path = SALIDA) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas(), lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


def resumen(filas: list[dict]) -> str:
    u = filas[-1]
    partes = [f"{AFP} al {u['fecha']}   Fondo A {u['vc_a']}   "
              f"E {u['vc_e']}   D {u['vc_d']}",
              f"{len(filas)} dias de cotizacion registrados",
              "",
              f"  {'media':>6} {'razon':>9} {'senal hoy':>11} {'en vigor':>10}"]
    for m in MEDIAS:
        r = u[f"razon_{m}"]
        partes.append(f"  {m:>6} {(float(r) if r else 0):>8.2%} "
                      f"{u[f'senal_{m}'] or '—':>11} {u[f'pos_{m}'] or '—':>10}")
    fuera = sum(1 for m in MEDIAS if u[f"pos_{m}"] == FUERA)
    cuentan = sum(1 for f in filas if f["fecha"] > CONGELADO)
    partes += ["", f"  {fuera} de {len(MEDIAS)} configuraciones estarian fuera del Fondo A.",
               f"  {cuentan} dias cuentan como evidencia (posteriores a {CONGELADO});",
               f"  los otros {len(filas) - cuentan} son la historia sobre la que se",
               "  eligieron los parametros y no discriminan nada."]

    # El peaje: la mitad del trato que no necesita una crisis para medirse.
    if u["acum_a"]:
        a = float(u["acum_a"])
        partes += ["", f"  Desde {CONGELADO}, el Fondo A acumula {a:+.2%}.",
                   f"  Peaje de cada configuracion contra quedarse ahi:",
                   f"    {'media':>6}" + "".join(f"{'refugio ' + r:>14}" for r in REFUGIOS)]
        for m in MEDIAS:
            celdas = []
            for r in REFUGIOS:
                v = u[f"acum_{m}_{r.lower()}"]
                celdas.append(f"{float(v) - a:+.2%}" if v else "—")
            partes.append(f"    {m:>6}" + "".join(f"{c:>14}" for c in celdas))
        partes.append("  En calma el peaje deberia ser negativo y chico; ahi se ve cual"
                      " media cuesta menos.")

    partes.append("  Nada se opera. Nada se recalibra.")
    return "\n".join(partes)


def para_informe(filas: list[dict] | None = None) -> dict | None:
    """Lo que el informe del viernes necesita, armado aca y no alla.

    Los nombres de los fondos salen del registro y **nunca del codigo del
    informe**: en abril de 2027 los multifondos desaparecen y el informe tiene
    que seguir diciendo la verdad sin que nadie edite una plantilla.

    Devuelve None si no hay registro. Quien llama decide que hacer con eso, y
    lo que no puede hacer es reventar: esta seccion es la menos critica del
    informe porque no hay plata adentro.
    """
    filas = leer() if filas is None else filas
    if not filas:
        return None
    u = filas[-1]
    t = transicion(filas)
    peaje = []
    if u["acum_a"]:
        a = float(u["acum_a"])
        for m in MEDIAS:
            v = u[f"acum_{m}_{REFUGIO.lower()}"]
            peaje.append((m, float(v) - a if v else None))
    return {
        "fecha": u["fecha"],
        "filas": len(filas),
        "congelado": CONGELADO,
        "agresivo": DENTRO,
        "refugio": REFUGIO,
        "votos_para_salir": VOTOS_PARA_SALIR,
        "medias": [(m, u[f"senal_{m}"], float(u[f"razon_{m}"]) if u[f"razon_{m}"] else None,
                    u[f"pos_{m}"]) for m in MEDIAS],
        "votos": int(u["votos"]) if u["votos"] else None,
        "posicion": u["posicion"] or None,
        "desde": filas[t[0]]["fecha"] if t else None,
        "acum_a": float(u["acum_a"]) if u["acum_a"] else None,
        "acum_voto": float(u["acum_voto"]) if u["acum_voto"] else None,
        "peaje": peaje,
        "aviso": u.get("aviso") or None,
        "aviso_estado": u.get("aviso_estado") or None,
    }


def main(argv=None) -> int:
    viejo = leer()
    nuevo = construir()
    malas = alteraciones(viejo, nuevo)
    if malas:
        print("La fuente reescribio historia ya registrada:", file=sys.stderr)
        for m in malas[:20]:
            print(f"  {m}", file=sys.stderr)
        if len(malas) > 20:
            print(f"  ... y {len(malas) - 20} mas", file=sys.stderr)
        print("\nNo se sobrescribe. Hay que mirar la fuente antes de seguir.",
              file=sys.stderr)
        return 1
    entran, salen = cambio_de_esquema(viejo)
    if entran or salen:
        print("El esquema del registro cambio en esta corrida:")
        if entran:
            print("  entran: " + ", ".join(entran))
        if salen:
            print("  salen:  " + ", ".join(salen))
        print("  (es un cambio de codigo, no de la fuente; la grilla la fija la prueba)\n")
    nuevo = arrastrar(viejo, nuevo)

    # El aviso va antes de guardar para que la fila salga con su marca puesta,
    # pero **el archivo se guarda pase lo que pase con el correo**: el registro
    # es lo principal y una falla de la notificacion no puede hacerle perder un
    # dia. Es el defecto que ya nos costo un informe entero con FRED.
    problema = salto_imposible(nuevo)
    aviso_ok, aviso_dicho = True, "sin transicion pendiente"
    if problema:
        aviso_dicho = f"aviso suspendido — {problema}"
    else:
        try:
            from src.aviso_afp import avisar
            aviso_ok, aviso_dicho = avisar(nuevo)
        except Exception as e:                   # noqa: BLE001
            aviso_ok, aviso_dicho = False, f"el aviso reviento: {type(e).__name__}: {e}"

    guardar(nuevo)
    print(resumen(nuevo))
    print(f"\n  Aviso: {aviso_dicho}")
    if problema:
        print(f"\n{problema}\nNo se disparo ningun aviso: es dato malo antes que mercado.",
              file=sys.stderr)
        return 1
    if not aviso_ok:
        print(f"\n{aviso_dicho}\nEl registro quedo guardado; el aviso se reintenta manana.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
