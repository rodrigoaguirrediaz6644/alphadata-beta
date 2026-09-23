"""¿Puede el analisis tecnico sobre el spread A/E anticipar los movimientos?

Reproduce las tres series que muestra el canal de Telegram, las somete a las
pruebas que corresponden, y mide la regla que esos graficos implican.

Investigacion pura: no toca produccion ni el informe.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/afp")
SALIDA = Path("research/afp_analisis_tecnico")
VENTANA_GRAFICO = "2025-05-20"      # los 16 meses de la primera imagen
N_ROC, N_BANDA, K = 20, 20, 2       # variacion de 20 dias, Bollinger (20, 2)
REZAGO = 2                          # dias corridos, medido contra el repositorio fuente


def cuotas(afp):
    return (pd.read_csv(SP / f"vc_{afp}.csv", parse_dates=["date"])
            .set_index("date")[["A", "E"]].dropna().sort_index())


def series(v):
    ratio = v.A / v.E
    roc = ratio.pct_change(N_ROC) * 100                 # la serie de la imagen 3
    nivel = (np.log(ratio) - np.log(ratio.iloc[0])) * 100   # la serie de la imagen 2
    ma = roc.rolling(N_BANDA).mean()
    sd = roc.rolling(N_BANDA).std()
    return ratio, roc, nivel, ma + K * sd, ma - K * sd, ma


def estados(cond_e, cond_a, idx):
    """Maquina de estados: se queda donde esta hasta que una condicion dispara."""
    out, st = [], "A"
    for e, a in zip(cond_e, cond_a):
        if e:
            st = "E"
        elif a:
            st = "A"
        out.append(st)
    return pd.Series(out, index=idx)


def correr(v, st):
    r = v.pct_change().fillna(0)
    pos = st.shift(REZAGO).ffill().reindex(r.index).ffill().dropna()
    return pd.Series(np.where(pos.eq("A"), r.A.loc[pos.index], r.E.loc[pos.index]),
                     index=pos.index), pos


def cagr(s):
    anios = (s.index[-1] - s.index[0]).days / 365.25
    return (1 + s).prod() ** (1 / anios) - 1


def caida(s):
    n = (1 + s).cumprod()
    return float((n / n.cummax() - 1).min())


def pct(v):
    return f"{v:+.2%}".replace(".", ",")


def main():
    v = cuotas("habitat")
    ratio, roc, nivel, up, lo, ma = series(v)

    print("#" * 78)
    print("# 1. LAS TRES IMAGENES, REPRODUCIDAS")
    print("#" * 78)
    w = v.loc[VENTANA_GRAFICO:]
    perf = (w / w.iloc[0] - 1) * 100
    print(f"  ventana del grafico: {w.index.min().date()} a {w.index.max().date()}")
    print(f"  imagen 1  Habitat-A {perf.A.iloc[-1]:+.1f}%   Habitat-E {perf.E.iloc[-1]:+.1f}%"
          f"   (la imagen: ~+28% y ~+2,5%)")
    print(f"  imagen 2  spread en niveles, final {(perf.A - perf.E).iloc[-1]:.1f}"
          f"   (la imagen: ~24)")
    x = roc.loc[VENTANA_GRAFICO:]
    print(f"  imagen 3  variacion de {N_ROC} dias de A/E: rango [{x.min():.2f}%, {x.max():.2f}%], "
          f"media {x.mean():+.2f}%")
    print(f"            (la imagen: rango ~[-3%, +4%] y lineas rojas en +1% y -1%)")
    print(f"\n  **La linea roja de +1% esta en la MEDIA de la serie, no en un extremo.**")

    print("\n" + "#" * 78)
    print("# 2. LA PRUEBA QUE DECIDE SI LAS BANDAS SIGNIFICAN ALGO")
    print("#" * 78)
    for nombre, s in [("spread en niveles (imagen 2)", nivel), (f"variacion {N_ROC} dias (imagen 3)", roc)]:
        p = adfuller(s.dropna(), autolag="AIC")[1]
        print(f"  {nombre:34} ADF p = {p:.4f}  -> "
              f"{'estacionaria' if p < .05 else 'NO estacionaria'}")
    print(f"\n  Las bandas de Bollinger suponen que la serie vuelve a su media. La de la")
    print(f"  imagen 2 **no vuelve**: tiene tendencia. Que toque la banda superior es")
    print(f"  lo que hace una serie que sube, no una senal de nada.")
    print(f"  Tiempo que pasa sobre su media movil: {(nivel > nivel.rolling(N_BANDA).mean()).mean():.0%}")

    print("\n" + "#" * 78)
    print("# 3. ¿LA POSICION EN LAS BANDAS ANTICIPA ALGO?")
    print("#" * 78)
    pb = (roc - lo) / (up - lo)
    print("  %B = donde esta la serie dentro de sus bandas. Si anticipara, %B alto")
    print("  deberia predecir que A rinde MENOS que E en adelante.\n")
    print(f"  {'horizonte':>12} {'correlacion con lo que viene':>32} {'n':>8}")
    for h in (5, 10, 20, 60):
        fut = np.log(ratio.shift(-h) / ratio) * 100
        j = pd.concat([pb.rename("pb"), fut.rename("f")], axis=1).dropna()
        print(f"  {f'{h} dias':>12} {j.pb.corr(j.f):>32.3f} {len(j):>8}")
    print("\n  **Cero, y con el signo al reves del que haria falta.** Esto no descarta")
    print("  una regla: descarta TODAS las reglas construidas sobre estas bandas,")
    print("  en cualquier direccion y con cualquier umbral.")

    print("\n" + "#" * 78)
    print("# 4. LAS REGLAS QUE ESOS GRAFICOS IMPLICAN, MEDIDAS")
    print("#" * 78)
    for afp in ("habitat", "cuprum"):
        vv = cuotas(afp)
        _, rr, _, uu, ll, _ = series(vv)
        d = pd.concat({"roc": rr, "up": uu, "lo": ll}, axis=1).dropna()
        reglas = {
            "reversion: banda alta -> E": estados(d.roc > d.up, d.roc < d.lo, d.index),
            "tendencia: banda alta -> A": estados(d.roc < d.lo, d.roc > d.up, d.index),
            "lineas rojas: sobre +1% -> E": estados(d.roc > 1, d.roc < -1, d.index),
            "lineas rojas: sobre +1% -> A": estados(d.roc < -1, d.roc > 1, d.index),
        }
        print(f"\n  --- {afp.upper()} ---")
        print(f"  {'regla':32} {'anual':>9} {'peor caida':>12} {'cambios/anio':>13}")
        anios = (vv.index[-1] - d.index[0]).days / 365.25
        for n, st in reglas.items():
            s, _ = correr(vv, st)
            print(f"  {n:32} {pct(cagr(s)):>9} {pct(caida(s)):>12} "
                  f"{int((st != st.shift()).sum()) / anios:>13.1f}")
        for n, c in [("comprar A y no mirar", "A"), ("comprar E y no mirar", "E")]:
            s = vv[c].pct_change().dropna().loc[d.index[0]:]
            print(f"  {n:32} {pct(cagr(s)):>9} {pct(caida(s)):>12} {0:>13.1f}")

    print("\n" + "#" * 78)
    print("# 5. LA UNICA QUE GANA, PARTIDA EN PEDAZOS")
    print("#" * 78)
    st = estados(roc < -1, roc > 1, roc.index).dropna()
    s, pos = correr(v, st)
    a = v.A.pct_change().dropna()
    print("  regla: variacion de 20 dias sobre +1% -> Fondo A, bajo -1% -> Fondo E\n")
    print(f"  {'tramo':26} {'regla':>9} {'Fondo A':>9} {'diferencia':>12}")
    tramos = [("2002-2007", "2002-09-09", "2007-10-31"),
              ("la crisis 2007-2009", "2007-11-01", "2009-03-31"),
              ("2009-2013", "2009-04-01", "2013-12-31"),
              ("2014-2019", "2014-01-01", "2019-12-31"),
              ("2020 (covid)", "2020-01-01", "2020-12-31"),
              ("2021-2026", "2021-01-01", None),
              ("los 16 meses del canal", VENTANA_GRAFICO, None)]
    for etq, i, f in tramos:
        x, y = s.loc[i:f], a.loc[i:f]
        marca = "  <-- una sola" if etq.startswith("la crisis") else ""
        print(f"  {etq:26} {pct(cagr(x)):>9} {pct(cagr(y)):>9} {pct(cagr(x) - cagr(y)):>12}{marca}")
    print(f"\n  **Toda la ventaja esta en un episodio.** En cuatro de los otros seis")
    print(f"  tramos la regla pierde, incluido el que el canal esta mostrando.")
    print(f"\n  peor caida: regla {pct(caida(s))} contra Fondo A {pct(caida(a))}")
    print(f"  tiempo en Fondo A: {pos.eq('A').mean():.0%}")

    # --- el grafico ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), height_ratios=[2, 1])
    n_r, n_a, n_e = [(1 + x).cumprod() for x in (s, a.loc[s.index[0]:], v.E.pct_change().dropna().loc[s.index[0]:])]
    ax1.plot(n_a, label="Fondo A, comprar y no mirar", lw=1.6, color="#d97706")
    ax1.plot(n_e, label="Fondo E, comprar y no mirar", lw=1.3, color="#0d9488")
    ax1.plot(n_r, label="la regla del canal (version que gana)", lw=1.6, color="#be123c")
    ax1.axvspan(pd.Timestamp("2007-11-01"), pd.Timestamp("2009-03-31"), color="#94a3b8", alpha=.25)
    ax1.text(pd.Timestamp("2008-01-15"), n_a.max() * .55, "toda la ventaja\nsale de acá",
             fontsize=10, color="#334155")
    ax1.axvspan(pd.Timestamp(VENTANA_GRAFICO), n_a.index[-1], color="#fca5a5", alpha=.30)
    ax1.text(pd.Timestamp("2023-06-01"), n_a.max() * .82, "los 16 meses\nque muestra el canal:\nla regla pierde 10 puntos al año",
             fontsize=9, color="#7f1d1d")
    ax1.set_yscale("log"); ax1.legend(loc="upper left"); ax1.set_title(
        "La regla del canal contra no hacer nada — Habitat, 2002-2026 (escala logarítmica)")
    ax1.grid(alpha=.25)
    dif = (n_r / n_a)
    ax2.plot(dif, color="#be123c", lw=1.4)
    ax2.axhline(1, color="#334155", lw=1)
    ax2.axvspan(pd.Timestamp("2007-11-01"), pd.Timestamp("2009-03-31"), color="#94a3b8", alpha=.25)
    ax2.axvspan(pd.Timestamp(VENTANA_GRAFICO), n_a.index[-1], color="#fca5a5", alpha=.30)
    ax2.set_title("La regla dividida por el Fondo A: sube sólo en la crisis, y baja el resto del tiempo")
    ax2.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(SALIDA / "regla_contra_no_hacer_nada.png", dpi=130)
    print(f"\n  grafico en {SALIDA / 'regla_contra_no_hacer_nada.png'}")


if __name__ == "__main__":
    main()
