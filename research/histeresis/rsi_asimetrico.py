"""El RSI como filtro de entrada, no como condición de permanencia.

La histéresis sobre el ranking no baja la rotación porque no es ahí donde se
origina: de las 181 salidas de Delta-12 en cinco años, **134 son forzadas** por
dejar de cumplir la elegibilidad y sólo 47 son desplazamientos. Y de las
forzadas, 73 —el 54%— son por `RSI14 superior a 65`.

Dicho de otro modo: Delta-12 es una estrategia de momentum que vende sus
ganadoras justo cuando se ponen fuertes, y las vuelve a comprar cuando se
enfrían. El RSI está actuando como condición de permanencia cuando su sentido
natural es evitar comprar algo ya sobrecomprado.

La variante asimétrica aplica el RSI sólo a las candidatas nuevas. Una posición
vigente se mantiene mientras siga cumpliendo momentum, SMA200 y liquidez.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.fetch_prices import load_universe
from src.strategy_engine import capped_pro_rata, delta12
from research.histeresis.estudio import INICIO, FIN, POSICIONES, TOPE, COSTO, por_banda, simular

ROOT = Path(__file__).resolve().parents[2]
RSI_MAXIMO = 65


def auditorias_completas(precios, universo):
    ses = pd.DatetimeIndex(sorted(precios.loc[precios.date.between(INICIO, FIN), "date"].unique()))
    revisiones = pd.Series(ses, index=ses).groupby(ses.to_period("M")).max().tolist()
    salida = {}
    for fecha in revisiones:
        _, audit = delta12(precios, universo, pd.Timestamp(fecha))
        if len(audit):
            salida[pd.Timestamp(fecha)] = audit.set_index("ticker")
    return salida


def _sin_rsi(audit):
    """Elegible por todo menos el RSI."""
    return (audit.momentum_12_1 > 0) & (audit.adjusted_close > audit.sma200) & \
           (audit.liquidity_percentile >= 20) & (audit.history_rows >= 252)


def rsi_solo_al_entrar(banda=0):
    def elegir(audit, vigentes):
        base = _sin_rsi(audit)
        puede_entrar = base & (audit.rsi14 <= RSI_MAXIMO)
        puede_quedarse = base
        orden = audit.momentum_12_1.sort_values(ascending=False)
        tolerados = set(orden[puede_quedarse.reindex(orden.index, fill_value=False)].head(POSICIONES + banda).index) if banda else None
        seleccion = [t for t in orden.index if t in vigentes and puede_quedarse.get(t, False)
                     and (tolerados is None or t in tolerados)][:POSICIONES]
        for t in orden.index:
            if len(seleccion) >= POSICIONES:
                break
            if t not in seleccion and puede_entrar.get(t, False):
                seleccion.append(t)
        return seleccion
    return elegir


def rsi_con_banda(salida=75):
    """Entra con RSI <= 65, sale recién sobre `salida`.

    Es la histéresis aplicada a la variable que de verdad manda la rotación, en
    vez de al ranking. Conserva el sentido del filtro —no comprar algo ya
    sobrecomprado— sin expulsar a una ganadora por cruzar el umbral por un pelo.
    """
    def elegir(audit, vigentes):
        base = _sin_rsi(audit)
        puede_entrar = base & (audit.rsi14 <= RSI_MAXIMO)
        puede_quedarse = base & (audit.rsi14 <= salida)
        orden = audit.momentum_12_1.sort_values(ascending=False)
        seleccion = [t for t in orden.index if t in vigentes and puede_quedarse.get(t, False)][:POSICIONES]
        for t in orden.index:
            if len(seleccion) >= POSICIONES:
                break
            if t not in seleccion and puede_entrar.get(t, False):
                seleccion.append(t)
        return seleccion
    return elegir


def oficial(audit, vigentes):
    elegibles = audit.loc[audit.eligible, "momentum_12_1"].sort_values(ascending=False)
    return list(elegibles.head(POSICIONES).index)


def main() -> int:
    u = load_universe()
    p = pd.read_csv(ROOT / "data" / "market_prices_daily.csv", parse_dates=["date"])
    locales = set(u.loc[u.tipo == "accion_local", "alphadata_ticker"])
    panel = p[p.alphadata_ticker.isin(locales) & p.date.between(INICIO, FIN)].pivot_table(
        index="date", columns="alphadata_ticker", values="adjusted_close", aggfunc="last").sort_index().ffill(limit=3)
    print("Auditorías mensuales...")
    audits = auditorias_completas(p, u)
    print(f"  {len(audits)} revisiones")

    variantes = [("oficial", oficial),
                 ("RSI sólo al entrar", rsi_solo_al_entrar()),
                 ("RSI salida 70", rsi_con_banda(70)),
                 ("RSI salida 75", rsi_con_banda(75)),
                 ("RSI salida 80", rsi_con_banda(80))]

    mitad = panel.index[len(panel) // 2]
    for etiqueta, desde, hasta in [("completa", panel.index[0], panel.index[-1]),
                                   ("1ª mitad", panel.index[0], mitad),
                                   ("2ª mitad", mitad, panel.index[-1])]:
        sub = panel.loc[desde:hasta]
        sub_audits = {k: v for k, v in audits.items() if desde <= k <= hasta}
        print(f"\n=== {etiqueta} ({desde.date()} a {hasta.date()}) ===")
        print(f"{'variante':<24}{'base 100':>10}{'anual':>8}{'peor caída':>12}{'ops/año':>9}{'vs oficial':>12}")
        referencia = None
        for nombre, elegir in variantes:
            r = simular(sub, sub_audits, elegir)
            referencia = referencia or r
            print(f"{nombre:<24}{r['base_100']:>10,.1f}{r['anual']:>8.1%}{r['peor_caida']:>12.1%}"
                  f"{r['ops_anio']:>9.0f}{(r['anual'] - referencia['anual']) * 100:>+11.2f}pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
