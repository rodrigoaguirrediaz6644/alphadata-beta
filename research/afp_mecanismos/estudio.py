"""Los dos mecanismos, probados contra lo que ya paso. Ver HIPOTESIS.md.

No se ajusta ningun parametro. Son dos correlaciones sobre los episodios
historicos, con el signo predicho por escrito antes de mirar.

Investigacion pura: no toca produccion ni el informe.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/afp")
CAIDA_MINIMA = .10


def cuotas(afp="cuprum"):
    v = (pd.read_csv(SP / f"vc_{afp}.csv", parse_dates=["date"])
         .set_index("date").sort_index()[["A", "B", "C", "D", "E"]].dropna())
    return v[v.index >= "2002-08-01"]


# El proveedor entrega precios imposibles del dolar: 5,46 el 10-04-2014 y 5,00
# el 22-12-2016. El pipeline ya tiene una guardia para esto -sanear_fx- y sin
# ella la desviacion estandar del mercado sale 180% diaria y la beta colapsa a
# cero. Fue el segundo error de esta corrida.
MINIMO_CLP_POR_USD = 300


def mercado(t, desde="2002-01-01"):
    h = yf.Ticker(t).history(start=desde, auto_adjust=False)["Close"]
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    if "CLP" in t:
        h = h[h >= MINIMO_CLP_POR_USD]
    return h


def episodios(serie, minimo=CAIDA_MINIMA):
    """Todo retroceso de mas de `minimo` desde el maximo. Regla mecanica."""
    nav = serie / serie.iloc[0]
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


def _ret(s, a, b):
    s = s.reindex(pd.date_range(min(a, s.index.min()), max(b, s.index.max()), freq="D")).ffill()
    return float(s.loc[b] / s.loc[a] - 1)


def pct(v, d=2):
    return "   —   " if pd.isna(v) else f"{v:+.{d}%}".replace(".", ",")


def spearman(x, y):
    m = ~(pd.isna(x) | pd.isna(y))
    if m.sum() < 4:
        return np.nan, np.nan, int(m.sum())
    r = stats.spearmanr(np.asarray(x)[m], np.asarray(y)[m])
    return r.statistic, r.pvalue, int(m.sum())


def main():
    v = cuotas()
    mundo, em, fx = mercado("^990100-USD-STRD"), mercado("EEM"), mercado("USDCLP=X")
    mclp = (mundo * fx.reindex(mundo.index).ffill()).dropna()

    eps = episodios(v.A)
    print("#" * 78)
    print("# LOS EPISODIOS (regla mecanica: caida del Fondo A de mas de 10%)")
    print("#" * 78)
    print(f"  {len(eps)} episodios entre {v.index.min().date()} y {v.index.max().date()}\n")

    # --- beta unica, estimada sobre toda la muestra --------------------------
    # **El valor cuota del dia t refleja el mercado del dia t-1.** La covarianza
    # contemporanea es cero por construccion -beta 0,004 con t=0,5- asi que el
    # mercado va rezagado un dia. Sin esto la beta sale -0,000 y H2 corre
    # invalida: fue el primer resultado de esta corrida y estaba mal.
    # En ruedas de mercado, no en la grilla de calendario: los fines de semana
    # la cuota devenga y el mercado no, y esos ceros diluyen la covarianza.
    r_a = v.A.reindex(mclp.index).ffill().pct_change()
    r_m = mclp.pct_change().shift(1)
    j = pd.concat([r_a.rename("a"), r_m.rename("m")], axis=1).dropna()
    beta = j.cov().loc["a", "m"] / j.m.var()
    print(f"  beta del Fondo A al MSCI World en pesos: {beta:.3f}")
    print(f"  (una sola, sobre {len(j)} dias, con el mercado rezagado un dia;")
    print("   no se estima por episodio)\n")

    filas = []
    for a, b in eps:
        ra, re = _ret(v.A, a, b), _ret(v.E, a, b)
        rm, rfx = _ret(mclp, a, b), _ret(fx, a, b)
        try:
            rem = _ret(em, a, b) - _ret(mundo, a, b)
        except Exception:
            rem = np.nan
        if a < pd.Timestamp("2003-04-14"):
            rem = np.nan          # EEM no existe antes; escrito en HIPOTESIS.md
        filas.append({
            "inicio": a.date(), "fondo": b.date(),
            "dias": (b - a).days,
            "fondo_A": ra, "fondo_E": re,
            "beneficio": re - ra,                 # lo que aportaba cambiarse
            "peso": rfx,                          # + = el peso se debilita = hay colchon
            "mundo_clp": rm,
            "residuo": ra - beta * rm,            # lo que el mundo desarrollado no explica
            "em_vs_dev": rem,
        })
    t = pd.DataFrame(filas)

    print("#" * 78)
    print("# H1 — EL COLCHON DICE CUANTO VALE SALIRSE")
    print("#" * 78)
    print("  prediccion escrita antes: correlacion NEGATIVA entre el peso y el beneficio\n")
    print(f"  {'episodio':24} {'dias':>5} {'Fondo A':>9} {'Fondo E':>9} "
          f"{'beneficio':>10} {'peso':>9}")
    for r in t.sort_values("peso").itertuples():
        print(f"  {str(r.inicio) + ' a ' + str(r.fondo):24} {r.dias:>5} {pct(r.fondo_A):>9} "
              f"{pct(r.fondo_E):>9} {pct(r.beneficio):>10} {pct(r.peso):>9}")
    rho, p, n = spearman(t.peso.values, t.beneficio.values)
    print(f"\n  Spearman(peso, beneficio) = {rho:+.3f}   p = {p:.3f}   n = {n}")
    veredicto = ("CONFIRMA" if rho <= -.75 and p < .05 else
                 "no confirma (signo correcto, fuerza insuficiente)" if rho < 0 else
                 "REFUTA: el signo sale al reves")
    print(f"  -> {veredicto}")

    print("\n" + "#" * 78)
    print("# H2 — LOS EMERGENTES EXPLICAN EL RESIDUO")
    print("#" * 78)
    print("  prediccion escrita antes: correlacion POSITIVA entre residuo y em_vs_dev\n")
    print(f"  {'episodio':24} {'Fondo A':>9} {'explicado':>10} {'residuo':>9} {'em-dev':>9}")
    for r in t.sort_values("em_vs_dev").itertuples():
        print(f"  {str(r.inicio) + ' a ' + str(r.fondo):24} {pct(r.fondo_A):>9} "
              f"{pct(beta * r.mundo_clp):>10} {pct(r.residuo):>9} {pct(r.em_vs_dev):>9}")
    rho2, p2, n2 = spearman(t.residuo.values, t.em_vs_dev.values)
    print(f"\n  Spearman(residuo, em-dev) = {rho2:+.3f}   p = {p2:.3f}   n = {n2}")
    ver2 = ("CONFIRMA" if rho2 >= .75 and p2 < .05 else
            "no confirma (signo correcto, fuerza insuficiente)" if rho2 > 0 else
            "REFUTA: el signo sale al reves")
    print(f"  -> {ver2}")
    if n2 < len(t):
        print(f"  ({len(t) - n2} episodio sin datos de emergentes, como estaba escrito)")

    t.to_csv("research/afp_mecanismos/episodios.csv", index=False)
    print(f"\n  tabla completa en research/afp_mecanismos/episodios.csv")

    # --- replica en otra AFP -----------------------------------------------
    print("\n" + "#" * 78)
    print("# REPLICA EN HABITAT")
    print("#" * 78)
    v2 = cuotas("habitat")
    eps2 = episodios(v2.A)
    f2 = [{"beneficio": _ret(v2.E, a, b) - _ret(v2.A, a, b), "peso": _ret(fx, a, b)}
          for a, b in eps2]
    t2 = pd.DataFrame(f2)
    r3, p3, n3 = spearman(t2.peso.values, t2.beneficio.values)
    print(f"  {len(eps2)} episodios   Spearman(peso, beneficio) = {r3:+.3f}   p = {p3:.3f}")




# --- analisis secundario, NO pre-registrado --------------------------------

def secundario():
    """La severidad del episodio confunde las dos variables de H1.

    En la tabla se ve: el episodio con mayor beneficio de cambiarse (+57,23% en
    2008) es tambien el de mayor debilitamiento del peso (+23,83%). **Los dos
    los arrastra lo mismo: lo grande que fue la crisis.** Una crisis profunda
    debilita mas el peso Y hace que cambiarse aporte mas, en terminos absolutos.

    La hipotesis pre-registrada hablaba de «la caida que evitas», que es una
    magnitud absoluta, asi que la prueba de arriba es la fiel. Pero la pregunta
    de fondo -cuanto vale salirse- es una tasa, no un monto.

    **Esto no reemplaza la prueba pre-registrada. Va etiquetado como lo que es:
    una segunda mirada decidida despues de ver el resultado.**
    """
    v = cuotas()
    mundo, em, fx = mercado("^990100-USD-STRD"), mercado("EEM"), mercado("USDCLP=X")
    mclp = (mundo * fx.reindex(mundo.index).ffill()).dropna()
    r_a = v.A.reindex(mclp.index).ffill().pct_change()
    r_m = mclp.pct_change().shift(1)
    j = pd.concat([r_a.rename("a"), r_m.rename("m")], axis=1).dropna()
    beta = j.cov().loc["a", "m"] / j.m.var()

    filas = []
    for a, b in episodios(v.A):
        ra, re = _ret(v.A, a, b), _ret(v.E, a, b)
        rem = np.nan if a < pd.Timestamp("2003-04-14") else _ret(em, a, b) - _ret(mundo, a, b)
        filas.append({"inicio": a.date(), "fondo_A": ra,
                      "beneficio_por_punto": (re - ra) / abs(ra),
                      "peso": _ret(fx, a, b),
                      "residuo_por_punto": (ra - beta * _ret(mclp, a, b)) / abs(ra),
                      "em_vs_dev": rem})
    t = pd.DataFrame(filas)

    print("\n" + "#" * 78)
    print("# SECUNDARIO (no pre-registrado): normalizado por la severidad")
    print("#" * 78)
    print("  La severidad arrastra las dos variables de H1. Aca se mide la tasa:")
    print("  cuanto aporta cambiarse **por cada punto que cae el Fondo A**.\n")
    print(f"  {'episodio':12} {'cae el A':>10} {'peso':>9} {'beneficio por punto':>21}")
    for r in t.sort_values("peso").itertuples():
        print(f"  {str(r.inicio):12} {pct(r.fondo_A):>10} {pct(r.peso):>9} "
              f"{r.beneficio_por_punto:>20.2f}x")
    rho, p, n = spearman(t.peso.values, t.beneficio_por_punto.values)
    print(f"\n  Spearman(peso, beneficio por punto) = {rho:+.3f}   p = {p:.3f}   n = {n}")
    print(f"  (la prediccion de H1 seguia siendo signo NEGATIVO)")
    rho2, p2, n2 = spearman(t.residuo_por_punto.values, t.em_vs_dev.values)
    print(f"  Spearman(residuo por punto, em-dev) = {rho2:+.3f}   p = {p2:.3f}   n = {n2}")


if __name__ == "__main__":
    main()
    secundario()
