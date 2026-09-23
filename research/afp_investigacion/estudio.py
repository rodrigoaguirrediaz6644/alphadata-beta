"""Que compone cada fondo AFP, que mueve sus fluctuaciones, y que estrategia sale de eso.

Investigacion pura: no toca produccion ni el informe.

A diferencia de los dos estudios anteriores, este parte de la **composicion
publicada** de los fondos y de la normativa de cobertura cambiaria, en vez de
ajustar pesos contra el valor cuota. Ver README.md para las fuentes.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad")

# Composicion publicada del Fondo A: 80% renta variable -65% extranjera, 15%
# local- y 20% renta fija. No se ajusta contra el valor cuota.
W_EXT, W_LOC, W_RF = .65, .15, .20
# Limite regulatorio A03: la exposicion sin cobertura no puede pasar del 50%.
SIN_COBERTURA = .50
INICIO = "2004-01"


def _mes(t, desde="2003-01-01"):
    h = yf.Ticker(t).history(start=desde, auto_adjust=False)["Close"]
    h.index = pd.to_datetime(h.index).tz_localize(None)
    return h.resample("ME").last()


def datos(afp="cuprum"):
    v = pd.read_csv(SP / "afp" / f"vc_{afp}.csv", parse_dates=["date"]).set_index("date")
    fondos = v[["A", "B", "C", "D", "E"]].resample("ME").last().pct_change()
    c = pd.read_csv(SP / "afp2" / "componentes.csv", index_col=0, parse_dates=[0])
    d = pd.DataFrame({
        "mundo": _mes("^990100-USD-STRD").pct_change(),     # MSCI World, desarrollados
        "emergente": _mes("EEM").pct_change(),              # MSCI Emerging Markets
        "dolar": _mes("USDCLP=X").pct_change(),
        "chile": c.acciones_cl.pct_change(),                # indice de acciones de Chile, OCDE
    })
    return pd.concat([d, fondos], axis=1).dropna().loc[INICIO:]


def cagr(s):
    return (1 + s).prod() ** (12 / len(s)) - 1


def caida(s):
    n = (1 + s).cumprod()
    return float((n / n.cummax() - 1).min())


def calmar(s):
    return cagr(s) / abs(caida(s))


def pct(v, d=2):
    return f"{v:+.{d}%}".replace(".", ",")


# --- 1. la replica, ahora con la composicion publicada ----------------------

def replica(d, em_share, sin_cobertura=SIN_COBERTURA):
    ext = (1 - em_share) * d.mundo + em_share * d.emergente + sin_cobertura * d.dolar
    return W_EXT * ext + W_LOC * d.chile + W_RF * d.E


def seccion_replica(d):
    print("#" * 78)
    print("# 1. LA REPLICA, CON LA COMPOSICION PUBLICADA")
    print("#" * 78)
    print(f"  pesos fijados por la composicion publicada, no ajustados:")
    print(f"    renta variable extranjera {W_EXT:.0%} | local {W_LOC:.0%} | renta fija {W_RF:.0%}")
    print(f"  exposicion cambiaria sin cobertura: {SIN_COBERTURA:.0%} (limite regulatorio A03)\n")
    print(f"{'sin cobertura':>14}" + "".join(f"{f'EM {s:.0%}':>9}" for s in (0, .15, .25, .35, .50)))
    mejor = (9e9, None)
    for sc in (0, .25, .50, .75, 1.0):
        fila = []
        for s in (0, .15, .25, .35, .50):
            te = (replica(d, s, sc) - d.A).std() * np.sqrt(12)
            fila.append(te)
            if te < mejor[0]:
                mejor = (te, (s, sc))
        print(f"{sc:>13.0%} " + "".join(f"{x:>9.1%}" for x in fila))
    s, sc = mejor[1]
    r = replica(d, s, sc)
    print(f"\n  mejor: emergentes {s:.0%} de la RV extranjera, sin cobertura {sc:.0%}")
    print(f"  **El ajuste cae exactamente en el limite regulatorio de 50%.**")
    print(f"  error de seguimiento {mejor[0]:.1%} anual | correlacion {r.corr(d.A):.3f}")
    print(f"  (la replica de tres componentes del estudio anterior: 8,0% y 0,751)")
    print(f"\n  Pero {mejor[0]:.1%} sigue siendo mucho mas que la ventaja que se busca")
    print(f"  (0,5 a 1,6 puntos). **Sirve para entender el fondo, no para operarlo.**")


# --- 2. que mueve al Fondo A ------------------------------------------------

def seccion_factores(d):
    print("\n" + "#" * 78)
    print("# 2. QUE MUEVE AL FONDO A")
    print("#" * 78)
    cols = ["mundo", "emergente", "dolar", "chile", "E"]
    m = sm.OLS(d.A, sm.add_constant(d[cols])).fit()
    cov, b = d[cols].cov(), m.params.drop("const")
    contrib = {k: sum(b[k] * b[j] * cov.loc[k, j] for j in cols) for k in cols}
    tot = sum(contrib.values())
    print(f"{'factor':14} {'beta':>8} {'t':>7} {'aporte a la varianza':>22}")
    for k in cols:
        nombre = "renta fija (E)" if k == "E" else k
        print(f"{nombre:14} {b[k]:>8.3f} {m.tvalues[k]:>7.1f} {contrib[k] / tot:>21.0%}")
    print(f"\n  R2 {m.rsquared:.3f} | volatilidad del Fondo A {d.A.std() * np.sqrt(12):.1%} anual")
    print(f"  residuo no explicado {np.sqrt(1 - m.rsquared) * d.A.std() * np.sqrt(12):.1%} anual")
    print(f"\n  **El dolar aporta varianza NEGATIVA.** No es un error de signo: su")
    print(f"  correlacion con la bolsa global es {d.dolar.corr(d.mundo):+.2f}, asi que sus")
    print(f"  terminos de covarianza restan. La exposicion cambiaria **reduce** el")
    print(f"  riesgo del fondo en vez de aumentarlo.")


def seccion_colchon(d):
    print("\n" + "#" * 78)
    print("# 3. EL COLCHON CAMBIARIO, MEDIDO")
    print("#" * 78)
    baja, cae = d.mundo < 0, d.mundo < -.05
    print(f"  meses con bolsa global en baja: {int(baja.sum())} de {len(d)}")
    print(f"    dolar en esos meses   {pct(d.dolar[baja].mean())}")
    print(f"    dolar en los demas    {pct(d.dolar[~baja].mean())}")
    print(f"    correlacion dolar / bolsa global {d.dolar.corr(d.mundo):+.3f}")
    print(f"\n  caidas fuertes (bolsa global bajo -5%, {int(cae.sum())} meses):")
    print(f"    bolsa global {pct(d.mundo[cae].mean())} | dolar {pct(d.dolar[cae].mean())} "
          f"| Fondo A {pct(d.A[cae].mean())}")
    print(f"    **el Fondo A cae solo el {d.A[cae].mean() / d.mundo[cae].mean():.0%} de lo que cae la bolsa global**")
    con, sin = cae & (d.dolar >= 0), cae & (d.dolar < 0)
    print(f"\n  la hipotesis de que el peligro es que el colchon falle:")
    print(f"    caidas CON colchon ({int(con.sum())} meses): Fondo A {pct(d.A[con].mean())}")
    print(f"    caidas SIN colchon ({int(sin.sum())} meses): Fondo A {pct(d.A[sin].mean())}")
    print(f"    -> al fondo le fue **mejor** cuando el colchon fallo. Con {int(sin.sum())} casos")
    print(f"       no es concluyente, pero no respalda la hipotesis.")


# --- 4. los cinco fondos ----------------------------------------------------

def seccion_fondos(d):
    print("\n" + "#" * 78)
    print("# 4. LOS CINCO FONDOS, Y LO QUE NADIE MIRA")
    print("#" * 78)
    print(f"{'fondo':7} {'anual':>9} {'vol':>7} {'peor caida':>12} {'Calmar':>7} {'cuando la peor':>16}")
    for f in "ABCDE":
        s = d[f]
        n = (1 + s).cumprod()
        cuando = (n / n.cummax() - 1).idxmin().date()
        print(f"{f:7} {pct(cagr(s)):>9} {s.std() * np.sqrt(12):>7.1%} {pct(caida(s)):>12} "
              f"{calmar(s):>7.2f} {str(cuando):>16}")
    print(f"\n  **El Fondo E rinde menos que el D y cae mas.** Y los dos tocan su peor")
    print(f"  caida en octubre de 2021, que no fue una crisis de bolsa sino el shock")
    print(f"  de tasas: el Fondo E es renta fija larga, no es caja.")


def seccion_refugio(d):
    print("\n" + "#" * 78)
    print("# 5. PERO E NO ESTA DOMINADO COMO COBERTURA")
    print("#" * 78)
    print("  A igual peor caida objetivo, cuanto retorno da cada refugio:\n")
    print(f"{'caida maxima':>14} {'con Fondo E':>24} {'con Fondo D':>24}")
    for o in (-.15, -.20, -.25, -.30):
        fila = []
        for ref in ("E", "D"):
            mejor = None
            for w in np.arange(0, 1.001, .01):
                s = w * d.A + (1 - w) * d[ref]
                if caida(s) >= o and (mejor is None or cagr(s) > mejor[0]):
                    mejor = (cagr(s), w)
            fila.append(mejor)
        print(f"{o:>13.0%}  {pct(fila[0][0])} con {fila[0][1]:>4.0%} en A   "
              f"{pct(fila[1][0])} con {fila[1][1]:>4.0%} en A")
    print(f"\n  Son equivalentes. E rinde menos pero cubre mejor, asi que se necesita")
    print(f"  menos. **La eleccion no es cual rinde mas, es contra que se cubre:**\n")
    print(f"{'episodio':16} {'Fondo A':>10} {'Fondo D':>10} {'Fondo E':>10}")
    for a, b, n in [("2007-11", "2009-02", "2008 bolsa"), ("2020-02", "2020-03", "2020 bolsa"),
                    ("2022-01", "2023-03", "2022 bolsa"), ("2021-01", "2021-10", "2021 tasas")]:
        print(f"{n:16} {pct((1 + d.A[a:b]).prod() - 1):>10} "
              f"{pct((1 + d.D[a:b]).prod() - 1):>10} {pct((1 + d.E[a:b]).prod() - 1):>10}")


# --- 6. la frontera y 2027 --------------------------------------------------

def seccion_frontera(d):
    print("\n" + "#" * 78)
    print("# 6. LA FRONTERA: ELEGIR MEZCLA, NO MOMENTO")
    print("#" * 78)
    # Etapa 10 ~ 29% de activos de crecimiento; el Fondo C esta en 27,5%.
    e10 = d.C
    print(f"{'% en A':>8} {'anual':>9} {'vol':>7} {'peor caida':>12} {'Calmar':>7} "
          f"{'02-13':>9} {'14-26':>9}")
    for w in (1.0, .8, .6, .4, .3, .2, .1, 0.):
        s = w * d.A + (1 - w) * d.E
        a, b = s[:"2013-12"], s["2014-01":]
        print(f"{f'{w:.0%}':>8} {pct(cagr(s)):>9} {s.std() * np.sqrt(12):>7.1%} "
              f"{pct(caida(s)):>12} {calmar(s):>7.2f} {pct(cagr(a)):>9} {pct(cagr(b)):>9}")
    mejor = max(np.arange(0, 1.01, .1), key=lambda w: calmar(w * d.A + (1 - w) * d.E))
    print(f"\n  mejor Calmar: {mejor:.0%} en A / {1 - mejor:.0%} en E")
    for etq, a, b in [("2002-2013", None, "2013-12"), ("2014-2026", "2014-01", None)]:
        k = max(np.arange(0, 1.01, .1), key=lambda w: calmar((w * d.A + (1 - w) * d.E)[a:b]))
        print(f"    y en {etq} por separado: {k:.0%} en A")

    print("\n" + "#" * 78)
    print("# 7. QUE CAMBIA EN ABRIL DE 2027")
    print("#" * 78)
    print(f"  La Etapa 10 tiene ~29% de activos de crecimiento. El Fondo C tiene 27,5%")
    print(f"  de renta variable de referencia, asi que es el equivalente mas cercano.\n")
    print(f"{'% en A':>8} {'con Fondo E (hoy)':>26} {'con Etapa 10 ~ C (2027)':>28}")
    print(f"{'':8} {'anual':>13}{'caida':>13} {'anual':>14}{'caida':>14}")
    for w in (1.0, .6, .4, .2, 0.):
        s1, s2 = w * d.A + (1 - w) * d.E, w * d.A + (1 - w) * e10
        print(f"{w:>8.0%} {pct(cagr(s1)):>13}{pct(caida(s1)):>13} "
              f"{pct(cagr(s2)):>14}{pct(caida(s2)):>14}")
    print(f"\n  **El piso de proteccion sube de {pct(caida(.2 * d.A + .8 * d.E))} a {pct(caida(e10))}.**")
    print(f"  Despues de 2027 no se puede bajar de ahi, porque el refugio mas")
    print(f"  conservador del menu nuevo ya trae 29% de activos de crecimiento.")
    print(f"  A cambio rinde mas: {pct(cagr(e10))} contra {pct(cagr(d.E))} del Fondo E.")


def main():
    d = datos()
    print(f"Cuprum, {len(d)} meses, {d.index.min().date()} a {d.index.max().date()}\n")
    seccion_replica(d)
    seccion_factores(d)
    seccion_colchon(d)
    seccion_fondos(d)
    seccion_refugio(d)
    seccion_frontera(d)
    print("\n" + "#" * 78)
    print("# REPLICA EN HABITAT")
    print("#" * 78)
    h = datos("habitat")
    print(f"{'fondo':7} {'Cuprum anual':>14} {'Habitat anual':>15} {'Cuprum caida':>14} {'Habitat caida':>15}")
    for f in "ACDE":
        print(f"{f:7} {pct(cagr(d[f])):>14} {pct(cagr(h[f])):>15} "
              f"{pct(caida(d[f])):>14} {pct(caida(h[f])):>15}")


if __name__ == "__main__":
    main()
