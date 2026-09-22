"""El premio del CDV sobre su valor teorico, medido sobre dos anios.

La hipotesis era que la corredora cobra un margen en la conversion de dolar a
peso, invisible en la boleta, y que con la rotacion mensual de Gamma-6 ese
margen domina a todos los costos discutidos hasta ahora.

Se mide con `src.cdv`, que es el mismo codigo que corre en produccion.
"""
import sys

import pandas as pd

sys.path.insert(0, ".")
from src.cdv import RAZON_MAXIMA, cargar, frescas, premio
from src.fetch_prices import load_universe


def pct(v, d=3):
    return f"{v:+.{d}%}"


def main():
    c = cargar()
    p = pd.read_csv("data/market_prices_daily.csv", parse_dates=["date"])

    print("########## lo rancio que esta el dato ##########")
    c = c.sort_values(["cdv", "date"])
    salto = c.groupby("cdv").cdv_clp.diff()
    repite = (salto.notna() & salto.eq(0)).groupby(c.cdv).mean()
    print(f"ruedas con volumen cero            : {(c.volumen.fillna(0) == 0).mean():.1%}")
    print(f"ruedas que repiten el cierre previo: mediana entre nombres {repite.median():.1%}, "
          f"maximo {repite.max():.1%} ({repite.idxmax()})")
    g = (salto.ne(0) | salto.isna()).cumsum()
    racha = c.assign(g=g).groupby(["cdv", "g"]).size().groupby(level=0).max().sort_values(ascending=False)
    print("racha mas larga en el mismo precio :")
    for n, v in racha.head(4).items():
        print(f"  {n:14} {v} ruedas")

    f = frescas(c, p)
    print(f"\nruedas frescas (volumen Y cambio): {len(f):,} de {len(c):,} ({len(f) / len(c):.1%})")

    print("\n########## la razon contra el teorico, por nombre ##########")
    print("Si el CDV fuera uno a uno con la accion, esto da 1,00.")
    r = f.assign(razon=lambda d: d.desvio + 1).groupby("cdv").razon.agg(["median", "std", "count"])
    print(r[r["count"] >= 30].sort_values("median").to_string(float_format=lambda v: f"{v:,.4f}"))

    print("\n########## el premio, con su error ##########")
    for etiqueta, desde in [("dos anios", None), ("ultimo anio", "2025-09-22"), ("2026", "2026-01-01")]:
        x = premio(c, p, desde)
        if x is None:
            print(f"{etiqueta:14} sin ruedas suficientes")
            continue
        print(f"{etiqueta:14} {pct(x.medio)} +/- {x.error:.3%}   n={x.ruedas:5,}  "
              f"nombres={x.nombres:3}  distinguible de cero: {'si' if x.distinguible else 'NO'}")

    print("\n########## y lo que de verdad le cuesta a Gamma-6 ##########")
    print("Un premio de nivel no es un costo por lado: si se compra y se vende con")
    print("el mismo premio, se cancela. Lo que cuesta es que cambie entre medio.")
    m = f.groupby(f.date.dt.to_period("M")).desvio.agg(["mean", "count"])
    m = m[m["count"] >= 10]
    print(f"\nmeses con al menos 10 ruedas frescas: {len(m)}")
    print(f"  premio medio de los meses : {pct(m['mean'].mean())}")
    print(f"  desviacion mes a mes      : {m['mean'].std():.3%}")
    print(f"  cambio medio entre meses  : {m['mean'].diff().abs().mean():.3%}")

    print("\n########## los simbolos ##########")
    u = load_universe()
    sin = u.loc[u.tipo.isin({"accion_us", "etf_us"}) & u.cdv_ticker.fillna("").eq(""), "alphadata_ticker"]
    print(f"CDV sin simbolo confirmado: {list(sin) or 'ninguno'}")
    print(f"(se descarta cualquier rueda con |razon - 1| > {RAZON_MAXIMA:.0%}: no es un premio, es otro instrumento)")


if __name__ == "__main__":
    main()
