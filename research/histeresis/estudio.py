"""¿Cuánta rotación se puede quitar a Delta-12 sin perder retorno?

Delta-12 hace 78 operaciones al año con ocho posiciones: casi toda la cartera
rota cada mes. A capital bajo eso no es un detalle de costo, es lo que decide
si la estrategia sirve: con dos millones por pieza, la tarifa mínima de $1.990
se lleva 7,73% anual, más que toda la ventaja sobre el mercado.

Se prueban dos formas de histéresis, las dos sobre la misma regla de siempre:

- **Margen de puntaje.** Una candidata sólo desplaza a una posición vigente si
  su momentum la supera por más de `margen` puntos porcentuales.
- **Banda de ranking.** Una posición vigente se conserva mientras siga entre
  las primeras `8 + banda`, en vez de exigirle estar entre las ocho.

Se evalúan en la muestra completa y en dos submuestras, como cualquier regla
nueva. El costo incluye el porcentual, que es el que el backtest ya modelaba.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.fetch_prices import load_universe
from src.strategy_engine import capped_pro_rata, delta12

ROOT = Path(__file__).resolve().parents[2]
INICIO, FIN = pd.Timestamp("2021-07-01"), pd.Timestamp("2026-09-17")
POSICIONES, TOPE, COSTO = 8, .15, .001785


def auditorias(precios, universo, inicio=INICIO, fin=FIN):
    """El cálculo caro se hace una vez: un audit por revisión mensual."""
    ses = pd.DatetimeIndex(sorted(precios.loc[precios.date.between(inicio, fin), "date"].unique()))
    revisiones = pd.Series(ses, index=ses).groupby(ses.to_period("M")).max().tolist()
    salida = {}
    for fecha in revisiones:
        _, audit = delta12(precios, universo, pd.Timestamp(fecha))
        if len(audit):
            salida[pd.Timestamp(fecha)] = audit.loc[audit.eligible, ["ticker", "momentum_12_1"]].set_index("ticker")["momentum_12_1"].sort_values(ascending=False)
    return salida


def sin_histeresis(elegibles, vigentes):
    return list(elegibles.head(POSICIONES).index)


def por_margen(margen):
    def elegir(elegibles, vigentes):
        dentro = [t for t in elegibles.index if t in vigentes][:POSICIONES]
        fuera = [t for t in elegibles.index if t not in vigentes]
        seleccion = list(dentro)
        for t in fuera:
            if len(seleccion) < POSICIONES:
                seleccion.append(t)
            else:
                peor = min(seleccion, key=lambda x: elegibles[x])
                if elegibles[t] > elegibles[peor] + margen:
                    seleccion.remove(peor); seleccion.append(t)
                else:
                    break
        return seleccion[:POSICIONES]
    return elegir


def por_banda(banda):
    def elegir(elegibles, vigentes):
        tolerados = set(elegibles.head(POSICIONES + banda).index)
        seleccion = [t for t in elegibles.index if t in vigentes and t in tolerados][:POSICIONES]
        for t in elegibles.index:
            if len(seleccion) >= POSICIONES:
                break
            if t not in seleccion:
                seleccion.append(t)
        return seleccion
    return elegir


def simular(panel, audits, elegir, costo=COSTO):
    pesos, nav, filas, previo, operaciones = {}, 100.0, [], None, 0
    revisiones = set(audits)
    for s in panel.index:
        if previo is not None:
            paso = sum(w * (panel.at[s, t] / panel.at[previo, t] - 1) for t, w in pesos.items()
                       if t in panel and pd.notna(panel.at[previo, t]) and pd.notna(panel.at[s, t]) and panel.at[previo, t] > 0)
            nav *= 1 + paso
        if s in revisiones:
            elegidos = elegir(audits[s], set(pesos))
            nuevos = dict(capped_pro_rata(pd.Series(1.0, index=elegidos), TOPE)) if elegidos else {}
            operaciones += len(set(nuevos) - set(pesos)) + len(set(pesos) - set(nuevos))
            rot = sum(abs(nuevos.get(t, 0) - pesos.get(t, 0)) for t in set(pesos) | set(nuevos))
            caja = abs((1 - sum(nuevos.values())) - (1 - sum(pesos.values())))
            nav *= 1 - .5 * (rot + caja) * costo
            pesos = nuevos
        filas.append({"date": s, "nav": nav}); previo = s
    serie = pd.DataFrame(filas).set_index("date")["nav"]
    anios = (serie.index[-1] - serie.index[0]).days / 365.25
    return {"base_100": serie.iloc[-1], "anual": (serie.iloc[-1] / 100) ** (1 / anios) - 1,
            "peor_caida": float((serie / serie.cummax() - 1).min()),
            "ops_anio": operaciones / anios, "serie": serie}


def main() -> int:
    u = load_universe()
    p = pd.read_csv(ROOT / "data" / "market_prices_daily.csv", parse_dates=["date"])
    locales = set(u.loc[u.tipo == "accion_local", "alphadata_ticker"])
    panel = p[p.alphadata_ticker.isin(locales) & p.date.between(INICIO, FIN)].pivot_table(
        index="date", columns="alphadata_ticker", values="adjusted_close", aggfunc="last").sort_index().ffill(limit=3)
    print(f"Auditorías mensuales de {INICIO.date()} a {FIN.date()}...")
    audits = auditorias(p, u)
    print(f"  {len(audits)} revisiones")

    variantes = [("sin histéresis", sin_histeresis)]
    variantes += [(f"margen {m:.0%}", por_margen(m)) for m in (.02, .05, .10, .15, .20)]
    variantes += [(f"banda +{b}", por_banda(b)) for b in (2, 4, 6)]

    mitad = panel.index[len(panel) // 2]
    tramos = [("completa", panel.index[0], panel.index[-1]),
              ("1ª mitad", panel.index[0], mitad), ("2ª mitad", mitad, panel.index[-1])]
    for etiqueta, desde, hasta in tramos:
        sub = panel.loc[desde:hasta]
        sub_audits = {k: v for k, v in audits.items() if desde <= k <= hasta}
        print(f"\n=== {etiqueta} ({desde.date()} a {hasta.date()}) ===")
        print(f"{'variante':<18}{'base 100':>10}{'anual':>8}{'peor caída':>12}{'ops/año':>9}{'vs sin hist.':>13}")
        referencia = None
        for nombre, elegir in variantes:
            r = simular(sub, sub_audits, elegir)
            if referencia is None:
                referencia = r
            delta = (r["anual"] - referencia["anual"]) * 100
            print(f"{nombre:<18}{r['base_100']:>10,.1f}{r['anual']:>8.1%}{r['peor_caida']:>12.1%}"
                  f"{r['ops_anio']:>9.0f}{delta:>+12.2f}pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
