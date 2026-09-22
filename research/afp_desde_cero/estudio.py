"""Estrategia de fondos AFP, desde cero. Ver DISENO_CONGELADO.md.

Investigacion pura: no toca data/, reports/, el pipeline ni el informe.

El resultado principal **no es un CAGR**: es la tabla de episodios. Una regla
defensiva pasa la mayor parte del tiempo sin hacer nada, y un promedio sobre
esos tramos no mide la regla, mide al Fondo A.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/afp")

INICIO = pd.Timestamp("2002-08-01")
CORTE = pd.Timestamp("2014-01-01")      # seleccion antes, evaluacion desde
CAIDA_MINIMA = .10                      # que cuenta como episodio
# El valor cuota se publica con 2 dias corridos de rezago, medido contra 40
# versiones del repositorio fuente. Ejecutar antes de 3 dias es imposible en la
# practica; 1 y 2 se reportan solo para ver la sensibilidad.
REZAGO_BASE = 3
REZAGOS = [1, 2, 3, 5, 10]


# --- datos -----------------------------------------------------------------

def cuotas(afp):
    d = pd.read_csv(SP / f"vc_{afp}.csv", parse_dates=["date"])
    d = d[["date", "A", "E"]].dropna().sort_values("date").set_index("date")
    return d[d.index >= INICIO]


def mercado_en_pesos():
    w = pd.read_csv(SP / "msci_world.csv", parse_dates=["date"]).set_index("date").valor
    fx = pd.read_csv(SP / "usdclp.csv", parse_dates=["date"]).set_index("date").valor
    j = pd.concat({"w": w, "fx": fx}, axis=1).sort_index().ffill(limit=5).dropna()
    return j.w * j.fx


# --- las tres familias -----------------------------------------------------

def familia_1(q, n):
    """Tendencia de la propia serie del fondo. Sin dato externo."""
    m = q["A"].resample("ME").last().dropna()
    return (m > m.rolling(n).mean()).rename(f"propia-{n}m")


def familia_2(q, n, mercado):
    """Tendencia del mercado que compone al fondo, medida en pesos."""
    m = mercado.resample("ME").last().dropna()
    s = (m > m.rolling(n).mean())
    return s.reindex(q["A"].resample("ME").last().dropna().index).rename(f"mercado-{n}m")


def familia_3(q, p):
    """Regimen de volatilidad, con percentil expandido y no sobre todo el periodo."""
    r = q["A"].pct_change()
    vol = r.rolling(60).std() * np.sqrt(252)
    mv = vol.resample("ME").last().dropna()
    umbral = mv.expanding(min_periods=24).quantile(p / 100)
    return (mv < umbral).rename(f"vol-p{p}")


def configuraciones(q, mercado):
    c = {}
    for n in (3, 6, 9, 12):
        c[f"propia-{n}m"] = familia_1(q, n)
    for n in (3, 6, 9, 12):
        c[f"mercado-{n}m"] = familia_2(q, n, mercado)
    for p in (70, 80, 90, 95):
        c[f"vol-p{p}"] = familia_3(q, p)
    return c


# --- el backtest -----------------------------------------------------------

def correr(q, senal, rezago=REZAGO_BASE):
    """`senal` es booleana mensual: True = Fondo A, False = Fondo E."""
    ret = q.pct_change().fillna(0)
    objetivo = {}
    for fecha, en_a in senal.dropna().items():
        pos = q.index.searchsorted(fecha, side="right") + rezago - 1
        if pos >= len(q):
            continue
        objetivo[q.index[pos]] = "A" if en_a else "E"
    ev = pd.Series(objetivo, dtype="object").sort_index()
    ten = ev.reindex(q.index).ffill().dropna()
    return pd.Series(np.where(ten.eq("A"), ret.loc[ten.index, "A"], ret.loc[ten.index, "E"]),
                     index=ten.index), ten


def anual(r):
    if len(r) < 30:
        return np.nan
    nav = (1 + r).cumprod()
    a = max((nav.index[-1] - nav.index[0]).days / 365.25, 1 / 365.25)
    return nav.iloc[-1] ** (1 / a) - 1


def peor_caida(r):
    nav = (1 + r).cumprod()
    return float((nav / nav.cummax() - 1).min())


def tramo(r, desde, hasta=None):
    s = r[r.index >= desde]
    return s if hasta is None else s[s.index < hasta]


# --- episodios -------------------------------------------------------------

def episodios(serie_a, minimo=CAIDA_MINIMA):
    """Todo retroceso del Fondo A de mas de `minimo` desde su maximo."""
    nav = serie_a / serie_a.iloc[0]
    pico = nav.cummax()
    bajo = nav < pico
    eps, ini = [], None
    for f, en_caida in bajo.items():
        if en_caida and ini is None:
            ini = f
        elif not en_caida and ini is not None:
            t = nav.loc[ini:f]
            if 1 - t.min() / nav.loc[:ini].max() >= minimo:
                eps.append((ini, t.idxmin(), f))
            ini = None
    if ini is not None:
        t = nav.loc[ini:]
        if 1 - t.min() / nav.loc[:ini].max() >= minimo:
            eps.append((ini, t.idxmin(), nav.index[-1]))
    return eps


def pct(v):
    return "  —  " if pd.isna(v) else f"{v:+.1%}".replace(".", ",")


def main():
    q = cuotas("cuprum")
    mercado = mercado_en_pesos()
    print(f"Cuprum: {len(q)} dias, {q.index.min().date()} a {q.index.max().date()}")
    print(f"Mercado en pesos: desde {mercado.index.min().date()}\n")

    cfg = configuraciones(q, mercado)
    fondo_a = q["A"].pct_change().fillna(0)
    fondo_e = q["E"].pct_change().fillna(0)

    print("#" * 78)
    print("# 1. LOS EPISODIOS: caidas del Fondo A de mas de 10%")
    print("#" * 78)
    eps = episodios(q["A"])
    print(f"{'episodio':24} {'dias al fondo':>14} {'velocidad':>12} {'Fondo A':>9} {'Fondo E':>9}")
    tabla_eps = []
    for ini, fondo, fin in eps:
        dias = (fondo - ini).days
        vel = "rapida" if dias <= 90 else ("media" if dias <= 270 else "lenta")
        ca = q["A"].loc[fondo] / q["A"].loc[:ini].max() - 1
        ce = q["E"].loc[fondo] / q["E"].loc[:ini].max() - 1
        etiqueta = f"{ini.date()} a {fondo.date()}"
        print(f"{etiqueta:24} {dias:>14} {vel:>12} {pct(ca):>9} {pct(ce):>9}")
        tabla_eps.append((ini, fondo, fin, dias, vel, ca, ce))
    print(f"\n**{len(eps)} episodios en 24 anios.** Ese es el tamanio de muestra real.")

    print("\n" + "#" * 78)
    print("# 2. QUE HIZO CADA REGLA EN CADA EPISODIO")
    print("#" * 78)
    print("Retorno desde el maximo previo hasta el fondo del Fondo A.\n")
    resultados = {n: correr(q, s)[0] for n, s in cfg.items()}
    cab = f"{'regla':14}" + "".join(f"{i.year:>8}" for i, *_ in tabla_eps)
    print(cab)
    print(f"{'Fondo A':14}" + "".join(f"{pct(c):>8}" for *_, c, _ in tabla_eps))
    print(f"{'Fondo E':14}" + "".join(f"{pct(c):>8}" for *_, c in tabla_eps))
    print("-" * len(cab))
    for nombre, r in resultados.items():
        celdas = []
        for ini, fondo, _, _, _, _, _ in tabla_eps:
            s = tramo(r, q["A"].loc[:ini].idxmax(), fondo)
            celdas.append(pct((1 + s).prod() - 1 if len(s) > 5 else np.nan))
        print(f"{nombre:14}" + "".join(f"{c:>8}" for c in celdas))

    print("\n" + "#" * 78)
    print("# 3. SELECCION (2002-2013) Y EVALUACION (2014-2026)")
    print("#" * 78)
    filas = []
    for nombre, r in resultados.items():
        filas.append({
            "regla": nombre,
            "sel_anual": anual(tramo(r, INICIO, CORTE)),
            "sel_caida": peor_caida(tramo(r, INICIO, CORTE)),
            "eva_anual": anual(tramo(r, CORTE)),
            "eva_caida": peor_caida(tramo(r, CORTE)),
        })
    for nombre, s in [("Fondo A", fondo_a), ("Fondo E", fondo_e)]:
        filas.append({"regla": nombre,
                      "sel_anual": anual(tramo(s, INICIO, CORTE)),
                      "sel_caida": peor_caida(tramo(s, INICIO, CORTE)),
                      "eva_anual": anual(tramo(s, CORTE)),
                      "eva_caida": peor_caida(tramo(s, CORTE))})
    t = pd.DataFrame(filas).set_index("regla")
    print(t.to_string(float_format=lambda v: f"{v:+.2%}"))

    a_sel, a_eva = t.loc["Fondo A", "sel_anual"], t.loc["Fondo A", "eva_anual"]
    reglas = t.drop(index=["Fondo A", "Fondo E"])
    mejor = reglas.sel_anual.idxmax()
    print(f"\nLa mejor en SELECCION por retorno: **{mejor}** ({reglas.loc[mejor,'sel_anual']:+.2%} "
          f"contra {a_sel:+.2%} del Fondo A)")
    print(f"  y en EVALUACION esa misma regla hace {reglas.loc[mejor,'eva_anual']:+.2%} "
          f"contra {a_eva:+.2%}  ->  "
          f"{'GANA' if reglas.loc[mejor,'eva_anual']>a_eva else 'PIERDE'}")
    menor_caida = reglas.sel_caida.idxmax()
    print(f"\nLa mejor en SELECCION por peor caida: **{menor_caida}** "
          f"({reglas.loc[menor_caida,'sel_caida']:+.2%} contra {t.loc['Fondo A','sel_caida']:+.2%})")
    print(f"  y en EVALUACION: {reglas.loc[menor_caida,'eva_caida']:+.2%} contra "
          f"{t.loc['Fondo A','eva_caida']:+.2%}  ->  "
          f"{'PROTEGE' if reglas.loc[menor_caida,'eva_caida']>t.loc['Fondo A','eva_caida'] else 'NO PROTEGE'}")
    print(f"\nReglas que le ganan al Fondo A en retorno en EVALUACION: "
          f"{int((reglas.eva_anual > a_eva).sum())} de {len(reglas)}")
    print(f"Reglas que reducen la peor caida en EVALUACION: "
          f"{int((reglas.eva_caida > t.loc['Fondo A','eva_caida']).sum())} de {len(reglas)}")

    print("\n" + "#" * 78)
    print("# 4. EL COSTO EN CALMA: lo que resta el seguro cuando no pasa nada")
    print("#" * 78)
    en_episodio = pd.Series(False, index=q.index)
    for ini, _, fin, *_ in tabla_eps:
        en_episodio.loc[ini:fin] = True
    calma = ~en_episodio
    print(f"dias en calma: {int(calma.sum())} de {len(q)} ({calma.mean():.0%})\n")
    print(f"{'regla':14} {'anual en calma':>16} {'contra Fondo A':>16} {'cambios':>9}")
    a_calma = anual(fondo_a[calma.reindex(fondo_a.index).fillna(False)])
    print(f"{'Fondo A':14} {a_calma:>+16.2%} {'—':>16}")
    for nombre, r in resultados.items():
        c = calma.reindex(r.index).fillna(False)
        _, ten = correr(q, cfg[nombre])
        cambios = int((ten != ten.shift()).sum()) - 1
        print(f"{nombre:14} {anual(r[c]):>+16.2%} {anual(r[c]) - a_calma:>+16.2%} {cambios:>9}")

    print("\n" + "#" * 78)
    print("# 5. EL REZAGO")
    print("#" * 78)
    print("Publicacion medida contra 40 versiones del repositorio fuente: 2 dias")
    print("corridos en 39 de 40. Ejecutar a 1 o 2 dias es imposible; van por")
    print("sensibilidad, no como opcion.\n")
    print(f"{'regla':14}" + "".join(f"{d:>10}d" for d in REZAGOS))
    for nombre, s in cfg.items():
        celdas = [anual(tramo(correr(q, s, d)[0], CORTE)) for d in REZAGOS]
        print(f"{nombre:14}" + "".join(f"{c:>+10.2%}" for c in celdas))
    print(f"{'Fondo A':14}" + "".join(f"{a_eva:>+10.2%}" for _ in REZAGOS))

    print("\n" + "#" * 78)
    print("# 6. REPLICA EN OTRA AFP (Habitat)")
    print("#" * 78)
    q2 = cuotas("habitat")
    cfg2 = configuraciones(q2, mercado)
    a2 = q2["A"].pct_change().fillna(0)
    print(f"{'regla':14} {'eval Cuprum':>13} {'eval Habitat':>14} {'vs A Cuprum':>13} {'vs A Habitat':>14}")
    a2_eva = anual(tramo(a2, CORTE))
    for nombre in cfg:
        r2 = correr(q2, cfg2[nombre])[0]
        e1, e2 = t.loc[nombre, "eva_anual"], anual(tramo(r2, CORTE))
        print(f"{nombre:14} {e1:>+13.2%} {e2:>+14.2%} {e1 - a_eva:>+13.2%} {e2 - a2_eva:>+14.2%}")
    print(f"{'Fondo A':14} {a_eva:>+13.2%} {a2_eva:>+14.2%}")


if __name__ == "__main__":
    main()
