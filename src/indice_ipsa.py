"""El IPSA real, un dato por día, sin descargas manuales.

`IPSA_TR` es el MSCI IPSA Gross en pesos. Hasta el 17-09-2026 se cargaba a mano
desde un archivo de la Bolsa de Santiago; el historial ya está guardado y lo
único que falta cada día es el último nivel. Esto lo trae del gráfico público
de msci.com y lo agrega al almacén, que nunca reescribe lo ya grabado.

**Se validó contra lo guardado antes de usarlo:** en pesos y variante Gross, los
niveles del 14 al 17-09-2026 coinciden con el archivo manual al centavo
(11.342,39; 11.322,60; 11.235,60; 11.381,18). En dólares o en la variante Net
son otros números, y mezclarlos con la serie guardada es el empalme que ya
produjo un salto de 100 a 212 en el NAV. Por eso cada corrida vuelve a comparar
los días que se solapan y se niega a agregar nada si dejan de calzar.

## Lo que esto no es

- **Un contrato.** El gráfico de msci.com es público, pero no es una API
  documentada ni ofrecida para esto. Se pide una vez por día. Si desaparece o
  cambia, la línea del IPSA en el informe deja de avanzar y nada más: el
  cálculo de las estrategias no lo lee.
- **Un dato sin huecos.** MSCI publica el nivel con uno o más días de atraso, y
  en los feriados repite el último. Los días sin dato no se consideran: el
  informe arrastra el último valor unas ruedas y luego la línea termina donde
  terminan los datos.

## Cuándo avisa

Un día sin dato no es una falla. **Sí lo es que el IPSA lleve más de
`MAX_ATRASO_HABILES` ruedas hábiles sin avanzar respecto del mercado chileno**,
porque a esa altura la línea del informe ya no es la de hoy y nadie lo ve. Ese
caso lo detecta `atraso` en un paso aparte de la captura diaria, que sale en
rojo y dispara el aviso por correo. La captura del IPSA en sí va con
`continue-on-error`, para que una falla de MSCI no impida guardar el cierre
chileno.

Solo biblioteca estándar más pandas.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from src.price_store import agregar

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TICKER = "IPSA_TR"
SIMBOLO = "MSCI_IPSA_GROSS"
CODIGO_MSCI = "767564"
URL = ("https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph"
       "?currency_symbol=CLP&index_variant=GRTR&start_date={desde}&end_date={hasta}"
       "&data_frequency=DAILY&baseValue=false&index_codes=" + CODIGO_MSCI)
AGENTE = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}

# Cuántos días atrás se vuelve a pedir, sólo para comparar contra lo guardado.
SOLAPE_DIAS = 10
# Lo guardado viene redondeado a dos decimales y el nivel de MSCI trae doce.
TOLERANCIA_SOLAPE = 1e-5
# Nunca se movió más de 9,7% en un día en cinco años. Como el almacén no permite
# corregir, un valor imposible se rechaza antes de grabarlo.
SALTO_IMPOSIBLE = .12
# Cuántas ruedas hábiles puede llevar el IPSA detrás del mercado chileno antes de
# avisar. MSCI publica con un día de atraso, y tras un feriado largo el último
# nivel repetido se descarta, así que dos o tres es lo normal y cinco ya no.
MAX_ATRASO_HABILES = 4
COLUMNAS = ["date", "alphadata_ticker", "yahoo_ticker", "open", "high", "low", "close", "adjusted_close", "volume"]


def _descargar(desde: date, hasta: date, timeout: int = 40) -> dict:
    url = URL.format(desde=f"{desde:%Y%m%d}", hasta=f"{hasta:%Y%m%d}")
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENTE), timeout=timeout) as respuesta:
        return json.load(respuesta)


def niveles(cuerpo: dict) -> pd.Series:
    """La respuesta de MSCI como serie de nivel por fecha. Falla fuerte si no es lo esperado."""
    if cuerpo.get("error_code"):
        raise ValueError(f"MSCI respondió con error: {cuerpo.get('error_message', cuerpo['error_code']).strip()}")
    if cuerpo.get("ISO_currency_symbol") != "CLP" or cuerpo.get("index_variant_type") != "GRTR" \
            or str(cuerpo.get("msci_index_code")) != CODIGO_MSCI:
        raise ValueError("MSCI entregó otra serie que la pedida (moneda, variante o índice): "
                         f"{cuerpo.get('ISO_currency_symbol')}/{cuerpo.get('index_variant_type')}/"
                         f"{cuerpo.get('msci_index_code')}")
    filas = (cuerpo.get("indexes") or {}).get("INDEX_LEVELS") or []
    serie = pd.Series({pd.to_datetime(str(f["calc_date"]), format="%Y%m%d"): float(f["level_eod"]) for f in filas},
                      dtype=float).sort_index()
    if not serie.empty and (~serie.map(lambda v: v == v and v > 0)).any():
        raise ValueError("MSCI entregó niveles no positivos o vacíos.")
    return serie


def sin_repetidos(serie: pd.Series) -> pd.Series:
    """Quita los días en que el nivel es idéntico al anterior.

    En un feriado chileno MSCI repite el último nivel (el 18-09-2026 trae el
    mismo número que el 17, salvo por la última cifra de doce: 11381,183653564593
    contra 11381,183653564589). Comparar por igualdad exacta los deja pasar; un
    nivel igual al anterior con nueve cifras no ocurre en una rueda de verdad.
    """
    if serie.empty:
        return serie
    igual = (serie - serie.shift()).abs() <= serie.abs() * 1e-9
    return serie.loc[~igual.fillna(False)]


def nuevos(guardado: pd.DataFrame, cuerpo: dict) -> pd.DataFrame:
    """Las filas posteriores a la última guardada, ya validadas.

    Levanta `ValueError` en vez de devolver algo dudoso: agregar un dato malo es
    irreversible, y no agregar uno bueno se arregla mañana.
    """
    recibido = niveles(cuerpo)
    propio = guardado.loc[guardado.alphadata_ticker == TICKER]
    if propio.empty:
        raise ValueError("No hay historial de IPSA_TR contra el cual comparar; no se empalma una serie en el aire.")
    previo = pd.Series(pd.to_numeric(propio.adjusted_close, errors="coerce").to_numpy(),
                       index=pd.to_datetime(propio.date)).sort_index().dropna()
    ultima = previo.index.max()

    comunes = recibido.index.intersection(previo.index)
    if len(comunes) == 0:
        raise ValueError("Ningún día del solape coincide con lo guardado; no se puede validar la serie.")
    error = ((recibido.loc[comunes] - previo.loc[comunes]).abs() / previo.loc[comunes]).max()
    if error > TOLERANCIA_SOLAPE:
        raise ValueError(f"Los niveles de MSCI ya no calzan con lo guardado (diferencia {error:.2%} en el solape): "
                         "es otra serie. No se agrega nada.")

    tramo = sin_repetidos(recibido.loc[recibido.index >= comunes.max()])
    tramo = tramo.loc[tramo.index > ultima]
    if tramo.empty:
        return pd.DataFrame(columns=COLUMNAS)
    saltos = pd.concat([previo.iloc[[-1]], tramo]).pct_change().dropna().abs()
    if (saltos > SALTO_IMPOSIBLE).any():
        raise ValueError(f"Un cambio diario de {saltos.max():.1%} en el IPSA no es creíble; no se agrega nada.")
    return pd.DataFrame({"date": tramo.index, "alphadata_ticker": TICKER, "yahoo_ticker": SIMBOLO,
                         "open": float("nan"), "high": float("nan"), "low": float("nan"),
                         "close": tramo.round(2).to_numpy(), "adjusted_close": tramo.round(2).to_numpy(),
                         "volume": float("nan")})[COLUMNAS]


def actualizar(guardado: pd.DataFrame, descargar: Callable[[date, date], dict] = _descargar,
               hoy: date | None = None) -> tuple[pd.DataFrame, int]:
    """El almacén con las ruedas nuevas del IPSA, y cuántas se agregaron."""
    hoy = hoy or date.today()
    propio = guardado.loc[guardado.alphadata_ticker == TICKER]
    if propio.empty:
        raise ValueError("No hay historial de IPSA_TR guardado.")
    desde = pd.to_datetime(propio.date).max().date() - timedelta(days=SOLAPE_DIAS)
    agregadas = nuevos(guardado, descargar(desde, hoy))
    if agregadas.empty:
        return guardado, 0
    resultado, revisiones = agregar(guardado, agregadas)
    if len(revisiones):
        raise ValueError("El almacén habría reescrito filas ya grabadas del IPSA; no se guarda.")
    return resultado, len(agregadas)


def atraso(guardado: pd.DataFrame, locales: set[str]) -> tuple[pd.Timestamp | None, int | None]:
    """Última rueda guardada del IPSA y cuántas ruedas hábiles lleva detrás del mercado chileno.

    Se mide contra la última fecha de las acciones locales, que es la que la
    captura diaria actualiza sola, y no contra el calendario: así un fin de
    semana largo o un feriado no cuentan como atraso.
    """
    fechas = pd.to_datetime(guardado["date"], errors="coerce")
    propio = fechas[guardado.alphadata_ticker == TICKER].dropna()
    mercado = fechas[guardado.alphadata_ticker.isin(locales)].dropna()
    if propio.empty or mercado.empty:
        return (propio.max() if len(propio) else None), None
    ultima = propio.max()
    return ultima, max(0, len(pd.bdate_range(ultima.normalize(), mercado.max().normalize())) - 1)


def vigilar(guardado: pd.DataFrame, locales: set[str]) -> str | None:
    """El mensaje del atraso si pasó del límite, o None si el IPSA está al día.

    Sin historial o sin mercado con que comparar **también es un aviso**: que no
    se pueda medir no puede leerse como que está al día.
    """
    ultima, dias = atraso(guardado, locales)
    if dias is None:
        return "No se pudo medir el atraso del IPSA: falta su historial o el del mercado chileno."
    if dias > MAX_ATRASO_HABILES:
        return (f"El IPSA lleva {dias} ruedas hábiles sin avanzar: el último dato es del {ultima:%d-%m-%Y}. "
                f"El límite son {MAX_ATRASO_HABILES}.")
    return None


def vigilar_main() -> None:                                     # pragma: no cover - entrada
    from src.fetch_prices import load_universe
    universe = load_universe()
    locales = set(universe.loc[universe.tipo.isin({"accion_local", "accion_sigma"}), "alphadata_ticker"])
    problema = vigilar(pd.read_csv(DATA / "market_prices_daily.csv", parse_dates=["date"]), locales)
    if problema:
        raise SystemExit(problema)
    print("IPSA al día respecto del mercado chileno.")


def main() -> None:                                             # pragma: no cover - entrada
    import sys
    if sys.argv[1:] == ["vigilar"]:
        return vigilar_main()
    ruta = DATA / "market_prices_daily.csv"
    guardado = pd.read_csv(ruta, parse_dates=["date"])
    ultima = pd.to_datetime(guardado.loc[guardado.alphadata_ticker == TICKER, "date"]).max()
    resultado, cuantas = actualizar(guardado)
    if not cuantas:
        print(f"IPSA al día: sin ruedas nuevas desde el {ultima:%d-%m-%Y}.")
        return
    resultado.to_csv(ruta, index=False, date_format="%Y-%m-%d")
    fin = pd.to_datetime(resultado.loc[resultado.alphadata_ticker == TICKER, "date"]).max()
    print(f"IPSA: {cuantas} ruedas nuevas, del {ultima:%d-%m-%Y} (excluido) al {fin:%d-%m-%Y}.")


if __name__ == "__main__":                                      # pragma: no cover
    main()
