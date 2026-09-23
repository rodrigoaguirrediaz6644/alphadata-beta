"""Tres cosas: la especificacion diferenciada, los pares en las siete AFP, y 2027.

Parte 1 aisla la perilla que separa tu -15,56% de mi -21,83%. No es el refugio
ni el rezago: es que «126 dias» significa cosas distintas segun la grilla.

Parte 2 corre tu tabla de pares en las siete AFP, con A->C como proxy de 2027.

Parte 3 construye el par de 2027 -Fondo Inicial contra Consolidacion- como
mezcla sintetica de los multifondos que si existen, y mide lo que tu dijiste
que habia que mirar: la correlacion, no la volatilidad.

Investigacion pura: no toca data/, reports/, el pipeline ni el informe.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad")

AFPS = ("capital", "cuprum", "habitat", "modelo", "planvital", "provida", "uno")

BANDA = .02
# Tu convencion, la que reproduce tus numeros: grilla de dias corridos, media de
# 126 filas -o sea 126 dias corridos, unos 90 habiles- y la posicion desplazada
# 7 filas, que son los 5 dias habiles reales. Ver parte1() para por que importa.
MEDIA = 126
REZAGO = 7

# Los cinco pares ordenados por que tan defensivo es el refugio.
PARES = (("A", "E"), ("A", "D"), ("A", "C"), ("B", "D"), ("B", "C"))

# Limites maximos de renta variable de cada multifondo, DL 3.500. Son el ancla
# publica para traducir «activos de crecimiento» a una mezcla de fondos reales.
RV_MAXIMA = {"A": .80, "B": .60, "C": .40, "D": .20, "E": .05}

# Regimen de Inversion de los Fondos Generacionales, vigente el 01-04-2027.
# El 95% del fondo mas joven lo confirma la Superintendencia. El ~29% del fondo
# de Consolidacion viene de tu orden y NO lo pude verificar en la fuente, asi
# que se barre de 20% a 40% para no colgar la conclusion de un solo numero.
CRECIMIENTO_INICIAL = .95
CRECIMIENTO_CONSOLIDACION = .29


# --------------------------------------------------------------------------
# piezas
# --------------------------------------------------------------------------

def cuotas(afp, grilla="corrido"):
    t = (pd.read_csv(SP / "afp7" / f"vc_{afp}.csv", parse_dates=["date"])
         .set_index("date").sort_index()[["A", "B", "C", "D", "E"]].dropna())
    return t.asfreq("D").ffill() if grilla == "corrido" else t.asfreq("B").ffill()


def histeresis(precio, media=MEDIA, banda=BANDA):
    """Sale cuando precio/media-1 baja de -banda; vuelve cuando sube de +banda."""
    razon = precio / precio.rolling(media).mean() - 1
    est, cur = [], True
    for x in razon.values:
        if not np.isnan(x):
            if cur and x < -banda:
                cur = False
            elif not cur and x > banda:
                cur = True
        est.append(cur)
    return pd.Series(est, index=precio.index).astype(float)


def cagr(s):
    return (1 + s).prod() ** (365.25 / (s.index[-1] - s.index[0]).days) - 1


def caida(s):
    nav = (1 + s).cumprod()
    return float((nav / nav.cummax() - 1).min())


def pct(x):
    return "   —  " if pd.isna(x) else f"{x:+.2%}".replace(".", ",")


def correr(retornos, agr, ref, media=MEDIA, rezago=REZAGO, desde=None, hasta=None):
    """`retornos` trae las columnas de retorno; la senal va sobre el nivel de `agr`."""
    nivel = (1 + retornos[agr]).cumprod()
    pos = histeresis(nivel, media).shift(rezago).ffill()
    j = pd.concat([pos.rename("p"), retornos[[agr, ref]]], axis=1).dropna()
    j = j.loc[desde:hasta]
    s = pd.Series(np.where(j.p > .5, j[agr], j[ref]), index=j.index)
    anos = (s.index[-1] - s.index[0]).days / 365.25
    return s, int((j.p != j.p.shift()).sum()) / anos, j.p


# --------------------------------------------------------------------------
# PARTE 1 — la perilla
# --------------------------------------------------------------------------

def parte1():
    print("#" * 78)
    print("# PARTE 1 — la especificacion diferenciada: es la grilla, no el refugio")
    print("#" * 78)
    print("  Cuprum, banda 2%, refugio D, desde 2011-04-01. Tu numero: -15,56%.\n")

    t = (pd.read_csv(SP / "afp7" / "vc_cuprum.csv", parse_dates=["date"])
         .set_index("date").sort_index()[["A", "B", "C", "D", "E"]].dropna())
    hab, cor = t.asfreq("B").ffill(), t.asfreq("D").ffill()

    def uno(g, m, rez, ref):
        r = g.pct_change().fillna(0)
        s, cpa, _ = correr(r, "A", ref, media=m, rezago=rez, desde="2011-04-01")
        return caida(s), cpa

    casos = [
        (cor, 126, 5, "corridos", "126 filas = 126 corridos ~ 90 habiles", "5 corridos"),
        (cor, 126, 7, "corridos", "126 filas = 126 corridos ~ 90 habiles", "7 corridos = 5 habiles"),
        (hab, 90, 5, "habiles", " 90 filas =  90 habiles ~ 126 corridos", "5 habiles"),
        (hab, 126, 5, "habiles", "126 filas = 126 habiles ~ 176 corridos", "5 habiles"),
        (cor, 176, 7, "corridos", "176 filas = 176 corridos = 126 habiles", "7 corridos = 5 habiles"),
    ]
    print(f"  {'grilla':9} {'la media es':>38} {'rezago':>24} {'caida':>9} {'cam/anio':>9}")
    for g, m, rez, nm, dm, dr in casos:
        c, n = uno(g, m, rez, "D")
        print(f"  {nm:9} {dm:>38} {dr:>24} {c:>9.2%} {n:>9.1f}")

    print("\n  El rezago no mueve nada -5 o 7 filas dan lo mismo-. La media si.")
    print("  Tu «126 dias» son corridos; el mio eran habiles. Misma palabra,")
    print("  ventana efectiva de 90 contra 126 dias de cotizacion.\n")

    print("  Y el precipicio, en dias habiles efectivos, no esta donde creiamos:")
    print(f"  {'media (habiles)':>16}" + "".join(f"{m:>10}" for m in (45, 63, 90, 100, 110, 126, 150)))
    for ref in ("D", "E"):
        fila = [uno(hab, m, 5, ref)[0] for m in (45, 63, 90, 100, 110, 126, 150)]
        print(f"  {'refugio ' + ref:>16}" + "".join(f"{pct(c):>10}" for c in fila))
    print("\n  El salto esta entre 100 y 110 dias habiles. Tu barrido de 63/100/126")
    print("  corridos son 45/71/90 habiles: los tres caen antes del salto, por eso")
    print("  te parecio meseta. **La region buena termina alrededor de 100 habiles**")
    print("  y el punto elegido, leido en habiles, queda 26 dias despues del borde.")


# --------------------------------------------------------------------------
# PARTE 2 — los cinco pares en las siete AFP
# --------------------------------------------------------------------------

def parte2():
    print("\n" + "#" * 78)
    print("# PARTE 2 — los cinco pares en las siete AFP")
    print("#" * 78)
    print(f"  Banda {BANDA:.0%}, media {MEDIA} corridos, rezago {REZAGO} corridos"
          f" (= 5 habiles). Ventana 2004-2019.\n")

    datos = {a: cuotas(a).pct_change().fillna(0) for a in AFPS}
    D0, D1 = "2004-01-01", "2019-12-31"

    for agr, ref in PARES:
        print(f"  --- {agr} -> {ref}")
        print(f"    {'AFP':11} {'estrategia':>19} {'agresivo':>19} {'refugio':>19}"
              f" {'ventaja':>9} {'cam/anio':>9}")
        vent = []
        for a in AFPS:
            r = datos[a].loc[D0:D1]
            if len(r) < 500:
                print(f"    {a:11} {'sin historia en la ventana':>19}")
                continue
            s, cpa, _ = correr(datos[a], agr, ref, desde=D0, hasta=D1)
            ra, rr = r[agr], r[ref]
            v = caida(s) - caida(ra)
            vent.append(v)
            print(f"    {a:11} {pct(cagr(s))+' /'+pct(caida(s)):>19}"
                  f" {pct(cagr(ra))+' /'+pct(caida(ra)):>19}"
                  f" {pct(cagr(rr))+' /'+pct(caida(rr)):>19}"
                  f" {pct(v):>9} {cpa:>9.1f}")
        if vent:
            print(f"    {'':11} ventaja: mediana {np.median(vent):+.2%}"
                  f"  rango {max(vent) - min(vent):.2%}")
        print()


# --------------------------------------------------------------------------
# PARTE 3 — el par de 2027
# --------------------------------------------------------------------------

def sintetico(r, crecimiento):
    """Mezcla de Fondo A y Fondo E que iguala `crecimiento` de activos de riesgo.

    Se resuelve w * 80% + (1-w) * 5% = crecimiento, con los limites maximos de
    renta variable de cada multifondo como ancla. Es una aproximacion lineal: si
    el fondo real diversifica con algo que el Fondo E no tiene, su correlacion
    sera otra. Eso se dice y no se esconde.
    """
    w = (crecimiento - RV_MAXIMA["E"]) / (RV_MAXIMA["A"] - RV_MAXIMA["E"])
    return w * r["A"] + (1 - w) * r["E"], w


def sigue_cayendo(r, ref, posicion, dias=60):
    """Mediana de lo que hace el refugio en los `dias` siguientes a cada salida.

    Tu diagnostico, aplicado tal cual: un refugio sirve si deja de caer cuando
    uno llega, no si es tranquilo en promedio.
    """
    salidas = posicion[(posicion < .5) & (posicion.shift() >= .5)].index
    nivel = (1 + r[ref]).cumprod()
    out = []
    for f in salidas:
        i = nivel.index.searchsorted(f)
        if i + dias < len(nivel):
            out.append(nivel.iloc[i + dias] / nivel.iloc[i] - 1)
    return (float(np.median(out)) if out else np.nan), len(out)


def parte3():
    print("\n" + "#" * 78)
    print("# PARTE 3 — el par de 2027: Fondo Inicial contra Consolidacion")
    print("#" * 78)
    print(f"  Replica sintetica desde los limites: Inicial {CRECIMIENTO_INICIAL:.0%} de")
    print(f"  activos de crecimiento, Consolidacion {CRECIMIENTO_CONSOLIDACION:.0%}.")
    print("  La mezcla se arma con Fondo A y Fondo E reales (limites 80% y 5% de RV).\n")

    r = cuotas("cuprum").pct_change().fillna(0)
    D0, D1 = "2004-01-01", "2019-12-31"

    # --- primero tu diagnostico sobre los fondos que existen ---------------
    print("  Tu diagnostico, replicado en Cuprum (2004-2019):")
    print(f"    {'fondo':10} {'corr con A':>11} {'vol anual':>10} {'caida propia':>13}"
          f" {'sigue cayendo':>14}")
    _, _, pos = correr(r, "A", "E", desde=D0, hasta=D1)
    for f in ("B", "C", "D", "E"):
        rr = r.loc[D0:D1]
        sc, n = sigue_cayendo(r.loc[D0:D1], f, pos.loc[D0:D1])
        print(f"    {'Fondo ' + f:10} {rr[f].corr(rr.A):>11.3f} "
              f"{rr[f].std() * np.sqrt(365.25):>10.2%} {pct(caida(rr[f])):>13}"
              f" {pct(sc):>14}")
    print(f"    (sobre {n} salidas)\n")

    # --- ahora los sinteticos ----------------------------------------------
    print("  Y ahora el par de 2027, con la Consolidacion barrida 20%-40%:")
    print(f"    {'Consolidacion':>14} {'w en Fondo A':>13} {'corr con Inicial':>17}"
          f" {'vol anual':>10} {'caida propia':>13} {'sigue cayendo':>14}")
    ini, w_ini = sintetico(r, CRECIMIENTO_INICIAL)
    r2 = r.copy()
    r2["INI"] = ini
    for g in (.20, .25, CRECIMIENTO_CONSOLIDACION, .35, .40):
        con, w = sintetico(r, g)
        r2["CON"] = con
        _, _, p2 = correr(r2, "INI", "CON", desde=D0, hasta=D1)
        rr = r2.loc[D0:D1]
        sc, _ = sigue_cayendo(rr, "CON", p2.loc[D0:D1])
        marca = " <-" if abs(g - CRECIMIENTO_CONSOLIDACION) < 1e-9 else ""
        print(f"    {g:>13.0%}{marca:2} {w:>13.2f} {rr.CON.corr(rr.INI):>17.3f}"
              f" {rr.CON.std() * np.sqrt(365.25):>10.2%} {pct(caida(rr.CON)):>13}"
              f" {pct(sc):>14}")
    print(f"\n    (el Inicial sintetico pide w = {w_ini:.2f} en Fondo A: el fondo mas")
    print("     joven de 2027 es MAS agresivo que el Fondo A de hoy, no menos)\n")

    # --- la estrategia sobre el par sintetico -------------------------------
    print("  La estrategia sobre el par sintetico, contra los pares reales:")
    print(f"    {'par':22} {'estrategia':>19} {'agresivo':>19} {'ventaja':>9} {'cam/anio':>9}")
    filas = []
    for agr, ref in PARES:
        s, cpa, _ = correr(r, agr, ref, desde=D0, hasta=D1)
        filas.append((f"{agr} -> {ref}", s, r.loc[D0:D1][agr], cpa))
    for g in (.20, CRECIMIENTO_CONSOLIDACION, .40):
        con, _ = sintetico(r, g)
        r2["CON"] = con
        s, cpa, _ = correr(r2, "INI", "CON", desde=D0, hasta=D1)
        filas.append((f"Inicial -> Consol {g:.0%}", s, r2.loc[D0:D1]["INI"], cpa))
    for nombre, s, ra, cpa in filas:
        print(f"    {nombre:22} {pct(cagr(s))+' /'+pct(caida(s)):>19}"
              f" {pct(cagr(ra))+' /'+pct(caida(ra)):>19}"
              f" {pct(caida(s) - caida(ra)):>9} {cpa:>9.1f}")

    # --- la salvedad de la ventana ------------------------------------------
    print("\n  Tu salvedad, medida: el orden de los refugios se da vuelta por ventana.")
    print(f"    {'ventana':22} {'corr D-A':>10} {'corr E-A':>10}"
          f" {'caida D':>10} {'caida E':>10} {'mejor refugio':>15}")
    for d0, d1 in (("2004-01-01", "2019-12-31"), ("2011-04-01", "2026-09-20"),
                   ("2020-01-01", "2026-09-20")):
        rr = r.loc[d0:d1]
        sd, _, _ = correr(r, "A", "D", desde=d0, hasta=d1)
        se, _, _ = correr(r, "A", "E", desde=d0, hasta=d1)
        mejor = "E" if caida(se) > caida(sd) else "D"
        print(f"    {d0[:7] + ' a ' + d1[:7]:22} {rr.D.corr(rr.A):>10.3f}"
              f" {rr.E.corr(rr.A):>10.3f} {pct(caida(sd)):>10} {pct(caida(se)):>10}"
              f" {mejor:>15}")


if __name__ == "__main__":
    parte1()
    parte2()
    parte3()
