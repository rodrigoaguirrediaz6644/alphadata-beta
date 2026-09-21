"""Los cinco esquemas de concentración, con diagnósticos y costo."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.fetch_prices import load_universe
from src.strategy_engine import validate_recommendations
from research.concentracion.diagnostico import carteras_mensuales, solape
from research.ponderaciones.estudio import PIEZAS, simular
from research.ponderaciones.piezas import construir
from research.ponderaciones.costo_reparto import costo_anual

ROOT = Path(__file__).resolve().parents[2]
CAPITAL = 20e6
VENTANAS = {"limpia (2025-2026)": (pd.Timestamp("2025-01-02"), pd.Timestamp("2026-09-17")),
            "larga (2021-2026)": (pd.Timestamp("2021-07-08"), pd.Timestamp("2026-09-17"))}

ESQUEMAS = {
    "1 actual: cuatro al 25%":      {"Sigma-6": .25,  "Delta-12": .25,  "Gamma-6": .25,  "Oro": .25},
    "2 sin Sigma-6, tres parejas":  {"Sigma-6": 0,    "Delta-12": 1/3,  "Gamma-6": 1/3,  "Oro": 1/3},
    "3 sin Delta-12, tres parejas": {"Sigma-6": 1/3,  "Delta-12": 0,    "Gamma-6": 1/3,  "Oro": 1/3},
    "4 parejo por mercado":         {"Sigma-6": 1/6,  "Delta-12": 1/6,  "Gamma-6": 1/3,  "Oro": 1/3},
    "5 Chile al 40%":               {"Sigma-6": .20,  "Delta-12": .20,  "Gamma-6": .30,  "Oro": .30},
}

MARGINALES = {
    "Delta-12 + Gamma-6 + Oro":            {"Sigma-6": 0,   "Delta-12": 1/3, "Gamma-6": 1/3, "Oro": 1/3},
    "  + Sigma-6 (cuatro al 25%)":         {"Sigma-6": .25, "Delta-12": .25, "Gamma-6": .25, "Oro": .25},
    "Sigma-6 + Gamma-6 + Oro":             {"Sigma-6": 1/3, "Delta-12": 0,   "Gamma-6": 1/3, "Oro": 1/3},
    "  + Delta-12 (cuatro al 25%)":        {"Sigma-6": .25, "Delta-12": .25, "Gamma-6": .25, "Oro": .25},
}


def bloque(navs, ops, etiqueta):
    print(f"\n{'='*80}\nESQUEMAS — ventana {etiqueta}\n{'='*80}")
    print(f"{'esquema':<32}{'anual':>9}{'peor caída':>12}{'costo/año':>12}{'% cap':>8}{'Chile':>8}")
    salida = {}
    for nombre, pesos in ESQUEMAS.items():
        r = simular(navs, ops, None, CAPITAL, pesos_fijos=pd.Series(pesos))
        c = costo_anual(pesos, CAPITAL)["total"]
        chile = pesos["Sigma-6"] + pesos["Delta-12"]
        salida[nombre] = {**r, "costo": c}
        print(f"{nombre:<32}{r['anual']:>9.2%}{r['peor_caida']:>12.1%}{c:>12,.0f}{c/CAPITAL:>8.2%}{chile:>8.0%}")
    return salida


def marginal(navs, ops, etiqueta):
    print(f"\n  Aporte marginal de la segunda chilena — {etiqueta}")
    print(f"  {'cartera':<34}{'anual':>9}{'peor caída':>12}{'costo/año':>12}")
    previo = None
    for nombre, pesos in MARGINALES.items():
        r = simular(navs, ops, None, CAPITAL, pesos_fijos=pd.Series(pesos))
        c = costo_anual(pesos, CAPITAL)["total"]
        extra = ""
        if nombre.startswith("  +") and previo:
            extra = (f"   ({(r['anual']-previo['anual'])*100:+.2f}pp, "
                         f"caída {(r['peor_caida']-previo['peor_caida'])*100:+.1f}pp, ${c-previo['costo']:+,.0f})")
        print(f"  {nombre:<34}{r['anual']:>9.2%}{r['peor_caida']:>12.1%}{c:>12,.0f}{extra}")
        previo = {**r, "costo": c}


def main() -> int:
    u = load_universe()
    p = pd.read_csv(ROOT / "data" / "market_prices_daily.csv", parse_dates=["date"])
    raw = pd.read_csv(ROOT / "data" / "recommendations_input.csv", dtype=str).fillna("")
    valid, _ = validate_recommendations(raw, set(u.alphadata_ticker))

    for etiqueta, (inicio, fin) in VENTANAS.items():
        print(f"\nReconstruyendo {etiqueta}...")
        navs, ops = construir(inicio, fin)
        datos = navs.set_index("date")[PIEZAS].apply(pd.to_numeric, errors="coerce")
        mensual = datos.resample("ME").last().pct_change(fill_method=None).dropna(how="all")

        print(f"\n{'='*80}\nDIAGNÓSTICO — ventana {etiqueta}\n{'='*80}")
        c = mensual[["Sigma-6", "Delta-12"]].dropna().corr().iloc[0, 1]
        print(f"  correlación de retornos mensuales Sigma-6 / Delta-12: {c:.3f}  ({len(mensual.dropna())} meses)")
        otras = [("Sigma-6", "Gamma-6"), ("Sigma-6", "Oro"), ("Delta-12", "Gamma-6"), ("Delta-12", "Oro"), ("Gamma-6", "Oro")]
        print("  para comparar: " + "  ".join(f"{a[:3]}/{b[:3]} {mensual[[a,b]].dropna().corr().iloc[0,1]:.2f}" for a, b in otras))

        carteras = carteras_mensuales(p, u, valid, inicio, fin)
        so = solape(carteras)
        print(f"\n  solape de carteras en {len(so)} revisiones:")
        print(f"    nombres en común: media {so.n_comunes.mean():.1f}   de {so.n_sigma.mean():.1f} de Sigma-6 "
              f"y {so.n_delta.mean():.1f} de Delta-12")
        print(f"    Jaccard medio: {so.jaccard.mean():.2f}   fracción de Sigma-6 que también está en Delta-12: "
              f"{so.frac_sigma_en_delta.mean():.0%}")
        print(f"    peso solapado medio: {so.peso_comun.mean():.1%} de la cartera")
        print(f"    caja: Sigma-6 media {so.caja_sigma.mean():.0%} (rango {so.caja_sigma.min():.0%}-{so.caja_sigma.max():.0%}), "
              f"Delta-12 media {so.caja_delta.mean():.0%}")

        for nombre in ["Sigma-6", "Delta-12"]:
            s = datos[nombre].dropna()
            d = s / s.cummax() - 1
            print(f"    mínimo de {nombre}: {d.min():.1%} el {d.idxmin().date()}")

        bloque(navs, ops, etiqueta)
        marginal(navs, ops, etiqueta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
