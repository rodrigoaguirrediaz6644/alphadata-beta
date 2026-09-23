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

def columnas() -> list[str]:
    cols = ["fecha"] + [f"vc_{f.lower()}" for f in (DENTRO, *REFUGIOS)]
    for m in MEDIAS:
        cols += [f"razon_{m}", f"senal_{m}", f"pos_{m}"]
    cols.append("acum_a")
    for m in MEDIAS:
        cols += [f"acum_{m}_{r.lower()}" for r in REFUGIOS]
    return cols


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


def acumulados(coti, grilla, congelado: str | None = None) -> dict[str, list[str]]:
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

    acum = acumulados(coti, grilla)

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
        for c, vals in acum.items():
            fila[c] = vals[i]
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
    for f in viejo:
        n = por_fecha.get(f["fecha"])
        if n is None:
            malas.append(f"{f['fecha']}: desaparecio de la fuente")
            continue
        for c in columnas():
            if (f.get(c) or "") != (n.get(c) or ""):
                malas.append(f"{f['fecha']}: {c} era {f.get(c)!r} y ahora es {n.get(c)!r}")
    return malas


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


def main(argv=None) -> int:
    nuevo = construir()
    malas = alteraciones(leer(), nuevo)
    if malas:
        print("La fuente reescribio historia ya registrada:", file=sys.stderr)
        for m in malas[:20]:
            print(f"  {m}", file=sys.stderr)
        if len(malas) > 20:
            print(f"  ... y {len(malas) - 20} mas", file=sys.stderr)
        print("\nNo se sobrescribe. Hay que mirar la fuente antes de seguir.",
              file=sys.stderr)
        return 1
    guardar(nuevo)
    print(resumen(nuevo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
