"""Reemplaza la serie del benchmark por el MSCI IPSA Gross.

    PYTHONPATH=. python -m tools.reemplazar_benchmark <archivo>              # ensayo
    PYTHONPATH=. python -m tools.reemplazar_benchmark <archivo> --confirmar  # escribe

**Es reemplazo total, no parche.** La serie del ETF proxy `CFMITNIPSA.SN` se
archiva completa y se va entera: no se repara, no se empalma, no se conserva
ningún tramo. Empalmar dos series de niveles distintos fue exactamente lo que
produjo el salto de 100 a 212,56 que el informe terminó suprimiendo.

Lo que se gana y lo que se pierde:

- Se gana una serie viva. El proxy lleva 44 de sus últimas 60 ruedas sin
  variación, porque es un ticker `.SN` y cayó con el resto del feed chileno.
- Se gana la variante correcta. El MSCI IPSA **Gross** reinvierte dividendos,
  igual que el NAV de las estrategias, que se calcula con precios ajustados.
- Se pierde la historia anterior a 2021. El archivo del índice empieza el
  04-01-2021 y el proxy llegaba a 2015. La reconstrucción oficial arranca el
  08-07-2021, así que no la necesita.

## Mantención

La Bolsa de Santiago publica "MSCI IPSA S" —la S es la Gross; la N es sin
dividendos— en ventanas de veinte ruedas que no se pueden ampliar, y su sitio
está detrás de un captcha, así que la descarga es manual y semanal. Veinte
ruedas son cuatro semanas de solape: saltarse una o dos no pierde ningún día, y
el almacén de sólo agregar ignora lo repetido.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.fetch_prices import PRICE_COLUMNS, load_universe
from src.referencia_investing import leer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARCHIVO = DATA / "archivo"
TICKER = "IPSA_TR"
FUENTE = "MSCI_IPSA_GROSS"          # serie manual, no se descarga
MAXIMO_SALTO_ACEPTABLE = .12        # por encima de esto la serie no es continua


def construir_filas(ruta: str) -> pd.DataFrame:
    indice = leer(ruta)
    return pd.DataFrame({
        "date": indice.date, "alphadata_ticker": TICKER, "yahoo_ticker": FUENTE,
        "open": indice.open, "high": indice.high, "low": indice.low,
        "close": indice.close, "adjusted_close": indice.close, "volume": pd.NA,
    })[PRICE_COLUMNS]


def main(ruta: str, confirmar: bool = False) -> int:
    if not ruta or not Path(ruta).exists():
        print(f"No existe el archivo del índice: {ruta}")
        return 1
    nuevas = construir_filas(ruta)
    precios = pd.read_csv(DATA / "market_prices_daily.csv", parse_dates=["date"])
    viejas = precios.loc[precios.alphadata_ticker == TICKER].sort_values("date")

    retornos = nuevas.set_index("date")["close"].pct_change().dropna()
    salto = float(retornos.abs().max())
    print(f"Serie nueva: {len(nuevas)} ruedas, {nuevas.date.min().date()} a {nuevas.date.max().date()}")
    print(f"Serie que se archiva: {len(viejas)} ruedas, {viejas.date.min().date()} a {viejas.date.max().date()}")
    print()
    print("CONDICIÓN 4 — continuidad de la serie nueva:")
    print(f"  mayor variación diaria: {salto:.2%} el {retornos.abs().idxmax().date()}")
    print(f"  ruedas con variación sobre 8%: {int((retornos.abs() > .08).sum())}")
    print(f"  valores repetidos consecutivos: {int((nuevas.close.diff() == 0).sum())}")
    if salto > MAXIMO_SALTO_ACEPTABLE:
        print(f"  RECHAZADO: {salto:.1%} supera el máximo aceptable de {MAXIMO_SALTO_ACEPTABLE:.0%}.")
        return 1
    print(f"  aceptada: por debajo del máximo de {MAXIMO_SALTO_ACEPTABLE:.0%}")

    if not confirmar:
        print("\nEnsayo: no se escribió nada. Repetir con --confirmar.")
        return 0

    ARCHIVO.mkdir(parents=True, exist_ok=True)
    destino = ARCHIVO / "ipsa_tr_proxy_cfmitnipsa.csv"
    viejas.to_csv(destino, index=False, date_format="%Y-%m-%d")

    resto = precios.loc[precios.alphadata_ticker != TICKER]
    resultado = pd.concat([resto, nuevas], ignore_index=True).sort_values(["date", "alphadata_ticker"])
    resultado.to_csv(DATA / "market_prices_daily.csv", index=False, date_format="%Y-%m-%d")

    universo = load_universe()
    universo.loc[universo.alphadata_ticker == TICKER, ["yahoo_ticker", "nombre", "estado"]] = [
        FUENTE, "MSCI IPSA Gross (descarga manual semanal)", "manual"]
    universo.to_csv(ROOT / "config" / "tickers.csv", index=False)

    (ARCHIVO / "reemplazo_benchmark.md").write_text(f"""# Reemplazo del benchmark — {pd.Timestamp.now():%d-%m-%Y}

Reemplazo **total** de la serie `IPSA_TR`. No es un parche.

| | antes | después |
|---|---|---|
| fuente | ETF proxy `CFMITNIPSA.SN`, descarga automática | MSCI IPSA Gross, descarga manual semanal |
| ruedas | {len(viejas):,} | {len(nuevas):,} |
| desde | {viejas.date.min():%d-%m-%Y} | {nuevas.date.min():%d-%m-%Y} |
| hasta | {viejas.date.max():%d-%m-%Y} | {nuevas.date.max():%d-%m-%Y} |
| mayor variación diaria | {viejas.set_index('date').close.pct_change().abs().max():.2%} | {salto:.2%} |

La serie anterior queda íntegra en `ipsa_tr_proxy_cfmitnipsa.csv`. No se borró
ni se empalmó con la nueva: empalmar dos series de niveles distintos fue lo que
produjo el salto de 100 a 212,56 en el NAV.

Se pierde la historia anterior al {nuevas.date.min():%d-%m-%Y}; la
reconstrucción oficial arranca el 08-07-2021 y no la necesita.

`config/tickers.csv` queda con `estado = manual`, que la excluye de la descarga
automática sin sacarla del universo ni del informe de cobertura.
""", encoding="utf-8")
    print(f"\nEscrito. Serie anterior archivada en {destino.relative_to(ROOT)}.")
    print(f"Registro del cambio en {(ARCHIVO / 'reemplazo_benchmark.md').relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    raise SystemExit(main(argumentos[0] if argumentos else "", "--confirmar" in sys.argv))
