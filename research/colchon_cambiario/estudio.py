"""El colchon cambiario, probado sobre episodios. Ver HIPOTESIS.md.

No se ajusta ningun parametro: el reparto viene de la configuracion del
proyecto y el umbral de episodio esta fijado en el diseno congelado.

Investigacion pura: no toca produccion.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "runtime.v2.json"

DESDE = "2007-11-20"        # donde empieza ECH
CAIDA_MINIMA = .15          # fijado en HIPOTESIS.md, no se mueve

# El proveedor entrega precios imposibles del dolar -5,46 el 10-04-2014-. Sin
# esta guardia la volatilidad del mercado sale absurda; ya nos paso.
MINIMO_CLP_POR_USD = 300


def serie(t):
    h = yf.Ticker(t).history(start="2007-01-01", auto_adjust=False)["Close"].dropna()
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return h[h >= MINIMO_CLP_POR_USD] if "CLP" in t else h


def pct(x):
    return "   —  " if pd.isna(x) else f"{x:+.2%}".replace(".", ",")


def episodios_del_diseno(nav, minimo=CAIDA_MINIMA):
    """La regla que escribi en HIPOTESIS.md. **Esta rota para esta serie.**

    Define el episodio como el tramo contiguo bajo el maximo movil, que es lo
    que usamos en las AFP y ahi funcionaba porque el Fondo A recuperaba maximos
    entre crisis. La bolsa chilena no: **estuvo bajo su maximo de 2010 durante
    diez anios seguidos**, asi que la regla junta 2011, 2015-16, 2019 y 2020 en
    un solo «episodio» de 3.422 dias.

    Se conserva y se reporta porque el defecto se ve **sin mirar el resultado**
    -un episodio de nueve anios no es un episodio- y porque cambiar la regla
    despues de correrla es justo lo que no se hace en silencio.
    """
    pico = nav.cummax()
    eps, ini = [], None
    for f, bajo in (nav < pico).items():
        if bajo and ini is None:
            ini = f
        elif not bajo and ini is not None:
            t = nav.loc[ini:f]
            if 1 - t.min() / nav.loc[:ini].max() >= minimo:
                eps.append((nav.loc[:ini].idxmax(), t.idxmin()))
            ini = None
    if ini is not None:
        t = nav.loc[ini:]
        if 1 - t.min() / nav.loc[:ini].max() >= minimo:
            eps.append((nav.loc[:ini].idxmax(), t.idxmin()))
    return eps


# Cuanto tiene que recuperar la serie para dar el episodio por terminado y
# volver a buscar maximos. La mitad de lo caido es la convencion habitual y es
# lo que impide que una decada bajo el maximo cuente como un solo episodio.
RECUPERACION = .50


def episodios(nav, minimo=CAIDA_MINIMA, recuperacion=RECUPERACION):
    """Caida de mas de `minimo` desde un maximo, cerrada al recuperar la mitad.

    **Es una reparacion del instrumento, no un ajuste del resultado.** El
    umbral de caida sigue siendo el 15% congelado; lo unico que cambia es
    cuando termina un episodio y empieza el siguiente, que en el diseno estaba
    mal definido para una serie que pasa anios bajo su maximo.
    """
    eps = []
    pico_v, pico_f = nav.iloc[0], nav.index[0]
    fondo_v, fondo_f, dentro = pico_v, pico_f, False
    for f, v in nav.items():
        if not dentro:
            if v >= pico_v:
                pico_v, pico_f = v, f
            elif 1 - v / pico_v >= minimo:
                dentro, fondo_v, fondo_f = True, v, f
        else:
            if v < fondo_v:
                fondo_v, fondo_f = v, f
            elif v >= fondo_v + (pico_v - fondo_v) * recuperacion:
                eps.append((pico_f, fondo_f))
                dentro = False
                pico_v, pico_f = v, f
    if dentro:
        eps.append((pico_f, fondo_f))
    return eps


def sin_dolar(r_clp, r_fx):
    """Identidad, no aproximacion: r_clp = (1+r_usd)(1+r_fx) - 1."""
    return (1 + r_clp) / (1 + r_fx) - 1


def caida(s):
    nav = (1 + s).cumprod()
    return float((nav / nav.cummax() - 1).min())


def cagr(s):
    return (1 + s).prod() ** (365.25 / (s.index[-1] - s.index[0]).days) - 1


def main():
    reparto = json.loads(CONFIG.read_text(encoding="utf-8"))["capital"]["reparto"]
    w_chi = float(reparto["Delta-12"])
    w_glo = float(reparto["Gamma-6"])
    w_oro = float(reparto["Oro"])

    fx, ech, mundo, oro = (serie("USDCLP=X"), serie("ECH"),
                           serie("^990100-USD-STRD"), serie("GC=F"))
    idx = fx.index.intersection(ech.index).intersection(mundo.index).intersection(oro.index)
    idx = idx[idx >= DESDE]
    fx, ech, mundo, oro = (s.reindex(idx) for s in (fx, ech, mundo, oro))

    chile_clp = ech * fx                     # acciones chilenas en pesos
    r = pd.DataFrame({
        "fx": fx.pct_change(),
        "chile": chile_clp.pct_change(),
        "mundo_usd": mundo.pct_change(),
        "oro_usd": oro.pct_change(),
    }).dropna()
    r["mundo_clp"] = (1 + r.mundo_usd) * (1 + r.fx) - 1
    r["oro_clp"] = (1 + r.oro_usd) * (1 + r.fx) - 1

    con = w_chi * r.chile + w_glo * r.mundo_clp + w_oro * r.oro_clp
    sin = w_chi * r.chile + w_glo * r.mundo_usd + w_oro * r.oro_usd

    nav_chile = (1 + r.chile).cumprod()
    rotos = episodios_del_diseno(nav_chile)
    eps = episodios(nav_chile)

    print("#" * 78)
    print("# PRIMERO: la regla que congele esta rota, y se ve sin mirar el resultado")
    print("#" * 78)
    print("  La escribi pensando en las AFP, donde el Fondo A recupera maximos entre")
    print("  crisis. La bolsa chilena estuvo bajo su maximo de 2010 diez anios seguidos.\n")
    print(f"  {'episodio':26} {'dias':>6}")
    for a, b in rotos:
        print(f"  {str(a.date()) + ' a ' + str(b.date()):26} {(b - a).days:>6}")
    print("\n  Un episodio de 3.422 dias junta 2011, 2015-16, 2019 y 2020 en uno solo.")
    print("  Se repara el instrumento: el umbral de 15% no se toca, y el episodio")
    print(f"  ahora se cierra cuando la serie recupera el {RECUPERACION:.0%} de lo caido.\n")

    print("#" * 78)
    print("# EL COLCHON CAMBIARIO, SOBRE EPISODIOS")
    print("#" * 78)
    print(f"  Bolsa chilena en pesos: ECH x USDCLP, {r.index.min().date()} a "
          f"{r.index.max().date()} ({len(r)} dias)")
    print(f"  Cartera: {w_chi:.1%} Chile, {w_glo:.1%} global, {w_oro:.1%} oro, "
          "rebalanceo diario.")
    print(f"  Episodio = caida de mas de {CAIDA_MINIMA:.0%} desde el maximo. "
          f"Salieron {len(eps)}.\n")

    print(f"  {'episodio':26} {'dias':>5} {'Chile':>9} {'USD/CLP':>9} "
          f"{'con dolar':>10} {'sin dolar':>10} {'beneficio':>10}")
    filas = []
    for a, b in eps:
        tramo_con, tramo_sin = con.loc[a:b], sin.loc[a:b]
        cc, cs = float((1 + tramo_con).prod() - 1), float((1 + tramo_sin).prod() - 1)
        r_chi = float(chile_clp[b] / chile_clp[a] - 1)
        r_fx = float(fx[b] / fx[a] - 1)
        filas.append({"inicio": a.date(), "fondo": b.date(), "dias": (b - a).days,
                      "chile": r_chi, "fx": r_fx, "con": cc, "sin": cs,
                      "beneficio": cc - cs})
        print(f"  {str(a.date()) + ' a ' + str(b.date()):26} {(b - a).days:>5} "
              f"{pct(r_chi):>9} {pct(r_fx):>9} {pct(cc):>10} {pct(cs):>10} "
              f"{pct(cc - cs):>10}")

    t = pd.DataFrame(filas)
    t.to_csv(Path(__file__).parent / "episodios.csv", index=False)

    print("\n" + "#" * 78)
    print("# VEREDICTO contra el criterio pre-registrado")
    print("#" * 78)
    suben = int((t.fx > 0).sum())
    mediano = float(t.beneficio.median())
    print(f"\n  1) «el peso sube en al menos 5 de los episodios»")
    print(f"     -> sube en {suben} de {len(t)}. "
          f"{'CUMPLE' if suben >= 5 else 'NO CUMPLE'}")
    print(f"\n  2) «el beneficio mediano es de al menos 2 puntos de caida evitada»")
    print(f"     -> mediano {pct(mediano)}. "
          f"{'CUMPLE' if mediano >= .02 else 'NO CUMPLE'}")
    print(f"     (beneficio positivo en {int((t.beneficio > 0).sum())} de {len(t)})")

    print(f"\n  Y mi segunda prediccion, la que me jugue en contra:")
    print(f"     «la cartera con dolar igual tiene peor caida sobre la ventana completa»")
    print(f"     -> con dolar {pct(caida(con))}, sin dolar {pct(caida(sin))}. "
          f"{'ACIERTO' if caida(con) < caida(sin) else 'FALLO: la prediccion se cae'}")

    print("\n" + "#" * 78)
    print("# LA VENTANA COMPLETA, para poner el colchon al lado de lo que cuesta")
    print("#" * 78)
    print(f"  {'':16} {'anual':>9} {'peor caida':>12} {'volatilidad':>13}")
    for nombre, s in (("con el dolar", con), ("sin el dolar", sin)):
        print(f"  {nombre:16} {pct(cagr(s)):>9} {pct(caida(s)):>12} "
              f"{pct(s.std() * 252 ** .5):>13}")
    print(f"  {'el dolar solo':16} {pct(cagr(r.fx)):>9} {pct(caida(r.fx)):>12} "
          f"{pct(r.fx.std() * 252 ** .5):>13}")

    fuera = ~pd.Series(False, index=r.index)
    for a, b in eps:
        fuera.loc[a:b] = False if True else fuera.loc[a:b]
    marca = pd.Series(True, index=r.index)
    for a, b in eps:
        marca.loc[a:b] = False
    print(f"\n  Y separando los dias de episodio de los demas:")
    print(f"  {'':16} {'en episodios':>14} {'fuera de ellos':>16}")
    for nombre, s in (("con el dolar", con), ("sin el dolar", sin)):
        print(f"  {nombre:16} {pct(cagr(s[~marca])):>14} {pct(cagr(s[marca])):>16}")
    print(f"  {'dias':16} {int((~marca).sum()):>14} {int(marca.sum()):>16}")


if __name__ == "__main__":
    main()
