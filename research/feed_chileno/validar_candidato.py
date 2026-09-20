"""Valida una fuente candidata contra los precios chilenos que sabemos buenos.

Uso:
    PYTHONPATH=. python -m research.feed_chileno.validar_candidato <carpeta>

La carpeta contiene un CSV por instrumento. Se aceptan dos formatos: el de
investing.com (Date, Price, Open, High, Low, Vol., Change %, con fechas
MM/DD/YYYY y miles con coma) y uno simple de date,close.

El tramo de comparación termina el 17-07-2026: desde el 18-07 los datos
guardados son los del feed congelado y no sirven como referencia.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.feed_validation import aprueba, comparar, serie_guardada

ROOT = Path(__file__).resolve().parents[2]
CORTE = pd.Timestamp("2026-07-17")  # último cierre chileno confiable

NOMBRES = {
    "banco de chile (sn)": "CHILE",
    "banco de credito e inversiones": "BCI",
    "enel chile": "ENELCHILE",
    "engie energia chile": "ECL",
    "inv la constru": "ILC",
    "latam airlines": "LTM",
    "parq arauco": "PARAUCO",
    "plaza": "MALLPLAZA",
    "salfacorp": "SALFACORP",
    "santander chile": "BSANTANDER",
    "soquimich b": "SQM-B",
}


def ticker_de(nombre: Path) -> str | None:
    base = nombre.stem.lower().replace(" stock price history", "").strip()
    return NOMBRES.get(base, base.upper() if base.upper().isalnum() else None)


def leer(ruta: Path) -> pd.Series:
    bruto = pd.read_csv(ruta, encoding="utf-8-sig", thousands=",")
    columnas = {c.strip().lower(): c for c in bruto.columns}
    fecha = columnas.get("date") or columnas.get("fecha")
    cierre = columnas.get("price") or columnas.get("close") or columnas.get("cierre")
    if fecha is None or cierre is None:
        raise ValueError(f"{ruta.name}: faltan columnas de fecha o cierre")
    serie = pd.Series(
        pd.to_numeric(bruto[cierre], errors="coerce").to_numpy(),
        index=pd.to_datetime(bruto[fecha], format="mixed", errors="coerce"),
    ).dropna().sort_index()
    return serie[~serie.index.duplicated(keep="last")]


def main(carpeta: str) -> int:
    precios = pd.read_csv(ROOT / "data" / "market_prices_daily.csv", parse_dates=["date"])
    precios = precios.loc[precios.date <= CORTE]
    archivos = sorted(Path(carpeta).glob("*.csv"))
    if not archivos:
        print(f"No hay CSV en {carpeta}")
        return 1
    filas, aprobados = [], 0
    for archivo in archivos:
        ticker = ticker_de(archivo)
        referencia = serie_guardada(precios, ticker) if ticker else pd.Series(dtype=float)
        if referencia.empty:
            print(f"{archivo.name}: sin referencia guardada para {ticker}")
            continue
        r = comparar(leer(archivo), referencia)
        ok = aprueba(r)
        aprobados += ok
        filas.append({"ticker": ticker, "dias": r["dias"], "razon_mediana": r["razon_mediana"],
                      "exactos": r["exactos"], "desvio_p95": r["desvio_p95"],
                      "desvio_max": r["desvio_max"], "bloques": len(r["bloques"]), "aprueba": ok})
        marca = "OK   " if ok else "FALLA"
        print(f"{marca} {ticker:<11} dias={r['dias']:<5} mediana={r['razon_mediana']:.6f} "
              f"exactos={r['exactos']:7.2%} p95={r['desvio_p95']:7.4%} max={r['desvio_max']:6.2%} "
              f"bloques={len(r['bloques'])}")
        for b in r["bloques"]:
            print(f"        bloque {b['desde']:%d-%m-%Y}..{b['hasta']:%d-%m-%Y} "
                  f"({b['dias']} dias) factor {b['factor']:.6f} = {b['factor']-1:+.2%}")
    print()
    print(f"Aprueban {aprobados} de {len(filas)} instrumentos.")
    pd.DataFrame(filas).to_csv(Path(__file__).parent / "resultado_validacion.csv", index=False)
    return 0 if aprobados == len(filas) and filas else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
