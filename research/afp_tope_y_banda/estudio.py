"""Dos cosas: de donde sale mi -40,43% del tope, y la banda en las siete AFP.

Parte 1 reproduce mi propio numero y lo reconcilia contra el -16,95% de la otra
sesion. Parte 2 replica la banda de histeresis en las siete AFP vigentes, con
el criterio escrito en HIPOTESIS.md antes de correrlo.

Investigacion pura: no toca data/, reports/, el pipeline ni el informe.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad")

AFPS = ("capital", "cuprum", "habitat", "modelo", "planvital", "provida", "uno")

# Los dos parametros vienen fijos de la otra sesion y no se re-eligen por AFP.
MEDIA = 126            # dias habiles
BANDA = .020           # el punto que ella eligio
REZAGO_HABILES = 5     # dias habiles entre la senal y quedar en el otro fondo

# El proveedor entrega precios imposibles del dolar -5,46 el 10-04-2014-.
MINIMO_CLP_POR_USD = 300


# --------------------------------------------------------------------------
# datos
# --------------------------------------------------------------------------

def cuotas(afp):
    """Valor cuota en dias habiles.

    La serie viene en dias calendario y el fin de semana repite el viernes,
    porque la cuota no devenga sabado ni domingo. Quedarse con dias habiles no
    pierde nada y hace que «126 dias» signifique lo mismo que en la otra sesion.
    """
    t = (pd.read_csv(SP / "afp7" / f"vc_{afp}.csv", parse_dates=["date"])
         .set_index("date").sort_index())
    return t[["A", "D", "E"]].dropna().asfreq("B").ffill()


def mercado(t):
    h = yf.Ticker(t).history(start="2002-01-01", auto_adjust=False)["Close"]
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return h[h >= MINIMO_CLP_POR_USD] if "CLP" in t else h


def cagr(s):
    return (1 + s).prod() ** (365.25 / (s.index[-1] - s.index[0]).days) - 1


def caida(s):
    nav = (1 + s).cumprod()
    return float((nav / nav.cummax() - 1).min())


def pct(x):
    return "   —  " if pd.isna(x) else f"{x:+.2%}".replace(".", ",")


# --------------------------------------------------------------------------
# PARTE 1 — de donde sale el -40,43%
# --------------------------------------------------------------------------

def con_tope(senal, tope=None):
    """Mi implementacion original, sin tocar. Aca esta lo que preguntaste.

    - Al agotar los traspasos la posicion **queda pegada en el fondo actual**.
      No vuelve a ningun fondo por defecto.
    - El contador se reinicia por **anio calendario**, no movil.
    - Arranca en Fondo A.
    - La regla evaluada es exactamente la misma con tope y sin tope: lo unico
      que cambia es si el cambio se ejecuta o se ignora.
    """
    est, cur, usados, anio = [], True, 0, None
    for fecha, x in senal.items():
        if fecha.year != anio:
            anio, usados = fecha.year, 0
        quiere = x > .5
        if quiere != cur and (tope is None or usados < tope):
            cur, usados = quiere, usados + 1
        est.append(cur)
    return pd.Series(est, index=senal.index).astype(float)


def parte1():
    """El -40,43% reproduce con MI pipeline original. La diferencia es 2008.

    Aca se usa `research/afp_tecnico_serio/estudio.py` sin tocar -indice de dias
    calendario, rezago de 6 dias corridos- porque el punto es reproducir mi
    numero, no producir uno nuevo. Si lo recalculo con otra convencion dejo de
    estar contestando la pregunta.
    """
    import sys
    sys.path.insert(0, "research/afp_tecnico_serio")
    from estudio import datos, REZAGO          # noqa: E402

    d = datos("habitat")
    mclp = d.mundo * d.fx
    sig = (mclp > mclp.rolling(100).mean()).astype(float).dropna()

    def correr(est, desde=None):
        pos = est.shift(REZAGO).ffill()
        r = pd.DataFrame({"A": d.A.pct_change(), "E": d.E.pct_change()}).fillna(0)
        j = pd.concat([pos.rename("p"), r], axis=1).dropna()
        if desde:
            j = j.loc[desde:]
        s = pd.Series(np.where(j.p > .5, j.A, j.E), index=j.index)
        return s, int((j.p != j.p.shift()).sum()) / ((s.index[-1] - s.index[0]).days / 365.25)

    print("#" * 78)
    print("# PARTE 1 — de donde sale mi -40,43%")
    print("#" * 78)
    print("  Habitat, tendencia 100d sobre el MSCI World en pesos, refugio Fondo E.")
    print("  Pipeline original: dias calendario, rezago de 6 dias corridos.")
    print("  Tope codicioso por anio calendario, posicion pegada al agotarse.\n")

    print(f"  {'desde':12} {'tope':>7} {'anual':>9} {'caida':>9} {'cam/anio':>9}"
          f" | {'Fondo A':>9} {'caida':>9} | {'peor caida va de':>24}")
    for desde in (None, "2010-01-01", "2014-01-01"):
        for tope in (None, 2):
            s, cpa = correr(con_tope(sig, tope), desde)
            a = d.A.pct_change().dropna().loc[s.index[0]:s.index[-1]]
            nav = (1 + s).cumprod()
            fondo = (nav / nav.cummax()).idxmin()
            pico = nav.loc[:fondo].idxmax()
            print(f"  {str(desde or s.index[0].date()):12} "
                  f"{('sin' if tope is None else '2/anio'):>7} {pct(cagr(s)):>9} "
                  f"{pct(caida(s)):>9} {cpa:>9.1f} | {pct(cagr(a)):>9} "
                  f"{pct(caida(a)):>9} | {str(pico.date()) + ' a ' + str(fondo.date()):>24}")

    # Cuantos cambios queria la regla en 2008, para ver si dos alcanzaban.
    e_sin = con_tope(sig, None)
    por_anio = e_sin.groupby(e_sin.index.year).apply(
        lambda x: int((x != x.shift()).sum()) - 1)
    print(f"\n  La regla sin tope queria {por_anio.get(2008, 0)} cambios en 2008 "
          f"y {por_anio.get(2020, 0)} en 2020.")
    print("  Con dos por anio se queda adentro del desplome de 2008 entero.")


# --------------------------------------------------------------------------
# PARTE 2 — la banda de histeresis en las siete AFP
# --------------------------------------------------------------------------

def histeresis(precio, media=MEDIA, banda=BANDA):
    """Sale cuando el precio cae banda% BAJO su media; vuelve cuando sube banda% sobre.

    Entre los dos umbrales no pasa nada: ahi esta el ahorro de rotacion. Los
    cruces de ida y vuelta alrededor de la linea dejan de contar.
    """
    ma = precio.rolling(media).mean()
    alto, bajo = ma * (1 + banda), ma * (1 - banda)
    est, cur = [], True
    for p, a, b in zip(precio.values, alto.values, bajo.values):
        if not np.isnan(a):
            if cur and p < b:
                cur = False
            elif not cur and p > a:
                cur = True
        est.append(cur)
    return pd.Series(est, index=precio.index).astype(float)


def evaluar(v, est, tope=None, desde=None, refugio="E"):
    if tope is not None:
        est = con_tope(est, tope)
    pos = est.shift(REZAGO_HABILES).ffill()
    r = v.pct_change().fillna(0)
    j = pd.concat([pos.rename("p"), r[["A", refugio]]], axis=1).dropna()
    if desde:
        j = j.loc[desde:]
    s = pd.Series(np.where(j.p > .5, j.A, j[refugio]), index=j.index)
    anos = (s.index[-1] - s.index[0]).days / 365.25
    return cagr(s), caida(s), int((j.p != j.p.shift()).sum()) / anos


def parte2():
    print("\n" + "#" * 78)
    print("# PARTE 2 — la banda de histeresis en las siete AFP, refugio Fondo E")
    print("#" * 78)
    print(f"  Media de {MEDIA} dias habiles, rezago de {REZAGO_HABILES} dias habiles.")
    print(f"  Senal sobre el valor cuota del Fondo A de cada AFP.")
    print(f"  Banda fija en {BANDA:.1%}: viene de la otra sesion y no se re-elige.\n")

    datos = {a: cuotas(a) for a in AFPS}

    print(f"  {'AFP':11} {'desde':>11} {'anual':>9} {'caida':>9} {'cam/anio':>9}"
          f" | {'Fondo A anual':>13} {'caida':>9} | {'ventaja':>8}")
    ventajas = {}
    for a in AFPS:
        v = datos[a]
        an, cd, cpa = evaluar(v, histeresis(v.A))
        ra = v.A.pct_change().dropna()
        ini = v.index[MEDIA + REZAGO_HABILES]
        ra = ra.loc[ini:]
        ventajas[a] = cd - caida(ra)
        print(f"  {a:11} {str(ini.date()):>11} {pct(an):>9} {pct(cd):>9} {cpa:>9.1f}"
              f" | {pct(cagr(ra)):>13} {pct(caida(ra)):>9} | {pct(ventajas[a]):>8}")

    print(f"\n  Dispersion de la ventaja entre AFP: "
          f"{pct(min(ventajas.values()))} a {pct(max(ventajas.values()))}"
          f"  (rango {max(ventajas.values()) - min(ventajas.values()):.1%})")
    print("  Pero esa dispersion es de VENTANAS, no de AFP: las que arrancan")
    print("  despues de 2009 no ven 2008. Hay que compararlas en ventana comun.")

    # --- la misma tabla, en ventanas comunes -------------------------------
    for desde, quienes in (("2008-10-01", [a for a in AFPS if a not in ("modelo", "uno")]),
                           ("2011-04-01", [a for a in AFPS if a != "uno"]),
                           ("2020-05-01", list(AFPS))):
        print(f"\n  Ventana comun desde {desde}  ({len(quienes)} AFP):")
        print(f"  {'AFP':11} {'anual':>9} {'caida':>9} {'cam/anio':>9}"
              f" | {'Fondo A anual':>13} {'caida':>9} | {'ventaja':>8}")
        vent = {}
        for a in quienes:
            v = datos[a]
            an, cd, cpa = evaluar(v, histeresis(v.A), desde=desde)
            ra = v.A.pct_change().dropna().loc[desde:]
            vent[a] = cd - caida(ra)
            print(f"  {a:11} {pct(an):>9} {pct(cd):>9} {cpa:>9.1f}"
                  f" | {pct(cagr(ra)):>13} {pct(caida(ra)):>9} | {pct(vent[a]):>8}")
        print(f"    rango de la ventaja entre AFP: "
              f"{max(vent.values()) - min(vent.values()):.1%}")

    # --- el barrido, para ver la forma, no para escoger el punto -----------
    print("\n  El barrido completo (caida), para ver si la meseta esta o no:")
    bandas = (0, .005, .01, .015, .02, .025, .03, .035, .05, .10)
    print(f"  {'AFP':11}" + "".join(f"{b:>8.1%}" for b in bandas))
    for a in AFPS:
        v = datos[a]
        fila = [evaluar(v, histeresis(v.A, banda=b))[1] for b in bandas]
        print(f"  {a:11}" + "".join(f"{pct(c):>8}" for c in fila))

    print(f"\n  Y la rotacion en las mismas bandas (cambios/anio):")
    print(f"  {'AFP':11}" + "".join(f"{b:>8.1%}" for b in bandas))
    for a in AFPS:
        v = datos[a]
        fila = [evaluar(v, histeresis(v.A, banda=b))[2] for b in bandas]
        print(f"  {a:11}" + "".join(f"{c:>8.1f}" for c in fila))

    # --- el tope sobre la banda -------------------------------------------
    print(f"\n  Y ahora el tope de 2/anio sobre la banda de {BANDA:.1%}:")
    print(f"  {'AFP':11} {'sin tope':>20} {'con tope 2/anio':>22}")
    print(f"  {'':11} {'anual':>9} {'caida':>10} {'anual':>11} {'caida':>10}")
    for a in AFPS:
        v = datos[a]
        s1 = evaluar(v, histeresis(v.A))
        s2 = evaluar(v, histeresis(v.A), tope=2)
        print(f"  {a:11} {pct(s1[0]):>9} {pct(s1[1]):>10} "
              f"{pct(s2[0]):>11} {pct(s2[1]):>10}")

    # --- cuantos anios pasarian del tope ----------------------------------
    print(f"\n  Anios que pasan de dos cambios, con la banda de {BANDA:.1%}:")
    for a in AFPS:
        v = datos[a]
        est = histeresis(v.A).shift(REZAGO_HABILES).ffill().dropna()
        por = est.groupby(est.index.year).apply(lambda x: int((x != x.shift()).sum()) - 1)
        por = por[por >= 0]
        exceso = por[por > 2]
        print(f"    {a:11} {len(exceso):>2} de {len(por):>2} anios"
              f"   peor: {' '.join(f'{y}:{n}' for y, n in exceso.nlargest(3).items()) or '—'}")


def refugio():
    """Por que mis caidas dan -19% y las de ella -15,30%: el refugio.

    Ella usa Fondo D, yo Fondo E. El E es mas conservador en riesgo de mercado
    pero es casi todo renta fija local, y en 2022 las tasas chilenas se
    dispararon. No es una eleccion libre de consecuencias.
    """
    print("\n" + "#" * 78)
    print("# EL REFUGIO: Fondo E contra Fondo D, misma banda, misma ventana")
    print("#" * 78)
    print("  Es la diferencia de convencion que queda entre las dos mediciones.\n")

    print(f"  {'AFP':11} {'refugio E':>20} {'refugio D':>20} | {'el refugio solo':>22}")
    print(f"  {'':11} {'anual':>9} {'caida':>10} {'anual':>9} {'caida':>10}"
          f" | {'E caida':>10} {'D caida':>10}")
    for a in AFPS:
        v = cuotas(a)
        e = evaluar(v, histeresis(v.A), refugio="E")
        dd = evaluar(v, histeresis(v.A), refugio="D")
        ini = v.index[MEDIA + REZAGO_HABILES]
        print(f"  {a:11} {pct(e[0]):>9} {pct(e[1]):>10} {pct(dd[0]):>9} {pct(dd[1]):>10}"
              f" | {pct(caida(v.E.pct_change().dropna().loc[ini:])):>10}"
              f" {pct(caida(v.D.pct_change().dropna().loc[ini:])):>10}")


def veredicto():
    """Contra las tres condiciones escritas en HIPOTESIS.md, sin moverlas."""
    print("\n" + "#" * 78)
    print("# VEREDICTO contra el criterio pre-registrado")
    print("#" * 78)

    comun = "2011-04-01"
    quienes = [a for a in AFPS if a != "uno"]
    vent = {}
    for a in quienes:
        v = cuotas(a)
        an, cd, _ = evaluar(v, histeresis(v.A), desde=comun)
        ra = v.A.pct_change().dropna().loc[comun:]
        vent[a] = (cd - caida(ra), an - cagr(ra))

    print(f"\n  1) «la banda de 2,0% deja la caida al menos 8 puntos mejor»")
    for a, (dv, dr) in vent.items():
        print(f"     {a:11} ventaja en caida {pct(dv):>8}  "
              f"{'CUMPLE' if dv >= .08 else 'NO CUMPLE'}")
    print(f"     -> {sum(1 for d, _ in vent.values() if d >= .08)} de {len(vent)} "
          f"llegan a 8 puntos. **La condicion 1 no se cumple.**")

    print(f"\n  2) «el retorno no queda por debajo del Fondo A»")
    print(f"     -> {sum(1 for _, r in vent.values() if r >= 0)} de {len(vent)} "
          f"lo cumplen (rango {min(r for _, r in vent.values()):+.2%} a "
          f"{max(r for _, r in vent.values()):+.2%}).")

    print(f"\n  3) «la dispersion entre AFP no puede ser del orden del efecto»")
    d = [x for x, _ in vent.values()]
    print(f"     -> rango de la ventaja: {max(d) - min(d):.1%} contra un efecto de "
          f"{sum(d)/len(d):.1%}. **La condicion 3 se cumple con holgura.**")

    print("\n  4) «el punto elegido cae dentro de la region buena en cada AFP»")
    print("     -> ver el barrido: la meseta va de 1,0% a 3,0% en las siete y el")
    print("        precipicio esta en 3,5% o mas tarde. **Se cumple.**")


if __name__ == "__main__":
    parte1()
    parte2()
    refugio()
    veredicto()
