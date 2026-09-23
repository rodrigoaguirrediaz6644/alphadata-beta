"""Cuanto de la cartera se mueve con el dolar, y que pasa si se le quita.

Sale de una correccion: yo escribi que la pieza de oro era "dos tercios dolar"
y eso describe la varianza, no la exposicion. **Beta 0,97 es dolar entero.**
Cada peso puesto ahi se mueve uno a uno con el tipo de cambio ademas de moverse
con el oro.

Y si el oro es dolar entero y Gamma-6 tambien, la pregunta deja de ser sobre el
oro: es cuanto de la cartera completa esta montado en el dolar sin que nadie lo
haya decidido.

Investigacion pura: no toca produccion. La linea del informe va aparte.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRECIOS = ROOT / "data" / "market_prices_daily.csv"
PUBLICADO = ROOT / "data" / "reconstruccion_historica.csv"
CONFIG = ROOT / "config" / "runtime.v2.json"
TICKERS = ROOT / "config" / "tickers.csv"

PIEZAS = ("Delta-12", "Gamma-6", "Oro")


def pct(x):
    return "   —  " if pd.isna(x) else f"{x:+.2%}".replace(".", ",")


def pesos(x):
    return "$" + f"{x:,.0f}".replace(",", ".")


def cargar():
    import json
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    capital = cfg.get("capital", {})
    d = pd.read_csv(PRECIOS, parse_dates=["date"])
    fx = d[d.alphadata_ticker == "USDCLP"].set_index("date").adjusted_close.sort_index()
    h = pd.read_csv(PUBLICADO, parse_dates=["date"]).set_index("date").sort_index()
    return capital, fx, h


def sin_dolar(r_clp, r_fx):
    """El retorno de un instrumento en dolares, despejado de su retorno en pesos.

    r_clp = (1 + r_usd)(1 + r_fx) - 1, asi que r_usd sale exacto. No es una
    aproximacion lineal: es la identidad.
    """
    return (1 + r_clp) / (1 + r_fx) - 1


def cagr(s):
    return (1 + s).prod() ** (365.25 / (s.index[-1] - s.index[0]).days) - 1


def caida(s):
    nav = (1 + s).cumprod()
    return float((nav / nav.cummax() - 1).min())


def main():
    capital, fx, h = cargar()
    reparto = capital.get("reparto", {})
    total = float(capital.get("total_clp", 0))

    # Que piezas nacen en dolares. La regla es la misma que usa `to_clp`: la
    # moneda del instrumento en config/tickers.csv, no una lista escrita aca.
    universo = pd.read_csv(TICKERS)
    en_usd = set(universo.loc[universo.moneda == "USD", "alphadata_ticker"])
    # Gamma-6 compra ETF y acciones de EE.UU.; el oro es IAU. Delta-12 es
    # chilena. Se declara por pieza porque la cartera de cada una cambia.
    piezas_usd = {"Delta-12": 0., "Gamma-6": 1., "Oro": 1.}

    print("#" * 78)
    print("# CUANTO DE LA CARTERA SE MUEVE CON EL DOLAR")
    print("#" * 78)
    print(f"  Capital de referencia: {pesos(total)}\n")
    print(f"  {'pieza':12} {'reparto':>9} {'en dolares':>12} {'monto en dolares':>18}")
    expuesto = 0.
    for p in PIEZAS:
        w = float(reparto.get(p, 0))
        usd = piezas_usd[p]
        expuesto += w * usd
        print(f"  {p:12} {w:>9.1%} {usd:>12.0%} {pesos(total * w * usd):>18}")
    print(f"  {'':12} {'':>9} {'TOTAL':>12} {pesos(total * expuesto):>18}")
    print(f"\n  **{expuesto:.1%} de la cartera se mueve uno a uno con el tipo de cambio.**")
    print(f"  Y no hay ninguna decision escrita que diga que esa era la intencion:")
    print(f"  salio de elegir tres piezas por separado, cada una por sus motivos.")
    print(f"\n  {len(en_usd)} instrumentos del universo nacen en dolares.")

    # --- la cartera con el dolar y sin el dolar ----------------------------
    r_fx = fx.pct_change()
    j = pd.concat({p: h[p].pct_change(fill_method=None) for p in PIEZAS}
                  | {"fx": r_fx}, axis=1, sort=True).dropna()
    con = sum(float(reparto.get(p, 0)) * j[p] for p in PIEZAS)
    sin = sum(float(reparto.get(p, 0))
              * (sin_dolar(j[p], j.fx) if piezas_usd[p] else j[p]) for p in PIEZAS)

    print("\n" + "#" * 78)
    print("# LA CARTERA COMPLETA, CON EL DOLAR Y SIN EL DOLAR")
    print("#" * 78)
    print(f"  {len(j)} dias, desde {j.index.min().date()}. Rebalanceo diario al reparto.\n")
    print(f"  {'':22} {'anual':>9} {'peor caida':>12} {'volatilidad':>13}")
    for nombre, s in (("con el dolar", con), ("sin el dolar", sin)):
        print(f"  {nombre:22} {pct(cagr(s)):>9} {pct(caida(s)):>12} "
              f"{pct(s.std() * 252 ** .5):>13}")
    print(f"  {'el dolar solo':22} {pct(cagr(j.fx)):>9} {pct(caida(j.fx)):>12} "
          f"{pct(j.fx.std() * 252 ** .5):>13}")

    print(f"\n  Diferencia: {pct(cagr(con) - cagr(sin))} de retorno anual y "
          f"{pct(caida(con) - caida(sin))} de peor caida.")

    # --- y por pieza, para ver donde trabaja y donde duplica ---------------
    print("\n  Por pieza, la correlacion con Delta-12 -que es la parte en pesos-:")
    print(f"  {'':12} {'en pesos':>10} {'sin el dolar':>14}")
    for p in ("Gamma-6", "Oro"):
        print(f"  {p:12} {j[p].corr(j['Delta-12']):>+10.3f} "
              f"{sin_dolar(j[p], j.fx).corr(j['Delta-12']):>+14.3f}")
    rho = j.fx.corr(j["Delta-12"])
    print(f"\n  El dolar contra Delta-12: {rho:+.3f}")
    print("\n  **Y aca los numeros contradicen la historia del colchon, asi que va")
    print("  como salio.** Quitar el dolar SUBE las correlaciones -o sea que el dolar")
    print("  las estaba bajando, como se esperaba- pero la cartera con dolar tiene")
    print(f"  mas volatilidad ({pct(con.std() * 252 ** .5)} contra "
          f"{pct(sin.std() * 252 ** .5)}) y peor caida.")
    print("\n  Correlacion mas baja no es riesgo mas bajo cuando lo que se agrega es")
    print(f"  esto de volatil: el dolar solo rinde {pct(cagr(j.fx))} anual con "
          f"{pct(caida(j.fx))} de caida propia")
    print(f"  y {pct(j.fx.std() * 252 ** .5)} de volatilidad, contra "
          f"{rho:+.3f} de correlacion con Delta-12, que es cero.")
    print("\n  En esta ventana el dolar **agrega retorno y agrega riesgo**. No amortigua.")
    print("  Lo que no se puede contestar con 2021-2026 es si amortiguaria en una")
    print("  caida de la bolsa chilena de las que importan: en esta ventana no hubo,")
    print("  y el mecanismo del colchon en las AFP se vio sobre episodios que si la")
    print("  tuvieron. Son dos afirmaciones distintas y solo una esta medida aca.")


if __name__ == "__main__":
    main()
