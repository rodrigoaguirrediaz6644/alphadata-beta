"""Cuatro piezas contra tres, en pesos, sobre $20 millones.

La decision de si Sigma-6 se queda hay que verla en pesos y no en Sharpe.

- **A** cuatro piezas al 25%: $5.000.000 cada una, con Sigma-6 tal como esta
  hoy. Es lo que existe si no se cambia nada.
- **B** tres piezas en tercios: $6.666.667 cada una, sin Sigma-6.
- **C** control: sin Sigma-6 pero dejando el oro en 25% y repartiendo el cuarto
  de Sigma-6 entre las dos de acciones. Delta-12 37,5%, Gamma-6 37,5%, Oro 25%.

C importa porque B no aisla el efecto de sacar Sigma-6: al pasar a tercios el
oro sube de 25% a 33%, y eso cambia el perfil por una razon que no tiene nada
que ver con Sigma-6. C mantiene el oro donde esta y reparte solo el cuarto que
queda libre.

**El capital por pieza cambia entre carteras, y eso no es cosmetico**: con
minimo de $999,99 por operacion, una pieza de $6.666.667 paga proporcionalmente
menos que una de $5.000.000. Cada pieza se corre con el capital que le toca en
su cartera.

Reglas de produccion tal como estan: pesos que corren, solo entradas y salidas,
entradas financiadas con lo que liberan las salidas a prorrata con tope en el
peso de referencia y el resto a caja, limite de concentracion del 25% por
posicion sobre su propia pieza. Caja a 0%.
"""
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from src.fetch_prices import load_universe
from src.nav_historico import _reasignar
from src.strategy_engine import delta12, gamma6, sigma6, to_clp

ZIP = ("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
       "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/corredoras/data/"
       "final_validated_recommendations.csv")
INICIO, CORTE, FIN = pd.Timestamp("2021-07-08"), pd.Timestamp("2024-01-01"), pd.Timestamp("2026-07-15")
TASA_CL, MIN_CL, TASA_US = .001785, 999.99, .001
TOTAL = 20_000_000.

CARTERAS = {
    "A  cuatro piezas al 25%": {"Delta-12": .25, "Gamma-6": .25, "Oro": .25, "Sigma-6": .25},
    "B  tres piezas en tercios": {"Delta-12": 1 / 3, "Gamma-6": 1 / 3, "Oro": 1 / 3},
    "C  control, oro en 25%": {"Delta-12": .375, "Gamma-6": .375, "Oro": .25},
}


def correr(panel, sesiones, objetivos, capital, tasa, minimo):
    pesos, caja, valor = {}, 1., 100.
    por_fecha, filas = dict(objetivos), []
    anterior = None
    for s in sesiones:
        if anterior is None:
            filas.append((s, valor)); anterior = s; continue
        r = {t: panel.at[s, t] / panel.at[anterior, t] - 1 for t in pesos
             if t in panel.columns and pd.notna(panel.at[anterior, t])
             and pd.notna(panel.at[s, t]) and panel.at[anterior, t] > 0}
        dia = sum(w * r.get(t, 0.) for t, w in pesos.items())
        valor *= 1 + dia
        if pesos:
            f = 1 + dia
            pesos = {t: w * (1 + r.get(t, 0.)) / f for t, w in pesos.items()}
            caja /= f
        if s in por_fecha:
            nuevos, nueva_caja = _reasignar(pesos, caja, por_fecha[s])
            cartera, costo = valor / 100 * capital, 0.
            for t in set(pesos) | set(nuevos):
                monto = abs(nuevos.get(t, 0.) - pesos.get(t, 0.)) * cartera
                if monto > 1:
                    costo += max(tasa * monto, minimo)
            valor *= 1 - costo / cartera if cartera > 0 else 1
            pesos, caja = nuevos, nueva_caja
        filas.append((s, valor)); anterior = s
    return pd.Series(dict(filas))


def combinar(series: dict[str, pd.Series], pesos: dict[str, float]) -> pd.Series:
    """Conjunto con pesos fijos, reequilibrado a fin de mes; dentro del mes corren."""
    valores = pd.DataFrame(series).sort_index().ffill().dropna(how="all")
    nivel, nav, previo = 100., [], None
    for _, bloque in valores.groupby(valores.index.to_period("M")):
        if previo is not None:
            bloque = pd.concat([previo.to_frame().T, bloque])
        crecimiento = bloque.divide(bloque.iloc[0])
        w = pd.Series({c: pesos[c] for c in crecimiento.columns})
        periodo = crecimiento.mul(w / w.sum(), axis=1).sum(axis=1) * nivel
        nav.append(periodo.iloc[1:] if previo is not None else periodo)
        nivel = float(periodo.iloc[-1]); previo = bloque.iloc[-1]
    s = pd.concat(nav).sort_index()
    return s[~s.index.duplicated(keep="last")]


def pesos_fmt(v):
    return f"${v:,.0f}".replace(",", ".")


def main():
    u = load_universe()
    p = pd.read_csv("data/market_prices_daily.csv", parse_dates=["date"])
    d = pd.read_csv(ZIP, dtype=str)
    from src.strategy_engine import ALIAS_TICKERS
    loc = d[d.instrument_type.isin({"accion_local", "accion_local_historica"})].copy()
    loc["tk"] = loc.ticker.str.strip().str.upper().map(lambda t: ALIAS_TICKERS.get(t, t))
    loc["fecha"] = pd.to_datetime(loc.date, errors="coerce")
    loc["score"] = pd.to_numeric(loc.score, errors="coerce").fillna(0)
    loc = loc[loc.tk.isin(set(p.alphadata_ticker.unique()))]
    cre = loc[loc.broker == "Credicorp Capital"]

    locales = set(u.loc[u.tipo.isin({"accion_local", "accion_sigma"}), "alphadata_ticker"])
    us = set(u.loc[u.tipo == "accion_us", "alphadata_ticker"])
    etf = set(u.loc[u.tipo == "etf_us", "alphadata_ticker"])
    fx = p[p.alphadata_ticker == "USDCLP"]
    panel = (p[p.alphadata_ticker.isin(locales) & p.date.between(INICIO - pd.Timedelta(days=400), FIN)]
             .pivot(index="date", columns="alphadata_ticker", values="adjusted_close").sort_index().ffill(limit=3))
    panel_us = (to_clp(p[p.alphadata_ticker.isin(us)], u, fx)
                .pivot(index="date", columns="alphadata_ticker", values="adjusted_close").sort_index().ffill(limit=3))
    panel_oro = (to_clp(p[p.alphadata_ticker.isin(etf)], u, fx)
                 .pivot(index="date", columns="alphadata_ticker", values="adjusted_close").sort_index().ffill(limit=3))
    ses = panel.index[panel.index >= INICIO]
    ses_us = panel_us.index[panel_us.index >= INICIO]
    semanas = sorted({f for f in pd.Series(ses, index=ses).groupby(ses.to_period("W-FRI")).max()})
    meses_cl = sorted({f for f in pd.Series(ses, index=ses).groupby(ses.to_period("M")).max()})
    meses_us = sorted({f for f in pd.Series(ses_us, index=ses_us).groupby(ses_us.to_period("M")).max()})

    valid = pd.DataFrame({"ticker": cre.tk, "broker_normalized": "Credicorp Capital",
                          "signal": cre.score.astype(int), "row_number": range(len(cre)),
                          "available_at_parsed": cre.fecha})
    estado, obj_sigma = {"sigma_entries": {}}, []
    for f in semanas:
        cart, _, estado = sigma6(valid, p.loc[p.date <= f], pd.Timestamp(f), estado)
        obj_sigma.append((f, dict(zip(cart.ticker, cart.target_weight))))
    obj_delta = [(f, dict(zip(*[delta12(p.loc[p.date <= f], u, pd.Timestamp(f))[0][c]
                                for c in ("ticker", "target_weight")]))) for f in meses_cl]
    obj_gamma = [(f, dict(zip(*[gamma6(p.loc[p.date <= f], u, pd.Timestamp(f))[0][c]
                                for c in ("ticker", "target_weight")]))) for f in meses_us]
    obj_oro = [(ses_us[1], {"IAU": 1.0})]
    print("objetivos listos", flush=True)

    receta = {"Delta-12": (panel, ses, obj_delta, TASA_CL, MIN_CL),
              "Gamma-6": (panel_us, ses_us, obj_gamma, TASA_US, 0.),
              "Oro": (panel_oro, ses_us, obj_oro, TASA_US, 0.),
              "Sigma-6": (panel, ses, obj_sigma, TASA_CL, MIN_CL)}

    conjuntos = {}
    for nombre, pesos in CARTERAS.items():
        series = {}
        for pieza, w in pesos.items():
            pan, se, obj, tasa, minimo = receta[pieza]
            series[pieza] = correr(pan, se, obj, TOTAL * w, tasa, minimo)
        conjuntos[nombre] = combinar(series, pesos)
        print(f"  {nombre} listo", flush=True)

    tramos = [("ventana completa", slice(None)), ("seleccion 21-23", slice(None, CORTE)),
              ("evaluacion 24-26", slice(CORTE, None))]
    for etiqueta, tramo in tramos:
        print(f"\n########## {etiqueta} ##########")
        print(f"{'cartera':28} {'parte de $20M':>16} {'ganancia':>16} {'anual':>9} "
              f"{'peor caida':>18} {'%':>8}")
        base = None
        for nombre, serie in conjuntos.items():
            s = serie.loc[tramo].dropna()
            pesos_final = TOTAL * s.iloc[-1] / s.iloc[0]
            anos = (s.index[-1] - s.index[0]).days / 365.25
            an = (s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1
            dd = float((s / s.cummax() - 1).min())
            caida_pesos = TOTAL * s.cummax().max() / s.iloc[0] * dd
            print(f"{nombre:28} {pesos_fmt(pesos_final):>16} "
                  f"{pesos_fmt(pesos_final - TOTAL):>16} {an:>+9.2%} "
                  f"{pesos_fmt(caida_pesos):>18} {dd:>8.1%}")
            if base is None:
                base = pesos_final
        print()
        valores = {n: TOTAL * conjuntos[n].loc[tramo].dropna().iloc[-1] / conjuntos[n].loc[tramo].dropna().iloc[0]
                   for n in conjuntos}
        a = valores["A  cuatro piezas al 25%"]
        for n in ["B  tres piezas en tercios", "C  control, oro en 25%"]:
            print(f"  A contra {n[:1]}: {pesos_fmt(a - valores[n])}  "
                  f"({(a / valores[n] - 1):+.2%} sobre el valor final)")


if __name__ == "__main__":
    main()
