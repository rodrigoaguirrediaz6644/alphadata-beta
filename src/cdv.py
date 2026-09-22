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
COLUMNAS = ["date", "cdv", "subyacente", "cdv_clp", "volumen"]

# Una razón muy lejos de 1 no es un premio, es otro instrumento o un dato roto:
# así se descubrió que el símbolo anotado para Bank of America era el de Boeing.
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


def bajar(universe: pd.DataFrame, periodo: str = "2y", ruta: Path | None = None) -> pd.DataFrame:
    """Baja los cierres de los CDV y los guarda. Es la única parte con red."""
    import yfinance as yf

    filas = []
    for base, simbolo in cdvs(universe).items():
        try:
            h = yf.Ticker(simbolo).history(period=periodo, auto_adjust=False)
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
    return tabla


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
    return d.loc[d.desvio.abs() < RAZON_MAXIMA]


def premio(cdv: pd.DataFrame, precios: pd.DataFrame, desde=None) -> Premio | None:
    """El premio medio sobre las ruedas frescas, o None si no alcanzan.

    `desde` acota la ventana: sin él toma todo lo que haya, que para decidir si
    la corredora cambió de régimen es demasiado viejo.
    """
    d = frescas(cdv, precios)
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
