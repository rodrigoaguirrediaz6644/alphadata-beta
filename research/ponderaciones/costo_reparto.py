"""¿Qué reparto de $20 millones minimiza el costo en pesos?

El mínimo de $1.990 es un peaje fijo por operación, no proporcional al capital.
Delta-12 hace sus ~78 operaciones al año tenga el tamaño que tenga, así que el
peso marginal en una pieza chilena es mucho más barato que el peso promedio:
una vez pagado el peaje, agregar capital no agrega costo hasta que la operación
supera $1.114.846.

Esto es un argumento de costo, no de retorno, y no depende del backtest.
"""

from __future__ import annotations

import pandas as pd

MINIMO, TASA_CL, TASA_US = 1990, .001785, .001
UMBRAL = MINIMO / TASA_CL
PIEZAS = ["Sigma-6", "Delta-12", "Gamma-6", "Oro"]
POSICIONES = {"Sigma-6": 10, "Delta-12": 8, "Gamma-6": 6, "Oro": 1}
OPS = {"Sigma-6": 49, "Delta-12": 78, "Gamma-6": 24, "Oro": 0}  # Gamma-6 rota mensual, ~2 nombres
CHILENAS = {"Sigma-6", "Delta-12"}


def costo_anual(pesos: dict, capital: float) -> dict:
    """Costo de la rotación interna de cada pieza, en pesos al año."""
    detalle = {}
    for pieza in PIEZAS:
        w = pesos.get(pieza, 0)
        if w <= 0 or not OPS[pieza]:
            detalle[pieza] = 0.0
            continue
        monto = w * capital / POSICIONES[pieza]
        tasa = TASA_CL if pieza in CHILENAS else TASA_US
        por_operacion = max(MINIMO, monto * tasa) if pieza in CHILENAS else monto * tasa
        detalle[pieza] = OPS[pieza] * por_operacion
    detalle["total"] = sum(v for k, v in detalle.items() if k != "total")
    return detalle


def rejilla(capital: float, paso: int = 5, minimo_por_pieza: int = 5):
    """Todos los repartos en múltiplos de `paso`%, con un piso por pieza."""
    salidas = []
    for s in range(minimo_por_pieza, 101, paso):
        for d in range(minimo_por_pieza, 101 - s, paso):
            for g in range(minimo_por_pieza, 101 - s - d, paso):
                o = 100 - s - d - g
                if o < minimo_por_pieza:
                    continue
                pesos = {"Sigma-6": s / 100, "Delta-12": d / 100, "Gamma-6": g / 100, "Oro": o / 100}
                salidas.append((pesos, costo_anual(pesos, capital)["total"]))
    return salidas


def main() -> int:
    capital = 20e6
    print(f"Umbral donde el porcentual alcanza al mínimo: ${UMBRAL:,.0f} por operación")
    print(f"  Delta-12 (8 posiciones) es eficiente sobre ${UMBRAL*8:,.0f} en la pieza")
    print(f"  Sigma-6 (10 posiciones) es eficiente sobre ${UMBRAL*10:,.0f} en la pieza")
    print(f"  suma de los dos umbrales: ${UMBRAL*18:,.0f}  —  con ${capital:,.0f} no alcanza para los dos\n")

    print(f"=== costo anual de la rotación interna, ${capital/1e6:.0f} millones ===")
    print(f"{'reparto':<34}{'Sigma-6':>11}{'Delta-12':>11}{'Gamma-6':>10}{'total':>12}{'% capital':>11}")
    esquemas = {
        "peso igual 25/25/25/25": {"Sigma-6": .25, "Delta-12": .25, "Gamma-6": .25, "Oro": .25},
        "inverso a volatilidad*": {"Sigma-6": .27, "Delta-12": .24, "Gamma-6": .17, "Oro": .32},
        "una chilena eficiente (D-12)": {"Sigma-6": .10, "Delta-12": .45, "Gamma-6": .20, "Oro": .25},
        "una chilena eficiente (S-6)": {"Sigma-6": .56, "Delta-12": .09, "Gamma-6": .10, "Oro": .25},
        "sin piezas chilenas": {"Sigma-6": 0, "Delta-12": 0, "Gamma-6": .50, "Oro": .50},
    }
    for nombre, pesos in esquemas.items():
        c = costo_anual(pesos, capital)
        print(f"{nombre:<34}{c['Sigma-6']:>11,.0f}{c['Delta-12']:>11,.0f}{c['Gamma-6']:>10,.0f}"
              f"{c['total']:>12,.0f}{c['total']/capital:>11.2%}")

    print(f"\n=== la rejilla: los cinco repartos más baratos con al menos 5% en cada pieza ===")
    puntos = sorted(rejilla(capital), key=lambda x: x[1])
    print(f"{'S-6':>6}{'D-12':>6}{'G-6':>6}{'Oro':>6}{'costo':>12}{'% capital':>11}")
    for pesos, costo in puntos[:5]:
        print("".join(f"{pesos[p]:>6.0%}" for p in PIEZAS) + f"{costo:>12,.0f}{costo/capital:>11.2%}")
    print(f"  ... y los cinco más caros:")
    for pesos, costo in puntos[-5:]:
        print("".join(f"{pesos[p]:>6.0%}" for p in PIEZAS) + f"{costo:>12,.0f}{costo/capital:>11.2%}")
    print(f"\n  rango de costo en toda la rejilla: ${puntos[0][1]:,.0f} a ${puntos[-1][1]:,.0f} "
          f"({(puntos[-1][1]-puntos[0][1])/capital:.2%} del capital)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
