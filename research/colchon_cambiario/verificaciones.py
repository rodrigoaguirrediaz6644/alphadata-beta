"""Las dos verificaciones sobre el resultado del colchon. Sin reglas nuevas.

**Primera:** ordenar los veinte episodios por profundidad y poner al lado el
beneficio del dolar. Si los fracasos son los episodios chicos, el seguro
funciona donde tiene que funcionar. Es una tabla ordenada, no una sub-regla: no
se sale a buscar que distingue a los siete, porque veinte episodios con siete
fracasos no sostienen una sub-regla y buscarla es como se fabrica un backtest
bonito.

**Segunda:** si `ECH x FX` se parece al IPSA en pesos. El tipo de cambio queda a
los dos lados de la cuenta —en la construccion del indice chileno y en la
porcion de dolares cuyo beneficio se mide— asi que si ECH tiene comportamiento
propio de su mercado, ese comportamiento entra multiplicado por el tipo de
cambio y puede estar generando parte del colchon.

Investigacion pura: no toca produccion.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from estudio import (CAIDA_MINIMA, DESDE, MINIMO_CLP_POR_USD, caida, cagr,
                     episodios, pct)

AQUI = Path(__file__).parent
ROOT = AQUI.parents[1]
CONFIG = ROOT / "config" / "runtime.v2.json"
# El proxy del IPSA total return que el proyecto guardo antes de que el feed
# chileno se congelara. Empieza en 2015 y **queda quieto desde el 17-07-2026**,
# asi que la comparacion termina ahi. Ver INCIDENTE_FEED_CHILENO.md.
IPSA = ROOT / "data" / "archivo" / "ipsa_tr_proxy_cfmitnipsa.csv"
FIN_IPSA = "2026-07-17"


def serie(t, ajustado=True):
    h = yf.Ticker(t).history(start="2007-01-01", auto_adjust=ajustado)["Close"].dropna()
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return h[h >= MINIMO_CLP_POR_USD] if "CLP" in t else h


# --------------------------------------------------------------------------
# PRIMERA: donde fallaron los siete
# --------------------------------------------------------------------------

def primera():
    t = pd.read_csv(AQUI / "episodios.csv")
    t = t.sort_values("chile")           # de la caida mas profunda a la mas leve
    print("#" * 78)
    print("# PRIMERA VERIFICACION — los veinte episodios, del mas profundo al mas leve")
    print("#" * 78)
    print("  El seguro existe para las caidas grandes. Fallar en una de 16% importa")
    print("  mucho menos que fallar en una de 43%.\n")
    print(f"  {'#':>3} {'episodio':24} {'cae Chile':>10} {'USD/CLP':>9} "
          f"{'beneficio':>10}")
    for i, r in enumerate(t.itertuples(), 1):
        marca = "  <- el dolar restó" if r.beneficio < 0 else ""
        print(f"  {i:>3} {str(r.inicio) + ' a ' + str(r.fondo):24} {pct(r.chile):>10} "
              f"{pct(r.fx):>9} {pct(r.beneficio):>10}{marca}")

    mitad = len(t) // 2
    profundos, leves = t.iloc[:mitad], t.iloc[mitad:]
    print(f"\n  {'':24} {'beneficio mediano':>18} {'fracasos':>10}")
    for nombre, g in (("los 10 mas profundos", profundos), ("los 10 mas leves", leves)):
        print(f"  {nombre:24} {pct(g.beneficio.median()):>18} "
              f"{int((g.beneficio < 0).sum()):>7} de {len(g)}")
    print(f"\n  Corte entre los dos grupos: caida de {pct(profundos.chile.max())}")
    peor = t.nsmallest(5, "chile")
    print(f"\n  Y en las cinco peores caidas del indice chileno, el beneficio fue:")
    for r in peor.itertuples():
        print(f"    {str(r.inicio):12} cae {pct(r.chile):>9} -> {pct(r.beneficio)}")


# --------------------------------------------------------------------------
# SEGUNDA: ECH x FX contra el IPSA
# --------------------------------------------------------------------------

def segunda():
    fx = serie("USDCLP=X", ajustado=False)
    ech = serie("ECH")                    # ajustado: incluye dividendos, como el IPSA TR
    ipsa = (pd.read_csv(IPSA, parse_dates=["date"]).set_index("date")
            .sort_index().adjusted_close)
    idx = fx.index.intersection(ech.index).intersection(ipsa.index)
    idx = idx[(idx >= "2015-01-02") & (idx <= FIN_IPSA)]
    fx, ech, ipsa = fx.reindex(idx), ech.reindex(idx), ipsa.reindex(idx)
    via_ech = (ech * fx).pct_change().dropna()
    via_ipsa = ipsa.pct_change().dropna()
    j = pd.concat({"ech": via_ech, "ipsa": via_ipsa}, axis=1).dropna()

    print("\n" + "#" * 78)
    print("# SEGUNDA VERIFICACION — ECH x FX contra el IPSA en pesos")
    print("#" * 78)
    print(f"  {len(j)} dias, {j.index.min().date()} a {j.index.max().date()}.")
    print("  El IPSA del proyecto empieza en 2015 y queda congelado el 17-07-2026,")
    print("  asi que la comparacion es sobre ese tramo y no sobre los 19 anios.\n")
    dif = j.ech - j.ipsa
    print(f"  correlacion de retornos diarios:  {j.ech.corr(j.ipsa):+.3f}")
    print(f"  error de seguimiento anualizado:  {dif.std() * 252 ** .5:.2%}")
    print(f"  diferencia de retorno anual:      "
          f"{pct(cagr(j.ech) - cagr(j.ipsa))}")

    # y por episodio, que es donde importa
    eps = episodios((1 + via_ech).cumprod())
    eps = [(a, b) for a, b in eps if a >= j.index.min() and b <= j.index.max()]
    print(f"\n  Y en los {len(eps)} episodios que caen dentro de esta ventana:")
    print(f"  {'episodio':24} {'corr':>7} {'error segu.':>12} {'ECH':>9} {'IPSA':>9}")
    filas = []
    for a, b in eps:
        k = j.loc[a:b]
        if len(k) < 5:
            continue
        rho = k.ech.corr(k.ipsa)
        te = (k.ech - k.ipsa).std() * 252 ** .5
        re, ri = float((1 + k.ech).prod() - 1), float((1 + k.ipsa).prod() - 1)
        filas.append({"rho": rho, "te": te, "dif": re - ri})
        print(f"  {str(a.date()) + ' a ' + str(b.date()):24} {rho:>+7.3f} "
              f"{te:>11.1%} {pct(re):>9} {pct(ri):>9}")
    e = pd.DataFrame(filas)
    print(f"\n  En episodios: correlacion mediana {e.rho.median():+.3f}, "
          f"error de seguimiento mediano {e.te.median():.1%}")
    print(f"  Diferencia de retorno en el episodio: mediana {pct(e.dif.median())}, "
          f"rango {pct(e.dif.min())} a {pct(e.dif.max())}")

    # --- y lo que decide: rehacer el colchon con el IPSA -------------------
    reparto = json.loads(CONFIG.read_text(encoding="utf-8"))["capital"]["reparto"]
    w = (float(reparto["Delta-12"]), float(reparto["Gamma-6"]), float(reparto["Oro"]))
    mundo, oro = serie("^990100-USD-STRD"), serie("GC=F")
    k = idx.intersection(mundo.index).intersection(oro.index)
    r = pd.DataFrame({
        "fx": fx.reindex(k).pct_change(),
        "mundo_usd": mundo.reindex(k).pct_change(),
        "oro_usd": oro.reindex(k).pct_change(),
        "ech": (ech * fx).reindex(k).pct_change(),
        "ipsa": ipsa.reindex(k).pct_change(),
    }).dropna()
    r["mundo_clp"] = (1 + r.mundo_usd) * (1 + r.fx) - 1
    r["oro_clp"] = (1 + r.oro_usd) * (1 + r.fx) - 1

    print("\n" + "#" * 78)
    print("# LO QUE DECIDE: el mismo colchon, con ECH y con el IPSA")
    print("#" * 78)
    print(f"  Misma regla, mismo umbral, misma ventana ({len(r)} dias).\n")
    print(f"  {'bolsa chilena':16} {'episodios':>10} {'peso sube':>11} "
          f"{'benef. mediano':>15} {'caida con':>11} {'caida sin':>11}")
    for nombre, col in (("ECH x FX", "ech"), ("IPSA", "ipsa")):
        con = w[0] * r[col] + w[1] * r.mundo_clp + w[2] * r.oro_clp
        sin = w[0] * r[col] + w[1] * r.mundo_usd + w[2] * r.oro_usd
        ep = episodios((1 + r[col]).cumprod())
        ben, sube = [], 0
        for a, b in ep:
            cc = float((1 + con.loc[a:b]).prod() - 1)
            cs = float((1 + sin.loc[a:b]).prod() - 1)
            ben.append(cc - cs)
            sube += int(float((1 + r.fx.loc[a:b]).prod() - 1) > 0)
        print(f"  {nombre:16} {len(ep):>10} {str(sube) + ' de ' + str(len(ep)):>11} "
              f"{pct(np.median(ben)):>15} {pct(caida(con)):>11} {pct(caida(sin)):>11}")


if __name__ == "__main__":
    primera()
    segunda()
