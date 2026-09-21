"""Tablas por nivel de capital, frontera por techo de caída y validación cruzada."""

from __future__ import annotations

import pandas as pd

from research.ponderaciones.estudio import ESQUEMAS, PIEZAS, simular
from research.ponderaciones.piezas import construir

CAPITALES = [8e6, 20e6, 50e6, 100e6]
TECHOS = [.10, .15, .20]
VENTANAS = {"limpia (2025-2026)": (pd.Timestamp("2025-01-02"), pd.Timestamp("2026-09-17")),
            "larga (2021-2026)": (pd.Timestamp("2021-07-08"), pd.Timestamp("2026-09-17"))}


def tabla(navs, ops, etiqueta):
    print(f"\n{'='*84}\nVENTANA {etiqueta}   ({navs.date.min().date()} a {navs.date.max().date()})\n{'='*84}")
    print(f"{'esquema':<26}" + "".join(f"{c/1e6:>10,.0f}M" for c in CAPITALES) + f"{'peor caída':>13}")
    resultados = {}
    for nombre, esquema in ESQUEMAS.items():
        fila, caidas = [], []
        for capital in CAPITALES:
            r = simular(navs, ops, esquema, capital)
            fila.append(r["anual"]); caidas.append(r["peor_caida"])
            resultados[(nombre, capital)] = r
        print(f"{nombre:<26}" + "".join(f"{v:>11.2%}" for v in fila) + f"{min(caidas):>13.1%}")
    return resultados


def frontera(resultados):
    print(f"\n  Mejor esquema por techo de caída y capital:")
    print(f"  {'techo':<8}" + "".join(f"{c/1e6:>28,.0f}M" for c in CAPITALES))
    for techo in TECHOS:
        celdas = []
        for capital in CAPITALES:
            aptos = [(n, r["anual"]) for (n, c), r in resultados.items()
                     if c == capital and r["peor_caida"] >= -techo]
            if not aptos:
                celdas.append("ninguno cumple")
            else:
                mejor = max(aptos, key=lambda x: x[1])
                celdas.append(f"{mejor[0]} {mejor[1]:.1%}")
        print(f"  {techo:<8.0%}" + "".join(f"{c:>29}" for c in celdas))


def validacion(navs, ops, etiqueta):
    print(f"\n  Validación cruzada — {etiqueta}")
    fechas = navs.date
    mitad = fechas.iloc[len(fechas) // 2]
    A = navs[navs.date <= mitad].reset_index(drop=True)
    B = navs[navs.date >= mitad].reset_index(drop=True)
    retornos = {"A": A.set_index("date")[PIEZAS].pct_change(fill_method=None).dropna(how="all"),
                "B": B.set_index("date")[PIEZAS].pct_change(fill_method=None).dropna(how="all")}
    paneles = {"A": A, "B": B}
    ordenes = {}
    for ajuste, medida in (("A", "B"), ("B", "A")):
        print(f"    pesos de {ajuste} ({paneles[ajuste].date.min().date()}..{paneles[ajuste].date.max().date()}) "
              f"medidos en {medida}, capital $20M:")
        puntajes = []
        for nombre, esquema in ESQUEMAS.items():
            fijos = esquema(retornos[ajuste])
            r = simular(paneles[medida], ops, esquema, 20e6, pesos_fijos=fijos)
            puntajes.append((nombre, r["anual"], r["peor_caida"]))
        for n, a, d in sorted(puntajes, key=lambda x: -x[1]):
            print(f"      {n:<26}{a:>8.2%}{d:>9.1%}")
        ordenes[f"{ajuste}-{medida}"] = [n for n, _, _ in sorted(puntajes, key=lambda x: -x[1])]
    a, b = ordenes["A-B"], ordenes["B-A"]
    coinciden = a[0] == b[0]
    print(f"    primero en A->B: {a[0]}")
    print(f"    primero en B->A: {b[0]}")
    print(f"    ¿coincide el orden? {'sí' if a == b else 'NO'}   ¿coincide el primero? {'sí' if coinciden else 'NO'}")
    return a, b


def referencia_maxima(navs, ops):
    """Sólo como referencia de cuánto deja sobre la mesa cualquier regla."""
    mejor = None
    for s in range(0, 101, 10):
        for d in range(0, 101 - s, 10):
            for g in range(0, 101 - s - d, 10):
                o = 100 - s - d - g
                pesos = pd.Series([s, d, g, o], index=PIEZAS) / 100
                r = simular(navs, ops, None, 20e6, pesos_fijos=pesos)
                if mejor is None or r["anual"] > mejor[1]:
                    mejor = (dict(pesos), r["anual"], r["peor_caida"])
    return mejor


def main() -> int:
    for etiqueta, (inicio, fin) in VENTANAS.items():
        print(f"\nReconstruyendo piezas para la ventana {etiqueta}...")
        navs, ops = construir(inicio, fin)
        print(f"  rotación medida: " + ", ".join(f"{k} {v:.0f} op/año" for k, v in ops.items() if v))
        resultados = tabla(navs, ops, etiqueta)
        frontera(resultados)
        validacion(navs, ops, etiqueta)
        mejor = referencia_maxima(navs, ops)
        print(f"\n  Referencia (no es una propuesta): la mejor combinación fija en rejilla de 10% "
              f"habría dado {mejor[1]:.2%} anual con caída {mejor[2]:.1%}")
        print(f"    {', '.join(f'{k} {v:.0%}' for k, v in mejor[0].items())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
