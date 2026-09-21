"""Arma la tabla de dividendos: el proveedor declara, el precio confirma.

    PYTHONPATH=. python -m tools.construir_dividendos              # ensayo
    PYTHONPATH=. python -m tools.construir_dividendos --confirmar  # escribe

Produce dos archivos:

- `data/dividendos.csv` — los que pasaron la prueba de aceptación: la caída del
  cierre crudo en la fecha ex corresponde al monto dentro de un punto
  porcentual. Son los únicos que se usan para derivar el cierre ajustado.
- `data/dividendos_por_confirmar.csv` — los que no calzaron. **No se usan.**
  Quedan para confirmar a mano contra lo que publica cada empresa, que es el
  diseño acordado: detectar, avisar, confirmar, nunca inferir en silencio.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

from src.dividendos import COLUMNAS_TABLA, descargar_eventos, localizar_fecha_ex
from src.fetch_prices import load_universe, operables

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DESDE, HASTA = pd.Timestamp("2024-06-01"), pd.Timestamp("2026-12-31")
TIPOS = {"accion_local", "accion_sigma"}


def main(confirmar: bool = False) -> int:
    universo = operables(load_universe())
    universo = universo.loc[universo.tipo.isin(TIPOS)]
    precios = pd.read_csv(DATA / "market_prices_daily.csv", parse_dates=["date"])
    aceptados, rechazados = [], []
    for item in universo.itertuples(index=False):
        try:
            eventos = descargar_eventos(item.yahoo_ticker, DESDE, HASTA)
        except Exception as error:
            rechazados.append({"alphadata_ticker": item.alphadata_ticker,
                               "origen": f"descarga fallo: {type(error).__name__}"})
            continue
        serie = precios.loc[precios.alphadata_ticker == item.alphadata_ticker].set_index("date")["close"]
        for evento in eventos:
            calce = localizar_fecha_ex(serie, evento["fecha_declarada"], evento["monto"])
            fila = {"alphadata_ticker": item.alphadata_ticker, "monto": evento["monto"],
                    "fecha_declarada": evento["fecha_declarada"],
                    "origen": "evento del proveedor, fecha confirmada con el cierre crudo"}
            if calce is None:
                rechazados.append({**fila, "fecha_ex": pd.NaT, "error": None})
                continue
            fila.update({k: v for k, v in calce.items() if k != "rechazado"})
            (rechazados if calce["rechazado"] else aceptados).append(fila)
        time.sleep(.35)

    tabla = pd.DataFrame(aceptados, columns=COLUMNAS_TABLA)
    dudosos = pd.DataFrame(rechazados, columns=COLUMNAS_TABLA)
    if len(tabla):
        tabla = tabla.sort_values(["alphadata_ticker", "fecha_ex"])
    if len(dudosos):
        dudosos = dudosos.sort_values(["alphadata_ticker", "fecha_declarada"])

    print(f"dividendos aceptados: {len(tabla)}   por confirmar a mano: {len(dudosos)}")
    if len(tabla):
        desfase = (tabla.fecha_declarada - tabla.fecha_ex).dt.days
        print(f"  error de calce: mediano {tabla.error.median():.2%}   p90 {tabla.error.quantile(.9):.2%}")
        print(f"  desfase entre fecha declarada y fecha ex: mediano {desfase.median():.0f} dias, "
              f"rango {desfase.min():.0f} a {desfase.max():.0f}")
        print(f"  instrumentos cubiertos: {tabla.alphadata_ticker.nunique()} de {len(universo)}")
    if len(dudosos):
        cuenta = dudosos.alphadata_ticker.value_counts().head(8)
        print("  sin calce: " + ", ".join(f"{t} {n}" for t, n in cuenta.items()))
    if not confirmar:
        print("\nEnsayo: no se escribio nada. Repetir con --confirmar.")
        return 0
    tabla.to_csv(DATA / "dividendos.csv", index=False, date_format="%Y-%m-%d")
    dudosos.to_csv(DATA / "dividendos_por_confirmar.csv", index=False, date_format="%Y-%m-%d")
    print(f"\nEscrito: data/dividendos.csv ({len(tabla)}) y "
          f"data/dividendos_por_confirmar.csv ({len(dudosos)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--confirmar" in sys.argv))
