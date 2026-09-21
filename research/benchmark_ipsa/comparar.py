"""Compara la reconstrucción de las estrategias contra el MSCI IPSA Gross.

    PYTHONPATH=. python -m research.benchmark_ipsa.comparar <archivo del índice>

Todo se mide en la misma ventana y con la misma base, que es el punto: la
comparación anterior usaba una serie rota y el informe terminaba suprimiéndola.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.benchmark_ipsa import leer

ROOT = Path(__file__).resolve().parents[2]
SERIES = ["Conjunto AlphaData", "Sigma-6", "Delta-12", "Gamma-6", "Oro"]


def metricas(serie: pd.Series) -> dict:
    anios = max((serie.index[-1] - serie.index[0]).days / 365.25, 1 / 365.25)
    base = serie.iloc[-1] / serie.iloc[0] * 100
    return {"base_100": base, "anual": (base / 100) ** (1 / anios) - 1, "peor_caida": float((serie / serie.cummax() - 1).min())}


def main(ruta: str) -> int:
    indice = leer(ruta)
    nav = pd.read_csv(ROOT / "data" / "historical_model_nav.csv", parse_dates=["date"]).set_index("date")
    base, fin = nav.index.min(), nav.index.max()
    tramo = indice.loc[:fin]
    if indice.loc[:base].empty or tramo.empty:
        print("El índice no cubre la ventana de la reconstrucción.")
        return 1
    mercado = pd.Series(tramo.loc[base:].to_numpy(), index=tramo.loc[base:].index)
    m = metricas(mercado)

    print(f"Ventana: {base.date()} .. {fin.date()}   (base 100 en la primera)")
    print(f"{'serie':<22}{'base 100':>11}{'anual':>9}{'peor caída':>12}{'vs mercado':>12}")
    filas = []
    for nombre in SERIES:
        if nombre not in nav:
            continue
        serie = pd.to_numeric(nav[nombre], errors="coerce").dropna()
        if serie.empty:
            continue
        r = metricas(serie)
        filas.append({"serie": nombre, **r, "vs_mercado": r["base_100"] - m["base_100"]})
        print(f"{nombre:<22}{r['base_100']:>11,.1f}{r['anual']:>9.1%}{r['peor_caida']:>12.1%}{r['base_100'] - m['base_100']:>+12,.1f}")
    filas.append({"serie": "MSCI IPSA Gross", **m, "vs_mercado": 0.0})
    print(f"{'MSCI IPSA Gross':<22}{m['base_100']:>11,.1f}{m['anual']:>9.1%}{m['peor_caida']:>12.1%}{0:>+12,.1f}")
    pd.DataFrame(filas).to_csv(Path(__file__).parent / "comparacion.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
