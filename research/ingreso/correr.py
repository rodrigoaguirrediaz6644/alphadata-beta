"""Ejecuta las tres mediciones del protocolo de ingreso."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.fetch_prices import load_universe
from research.ingreso.protocolo import (HORIZONTES, comparar_entradas, costo_entrada,
                                        dispersion_escalonada, historia_de_carteras,
                                        tenencia_residual)

ROOT = Path(__file__).resolve().parents[2]
INICIO, FIN = pd.Timestamp("2021-07-08"), pd.Timestamp("2026-09-17")


def bloque_entradas(tabla, etiqueta):
    print(f"\n  --- {etiqueta}  ({len(tabla)} fechas de ingreso) ---")
    print(f"  {'horizonte':<12}{'completa':>12}{'sólo las que van abajo':>26}{'diferencia':>13}{'n medio':>10}")
    orden = []
    for h in HORIZONTES:
        a = tabla[f"completa {h}"].dropna()
        b = tabla[f"perdedoras {h}"].dropna()
        comun = a.index.intersection(b.index)
        a, b = a.loc[comun], b.loc[comun]
        if a.empty:
            continue
        print(f"  {h:<12}{a.mean():>12.2%}{b.mean():>26.2%}{(b.mean()-a.mean())*100:>+12.2f}pp"
              f"{tabla.loc[comun,'n_perdedoras'].mean():>10.1f}")
        orden.append("perdedoras" if b.mean() > a.mean() else "completa")
    return orden


def main() -> int:
    u = load_universe()
    p = pd.read_csv(ROOT / "data" / "market_prices_daily.csv", parse_dates=["date"])
    print("Reconstruyendo el historial de carteras de Delta-12...")
    historia, panel = historia_de_carteras(p, u, INICIO, FIN)
    print(f"  {len(historia)} revisiones mensuales")

    print("\n" + "=" * 78)
    print("1. CARTERA COMPLETA CONTRA SÓLO LAS QUE VAN BAJO SU PRECIO DE ENTRADA")
    print("=" * 78)
    tabla = comparar_entradas(historia, panel)
    ordenes = {"completa": bloque_entradas(tabla, "muestra completa")}
    mitad = len(tabla) // 2
    ordenes["A"] = bloque_entradas(tabla.iloc[:mitad], "1ª mitad")
    ordenes["B"] = bloque_entradas(tabla.iloc[mitad:], "2ª mitad")
    print(f"\n  ¿gana la misma variante en las dos mitades? "
          f"{'sí' if ordenes['A'] == ordenes['B'] else 'NO — no se puede distinguir'}")
    print(f"    1ª mitad: {ordenes['A']}")
    print(f"    2ª mitad: {ordenes['B']}")

    print("\n" + "=" * 78)
    print("2. ESCALONAMIENTO: DISPERSIÓN A 12 MESES Y COSTO")
    print("=" * 78)
    disp = dispersion_escalonada(panel, historia)
    print(f"  {'esquema':<14}{'media':>10}{'desv. típica':>14}{'p10':>9}{'p90':>9}{'rango p10-p90':>15}")
    for nombre, serie in disp.items():
        if serie.empty:
            continue
        print(f"  {nombre:<14}{serie.mean():>10.2%}{serie.std():>14.2%}{serie.quantile(.1):>9.2%}"
              f"{serie.quantile(.9):>9.2%}{(serie.quantile(.9)-serie.quantile(.1))*100:>14.1f}pp")

    print(f"\n  Costo de entrada a $20M totales, por estrategia y número de tramos:")
    print(f"  {'estrategia':<12}{'1 tramo':>12}{'4 tramos':>12}{'8 tramos':>12}{'12 tramos':>12}")
    for nombre, posiciones, capital, tasa, minimo in [
            ("Delta-12", 8, 5e6, .001785, 1990), ("Sigma-6", 10, 5e6, .001785, 1990),
            ("Gamma-6", 6, 5e6, .001, 0), ("Oro", 1, 5e6, .001, 0)]:
        fila = [costo_entrada(capital, posiciones, n, tasa, minimo) for n in (1, 4, 8, 12)]
        print(f"  {nombre:<12}" + "".join(f"{v:>12,.0f}" for v in fila))

    print("\n" + "=" * 78)
    print("3. VIDA RESTANTE DE UNA POSICIÓN TOMADA A MITAD DE CAMINO")
    print("=" * 78)
    restos = tenencia_residual(historia)
    print(f"  observaciones: {len(restos)}")
    print(f"  media {restos.mean():.1f} meses   mediana {restos.median():.0f}   "
          f"p25 {restos.quantile(.25):.0f}   p75 {restos.quantile(.75):.0f}")
    print(f"  se vende en la revisión siguiente: {(restos == 0).mean():.0%} de las veces")
    costo_pos = max(1990, (5e6 / 8) * .001785)
    print(f"\n  A $5M en Delta-12 cada posición cuesta ${costo_pos:,.0f} al entrar.")
    print(f"  Repartido sobre la vida restante media son ${costo_pos/max(restos.mean(),1):,.0f} por mes mantenido;")
    print(f"  sobre las que se venden en la revisión siguiente, ${costo_pos:,.0f} por un solo mes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
