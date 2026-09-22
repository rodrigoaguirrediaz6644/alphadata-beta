"""El precio del CDV en pesos, que el sistema nunca tuvo, y el premio que paga.

El almacén guarda el **subyacente en dólares** —ABT, IAU— y el precio en pesos
lo sintetiza multiplicando por el tipo de cambio. Nunca tuvo el precio del
instrumento que Rodrigo compra de verdad, que es el CDV listado en Santiago.
Sin él, la pregunta de si la corredora cobra un margen en la conversión no se
podía ni plantear.

## Lo que mide

    premio = (precio del CDV en pesos / precio del subyacente en USD) / USDCLP − 1

Si el CDV siguiera exactamente a su subyacente convertido, el premio sería cero.

## Lo que **no** mide, y hay que decirlo

**Un precio de cierre no puede mostrar un spread de compra-venta.** Un cierre es
una sola punta: la del último negocio. La diferencia entre lo que la corredora
cobra al vender y paga al comprar no está en esta serie ni en ninguna serie de
cierres. Lo que esto mide es un **desvío de nivel**: si el CDV cotiza por encima
o por debajo de su valor teórico.

Y un desvío de nivel **no es un costo por lado**. Si se compra y se vende con el
mismo premio, se cancela. Lo que cuesta plata es que el premio cambie entre la
compra y la venta, y eso se mide aparte, por su variación.

## El filtro que hace la diferencia

**El 96% de las ruedas repite el precio del día anterior** y el volumen es cero
en el 72%. ABTCL estuvo **453 ruedas seguidas** en el mismo precio. Dividir un
precio rancio por un subyacente que sí se movió no mide un premio, mide el
rancio: sobre todas las ruedas la dispersión es 2% y no se puede afirmar nada.

Por eso sólo cuentan las ruedas **frescas**: con volumen y con cambio de precio.
Son el 11% de las ruedas, y sobre ellas la razón contra el teórico se va a 1,00
en todos los nombres con datos, lo que de paso confirma que **el CDV es uno a
uno con la acción** —un supuesto que el sistema venía haciendo sin respaldo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARCHIVO = ROOT / "data" / "cdv_precios.csv"
SIMBOLOS = ROOT / "data" / "cdv_simbolos.csv"
COLUMNAS = ["date", "cdv", "subyacente", "cdv_clp", "volumen"]

# Para **medir el premio**: una razón tan lejos de 1 no es un premio, es otro
# instrumento o un dato roto, y no puede entrar en una media. Para la puerta de
# símbolos es al revés —es la evidencia—, así que el recorte no vive en
# `frescas` sino acá.
RAZON_MAXIMA = .15
# Cuántas ruedas frescas hace falta para decir algo. Con menos, el error
# estándar es más grande que cualquier premio que se quiera detectar.
MINIMO_DE_RUEDAS = 30
# El premio medido sobre dos años es +0,29% con error estándar 0,05%, y viene
# bajando: +0,59% en 2024, +0,35% en 2025, +0,06% en 2026. La banda es ancha a
# propósito, porque lo que esto tiene que pillar es que la corredora cambie de
# régimen —meter un punto— y no el ruido de un mes flojo.
BANDA = .01


@dataclass(frozen=True)
class Premio:
    """El premio del CDV sobre su valor teórico, con su error."""
    medio: float
    error: float
    ruedas: int
    nombres: int
    desde: pd.Timestamp | None
    hasta: pd.Timestamp | None

    @property
    def distinguible(self) -> bool:
        """¿Se puede afirmar que no es cero? Dos errores estándar."""
        return abs(self.medio) > 2 * self.error if self.error > 0 else False

    @property
    def dentro_de_la_banda(self) -> bool:
        return abs(self.medio) <= BANDA


def cdvs(universe: pd.DataFrame) -> dict[str, str]:
    """`{subyacente: símbolo del CDV}` para los que tienen uno confirmado.

    Exxon queda fuera a propósito: su símbolo no se encontró en el proveedor y
    adivinarlo es exactamente el error que tenía Bank of America, cuyo símbolo
    anotado —BACL— resultó ser el de Boeing.
    """
    if "cdv_ticker" not in universe.columns:
        return {}
    simbolo = universe.cdv_ticker.fillna("").astype(str).str.strip()
    u = universe.loc[universe.tipo.isin({"accion_us", "etf_us"}) & simbolo.ne("")]
    return {r.alphadata_ticker: f"{str(r.cdv_ticker).strip()}.SN" for r in u.itertuples()}


def bajar(universe: pd.DataFrame, periodo: str = "2y", ruta: Path | None = None,
          ruta_simbolos: Path | None = None) -> pd.DataFrame:
    """Baja los cierres de los CDV y el nombre que el proveedor les pone.

    El nombre es la parte que importa y no es un adorno: es lo que delató que
    `BACL.SN` era Boeing. Es la única parte con red.
    """
    import yfinance as yf

    filas, nombres = [], []
    for base, simbolo in cdvs(universe).items():
        tk = yf.Ticker(simbolo)
        try:
            info = tk.get_info()
        except Exception:                                       # pragma: no cover - red
            info = {}
        nombres.append({"cdv": simbolo, "subyacente": base,
                        "nombre_proveedor": info.get("longName") or info.get("shortName") or ""})
        try:
            h = tk.history(period=periodo, auto_adjust=False)
        except Exception as e:                                  # pragma: no cover - red
            print(f"{simbolo}: {type(e).__name__}", flush=True)
            continue
        if h.empty:
            print(f"{simbolo}: sin datos", flush=True)
            continue
        h = h.reset_index()[["Date", "Close", "Volume"]]
        h.columns = ["date", "cdv_clp", "volumen"]
        h["date"] = pd.to_datetime(h.date).dt.tz_localize(None).dt.normalize()
        h["cdv"], h["subyacente"] = simbolo, base
        filas.append(h[COLUMNAS])
    tabla = (pd.concat(filas, ignore_index=True) if filas
             else pd.DataFrame(columns=COLUMNAS))
    destino = ruta or ARCHIVO
    tabla.sort_values(["cdv", "date"]).to_csv(destino, index=False, date_format="%Y-%m-%d")
    pd.DataFrame(nombres).sort_values("subyacente").to_csv(ruta_simbolos or SIMBOLOS, index=False)
    return tabla


def cargar_simbolos(ruta: Path | None = None) -> pd.DataFrame:
    destino = ruta or SIMBOLOS
    if not Path(destino).exists():
        return pd.DataFrame(columns=["cdv", "subyacente", "nombre_proveedor"])
    return pd.read_csv(destino).fillna("")


def cargar(ruta: Path | None = None) -> pd.DataFrame:
    destino = ruta or ARCHIVO
    if not Path(destino).exists():
        return pd.DataFrame(columns=COLUMNAS)
    return pd.read_csv(destino, parse_dates=["date"])


def frescas(cdv: pd.DataFrame, precios: pd.DataFrame) -> pd.DataFrame:
    """Las ruedas en que el CDV de verdad transó, con su desvío del teórico.

    Fresca es **volumen y cambio de precio**. El volumen solo no alcanza: hay
    ruedas con volumen que repiten el cierre anterior al peso.
    """
    if cdv.empty or precios.empty:
        return pd.DataFrame(columns=[*COLUMNAS, "desvio"])
    cdv = cdv.sort_values(["cdv", "date"]).copy()
    # La primera rueda de cada serie no tiene anterior, así que no se puede
    # saber si el precio es fresco o viene arrastrado de antes de la ventana.
    # `diff()` da NaN ahí, y NaN != 0 la habría dado por fresca.
    salto = cdv.groupby("cdv").cdv_clp.diff()
    cdv["cambio"] = salto.notna() & salto.ne(0)
    usd = (precios.loc[precios.alphadata_ticker.isin(cdv.subyacente.unique()), ["date", "alphadata_ticker", "close"]]
           .rename(columns={"alphadata_ticker": "subyacente", "close": "usd"}))
    fx = precios.loc[precios.alphadata_ticker == "USDCLP", ["date", "close"]].rename(columns={"close": "fx"})
    d = cdv.merge(usd, on=["date", "subyacente"]).merge(fx, on="date")
    d = d.dropna(subset=["cdv_clp", "usd", "fx"])
    d = d[(d.usd > 0) & (d.fx > 0) & (d.cdv_clp > 0) & (d.volumen.fillna(0) > 0) & d.cambio]
    d["desvio"] = (d.cdv_clp / d.usd) / d.fx - 1
    # **Sin recortar por razón.** El recorte vive en `premio`, que es de quien
    # era: ahí un 3,5 es un dato roto que ensucia una media. Acá un 3,5 es
    # justo la fila que la puerta necesita para rechazar un símbolo, y
    # descartarla la dejaba sin evidencia y sin poder pronunciarse.
    return d


def premio(cdv: pd.DataFrame, precios: pd.DataFrame, desde=None) -> Premio | None:
    """El premio medio sobre las ruedas frescas, o None si no alcanzan.

    `desde` acota la ventana: sin él toma todo lo que haya, que para decidir si
    la corredora cambió de régimen es demasiado viejo.
    """
    d = frescas(cdv, precios)
    d = d.loc[d.desvio.abs() < RAZON_MAXIMA]     # un dato roto no promedia
    if desde is not None:
        d = d.loc[d.date >= pd.Timestamp(desde)]
    vivos = d.groupby("cdv").desvio.count()
    d = d.loc[d.cdv.isin(vivos[vivos >= 5].index)]
    if len(d) < MINIMO_DE_RUEDAS:
        return None
    return Premio(medio=float(d.desvio.mean()),
                  error=float(d.desvio.std() / len(d) ** .5),
                  ruedas=int(len(d)), nombres=int(d.cdv.nunique()),
                  desde=d.date.min(), hasta=d.date.max())


# --- La puerta de símbolos --------------------------------------------------

# Un símbolo se arma pegando un sufijo a un ticker, y **cuando un ticker es
# prefijo de otro la regla produce un instrumento real y equivocado**:
# BA + CL = BACL, que es Boeing, y BAC + CL = BACCL, que es Bank of America.
# No falla con ruido, falla con una serie de precios perfectamente válida de
# otra empresa, y por eso duró dos años sin que nadie lo notara.
BANDA_DE_RAZON = .02
# Ruedas frescas mínimas para pronunciarse sobre la razón de un nombre.
RUEDAS_PARA_LA_RAZON = 10
# Una razón así de lejos de 1 basta para rechazar con **una sola** rueda fresca,
# sin esperar a las diez: BACL cotizaba a 3,5 veces su teórico en la única que
# tuvo. Pero se mide sobre ruedas frescas y nunca sobre el cierre exhibido.
#
# Esto estuvo mal y hay que dejarlo escrito. La red se tendió sobre la razón
# mediana de **todas** las ruedas, con el argumento de que ninguna cantidad de
# rancio explica un 3,6. Es falso: HONCL tiene once precios distintos en 480
# ruedas, y estar congelado mientras el subyacente se movía lo dejó con una
# mediana de 1,77 y un máximo de 2,08. La red lo rechazó y no había nada malo
# con él —sus ruedas frescas dan 1,005—, o sea que iba a impedir comprar una
# posición sana. El tamaño del artefacto no tiene techo: lo fija cuánto se
# movió el subyacente durante el congelamiento, y eso puede ser cualquier cosa.
RAZON_IMPOSIBLE = .25
RUEDAS_PARA_RECHAZAR = 1

OPERABLE = "operable"
RECHAZADO = "rechazado"
SIN_VERIFICAR = "sin verificar"
SIN_SIMBOLO = "sin símbolo"

# Palabras que sobran al comparar el nombre de la empresa con el que publica el
# proveedor: "Apple Inc." contra "Apple Inc.", pero también "Nike Inc." contra
# "NIKE, Inc." y "Coca-Cola Co." contra "The Coca-Cola Company".
_RUIDO = {"the", "inc", "corp", "corporation", "company", "co", "incorporated",
          "ltd", "plc", "sa", "class", "a", "b", "c", "group", "trust"}


def _palabras(nombre: str) -> set[str]:
    limpio = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in str(nombre).lower())
    return {w for w in limpio.split() if w and w not in _RUIDO}


def mismo_nombre(esperado: str, del_proveedor: str) -> bool | None:
    """¿El proveedor dice que ese símbolo es esa empresa?

    None cuando no hay nombre que comparar, que es distinto de que no calce.
    """
    if not str(del_proveedor).strip():
        return None
    a, b = _palabras(esperado), _palabras(del_proveedor)
    if not a or not b:
        return None
    return bool(a & b)


def estado(universe: pd.DataFrame, cdv: pd.DataFrame, precios: pd.DataFrame,
           simbolos: pd.DataFrame | None = None) -> pd.DataFrame:
    """Una fila por nombre estadounidense: si su CDV se puede operar y por qué.

    **Ningún nombre puede aparecer con símbolo en la guía de ingreso si no pasó
    por acá.** Vale para los que están y para los que entren después: la puerta
    no depende de que alguien se acuerde de revisar el que entró este mes.

    Hay cuatro veredictos y no dos, porque **no se puede verificar** y **está
    mal** son cosas distintas y merecen respuestas distintas. Tratarlas igual
    bloquearía a ABT, que no tiene una sola rueda fresca en dos años y cuyo
    símbolo sí está confirmado por nombre.
    """
    mapa = cdvs(universe)
    nombres = {}
    if simbolos is not None and len(simbolos):
        nombres = dict(zip(simbolos.subyacente, simbolos.nombre_proveedor))
    empresa = dict(zip(universe.alphadata_ticker, universe.nombre.astype(str).str.split(" (CDV", regex=False).str[0]))
    f = frescas(cdv, precios) if len(cdv) else pd.DataFrame(columns=["subyacente", "desvio"])

    filas = []
    for t in sorted(universe.loc[universe.tipo.isin({"accion_us", "etf_us"}), "alphadata_ticker"]):
        simbolo = mapa.get(t, "")
        razon = f.loc[f.subyacente == t, "desvio"]
        n = int(len(razon))
        mediana = float(razon.median() + 1) if n else None
        calza = mismo_nombre(empresa.get(t, t), nombres.get(t, ""))
        fila = {"ticker": t, "simbolo": simbolo, "ruedas": n, "razon": mediana,
                "nombre_proveedor": nombres.get(t, ""), "estado": SIN_VERIFICAR, "motivo": ""}
        if not simbolo:
            fila |= {"estado": SIN_SIMBOLO,
                     "motivo": "no se encontró el símbolo del CDV en el proveedor"}
        elif calza is False:
            fila |= {"estado": RECHAZADO,
                     "motivo": f"el proveedor dice que {simbolo} es «{nombres.get(t, '')}», no {empresa.get(t, t)}"}
        elif n >= RUEDAS_PARA_RECHAZAR and abs(mediana - 1) > RAZON_IMPOSIBLE:
            fila |= {"estado": RECHAZADO,
                     "motivo": f"{simbolo} cotiza a {mediana:.2f} veces su valor teórico "
                               f"en las {n} ruedas con negocio: es otro instrumento"}
        elif n >= RUEDAS_PARA_LA_RAZON and abs(mediana - 1) > BANDA_DE_RAZON:
            fila |= {"estado": RECHAZADO,
                     "motivo": f"la razón contra el teórico es {mediana:.4f}, fuera de "
                               f"1,00 ± {BANDA_DE_RAZON:.2f} sobre {n} ruedas"}
        elif n >= RUEDAS_PARA_LA_RAZON:
            fila |= {"estado": OPERABLE,
                     "motivo": f"razón {mediana:.4f} sobre {n} ruedas, y el proveedor confirma la empresa"}
        elif calza:
            fila |= {"estado": OPERABLE,
                     "motivo": f"el proveedor confirma la empresa; sólo {n} ruedas con negocio, "
                               "así que la razón no se puede medir y las unidades suponen uno a uno"}
        else:
            fila |= {"motivo": f"sólo {n} ruedas con negocio y el proveedor no confirma la empresa"}
        filas.append(fila)
    return pd.DataFrame(filas)
