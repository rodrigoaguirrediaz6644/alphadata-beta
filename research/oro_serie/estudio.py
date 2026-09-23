"""Sobre que serie se midio el oro, y cuanto de su diversificacion es el dolar.

La pregunta era si el aporte del oro se midio sobre los precios transados de
IAUCL —un CDV chileno con dias sin operar y saltos falsos— o sobre el oro. Si
fuera lo primero, la correlacion estaria subestimada por construccion y el 25%
estaria inflado.

**No es lo primero.** Pero midiendo para contestarlo aparece otra cosa, en el
mismo lugar y que tambien toca al 25%.

Investigacion pura: no toca produccion.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRECIOS = ROOT / "data" / "market_prices_daily.csv"
PUBLICADO = ROOT / "data" / "reconstruccion_historica.csv"

# Un CDV chileno sin libro se delata por dos cosas: dias con el precio
# exactamente repetido y saltos que el subyacente no puede dar.
SALTO_IMPOSIBLE_DIARIO = .08


def pct(x):
    return f"{x:+.2%}".replace(".", ",")


def cargar():
    d = pd.read_csv(PRECIOS, parse_dates=["date"])
    def serie(t):
        return d[d.alphadata_ticker == t].set_index("date").sort_index()
    return serie("IAU"), serie("USDCLP")


def parte1():
    """De donde sale la serie: se mira el dato, no la configuracion."""
    iau, _ = cargar()
    r = iau.adjusted_close.pct_change().dropna()
    print("#" * 78)
    print("# PARTE 1 — que serie es")
    print("#" * 78)
    print(f"  ticker de origen: {iau.yahoo_ticker.iloc[-1]}   "
          f"{len(iau)} filas, {iau.index.min().date()} a {iau.index.max().date()}")
    print(f"  ultimo precio: {iau.adjusted_close.iloc[-1]:.2f}   "
          f"volumen tipico: {iau.volume.median():,.0f} unidades")
    print(f"\n  dias con precio exactamente repetido: {(r == 0).sum()} de {len(r)} "
          f"({(r == 0).mean():.1%})")
    print(f"  huecos de mas de 4 dias corridos: "
          f"{int((iau.index.to_series().diff().dt.days > 4).sum())}")
    print(f"\n  los movimientos diarios mas grandes, con su volumen:")
    for f in r.abs().nlargest(4).index:
        i = iau.index.get_loc(f)
        print(f"    {f.date()}  {pct(r[f]):>8}   volumen {iau.volume.iloc[i]:>12,.0f}")
    grandes = r[r.abs() > SALTO_IMPOSIBLE_DIARIO]
    print(f"\n  Un CDV sin libro daria saltos grandes CON volumen bajo o nulo.")
    print(f"  Acá los {len(grandes)} saltos sobre {SALTO_IMPOSIBLE_DIARIO:.0%} vienen con "
          f"{iau.volume.reindex(grandes.index).median():,.0f} unidades de mediana,")
    print(f"  contra {iau.volume.median():,.0f} de un dia normal. Son sesiones reales.")


def parte2():
    """Cuanto de la diversificacion del oro es oro y cuanto es dolar."""
    iau, fx = cargar()
    h = pd.read_csv(PUBLICADO, parse_dates=["date"]).set_index("date").sort_index()
    j = pd.concat({
        "fx": fx.adjusted_close.pct_change(),
        "oro_usd": iau.adjusted_close.pct_change(),
        "oro_clp": h["Oro"].pct_change(fill_method=None),
        "g6": h["Gamma-6"].pct_change(fill_method=None),
        "d12": h["Delta-12"].pct_change(fill_method=None),
    }, axis=1, sort=True).dropna()

    print("\n" + "#" * 78)
    print("# PARTE 2 — cuanto de la diversificacion del oro es el dolar")
    print("#" * 78)
    print(f"  {len(j)} dias en comun, desde {j.index.min().date()}\n")
    print(f"  {'':28} {'en pesos':>10} {'sin el dolar':>14}")
    print(f"  {'oro contra Gamma-6':28} {j.oro_clp.corr(j.g6):>+10.3f} "
          f"{j.oro_usd.corr(j.g6 - j.fx):>+14.3f}")
    print(f"  {'oro contra Delta-12':28} {j.oro_clp.corr(j.d12):>+10.3f} "
          f"{j.oro_usd.corr(j.d12):>+14.3f}")
    print(f"\n  El oro en pesos contra el dolar: {j.oro_clp.corr(j.fx):+.3f}")
    print(f"  El oro en dolares contra el dolar: {j.oro_usd.corr(j.fx):+.3f}")
    print(f"\n  volatilidad anual del oro: {j.oro_usd.std() * 252 ** .5:.1%} en dolares, "
          f"{j.oro_clp.std() * 252 ** .5:.1%} en pesos")
    print(f"  El dolar le agrega {(j.oro_clp.std() - j.oro_usd.std()) * 252 ** .5:.1%} "
          "de volatilidad, no se la quita.")

    # Cuanto pesa el dolar dentro del oro en pesos, por regresion simple.
    beta = j.cov().loc["oro_clp", "fx"] / j.fx.var()
    r2 = j.oro_clp.corr(j.fx) ** 2
    print(f"\n  Regresion del oro en pesos sobre el dolar: beta {beta:.2f}, "
          f"R2 {r2:.0%}")
    print(f"  O sea que **el {r2:.0%} de la varianza de la pieza de oro es tipo de cambio**.")


if __name__ == "__main__":
    parte1()
    parte2()
