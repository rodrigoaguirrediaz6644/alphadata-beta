"""Estrategia de administracion A-E. Ver DISENO_CONGELADO.md y README.md.

Investigacion pura: no toca produccion ni el informe.

**La replica sintetica fallo** y esta parte del estudio lo documenta antes de
seguir: 8,0% anual de error de seguimiento contra una ventaja buscada de 0,5 a
1,6 puntos, y 44% de la varianza del Fondo A sin explicar. Con eso no se puede
ni sustituir al fondo ni extender la historia.

Lo que si se puede probar sin replica son los tres cambios de estructura:
**dos velocidades, exposicion graduada, y el colchon cambiario**. Las senales
rapida y del colchon salen de componentes -no necesitan replicar nada, solo ser
informativas- y los retornos se miden sobre los fondos reales.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import nnls

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad")

# El diseno congelado fijaba seleccion 1996-2002 sobre la replica. Al fallar la
# replica esa ventana no existe, y hay que caer a la de Chile, que el estudio
# anterior ya miro. Se dice en el README y no se disimula.
INI = pd.Timestamp("2004-01-31")
CORTE = pd.Timestamp("2014-01-01")
PISO_CAGR = .01
ETAPA10 = .29


def _me(t, ini="2003-01-01"):
    h = yf.Ticker(t).history(start=ini, auto_adjust=False)["Close"]
    h.index = pd.to_datetime(h.index).tz_localize(None)
    return h.resample("ME").last()


def datos():
    v = pd.read_csv(SP / "afp" / "vc_cuprum.csv", parse_dates=["date"]).set_index("date")
    A = v.A.resample("ME").last().pct_change()
    E = v.E.resample("ME").last().pct_change()
    mundo, fx = _me("^990100-USD-STRD"), _me("USDCLP=X")
    d = pd.DataFrame({
        "A": A, "E": E,
        # Renta variable global **en pesos**: es la moneda en que rinde el fondo.
        "rv_ext": (mundo * fx).pct_change(),
        "ret_clp": fx.pct_change(),
        "ret_mundo_usd": mundo.pct_change(),
    }).dropna()
    return d[d.index >= pd.Timestamp("2003-12-31")]


# --- la replica, que se documenta y se descarta ----------------------------

def diagnostico_replica():
    c = pd.read_csv(SP / "afp2" / "componentes.csv", index_col=0, parse_dates=[0])
    v = pd.read_csv(SP / "afp" / "vc_cuprum.csv", parse_dates=["date"]).set_index("date")
    A = v.A.resample("ME").last().pct_change()
    r = pd.DataFrame({"ext": (c.msci_world * c.clp).pct_change(),
                      "loc": c.acciones_cl.pct_change(),
                      "rf": c.tasa_corta_cl / 100 / 12})
    j = pd.concat([r, A.rename("real")], axis=1).dropna()
    C = j.loc["2002-08":"2013-12"]
    X, y, P = C[["ext", "loc", "rf"]].values, C.real.values, 1e3
    w, _ = nnls(np.vstack([X, np.ones((1, 3)) * P]), np.concatenate([y, [P]]))
    w = pd.Series(w / w.sum(), index=["ext", "loc", "rf"])
    rep = (j[["ext", "loc", "rf"]] * w).sum(axis=1)
    err = rep - j.real
    niv_r, niv_a = (1 + rep).cumprod(), (1 + j.real).cumprod()
    desac = {}
    for n in (6, 9, 12):
        d = pd.concat([(niv_r < niv_r.rolling(n).mean()),
                       (niv_a < niv_a.rolling(n).mean())], axis=1).dropna()
        desac[n] = (d.iloc[:, 0] != d.iloc[:, 1]).mean()
    return w, rep.corr(j.real), err.std(), j.real.std(), desac


# --- los tres mecanismos ---------------------------------------------------

def voto_lento(serie, n):
    nivel = (1 + serie).cumprod()
    return (nivel < nivel.rolling(n).mean()).astype(float)


def voto_rapido(rv_ext, u):
    """Histeresis: sale bajo -u%, vuelve cuando el mes es positivo."""
    fuera, estado = [], 0.
    for v in rv_ext:
        if estado == 0. and v < -u:
            estado = 1.
        elif estado == 1. and v > 0:
            estado = 0.
        fuera.append(estado)
    return pd.Series(fuera, index=rv_ext.index)


def voto_colchon(d, ventana=24):
    """Vota salir cuando el colchon cambiario deja de existir.

    Normalmente corr(retorno del peso, bolsa en USD) < 0: la bolsa cae, el
    dolar sube y el Fondo A recibe un amortiguador. El peligro es que caiga la
    bolsa **y el colchon no aparezca**. Umbral fijo en cero.
    """
    return (d.ret_clp.rolling(ventana).corr(d.ret_mundo_usd) > 0).astype(float)


def configuraciones(d):
    cfg, colchon = {}, voto_colchon(d)
    for n in (6, 9, 12):
        lento = voto_lento(d.A, n)
        for u in (.04, .06, .08):
            rapido = voto_rapido(d.rv_ext, u)
            cfg[f"L{n}-R{int(u * 100)}"] = (lento + rapido) / 2
            cfg[f"L{n}-R{int(u * 100)}-C"] = (lento + rapido + colchon) / 3
    return cfg


def correr(fuera, d, refugio, rezago=1):
    peso = (1 - fuera).shift(rezago)
    j = pd.concat([peso.rename("w"), d.A.rename("a"), refugio.rename("r")], axis=1).dropna()
    return (j.w * j.a + (1 - j.w) * j.r)[lambda s: s.index >= INI]


def cagr(s):
    return np.nan if len(s) < 12 else (1 + s).prod() ** (12 / len(s)) - 1


def caida(s):
    nav = (1 + s).cumprod()
    return float((nav / nav.cummax() - 1).min())


def tramo(s, a, b=None):
    x = s[s.index >= a]
    return x if b is None else x[x.index < b]


def pct(v):
    return "    —  " if pd.isna(v) else f"{v:+.2%}".replace(".", ",")


def main():
    print("#" * 78)
    print("# 1. LA REPLICA SINTETICA: por que no sirve")
    print("#" * 78)
    w, corr, te, vol, desac = diagnostico_replica()
    print(f"  pesos ajustados 2002-2013:  " + "  ".join(f"{k} {v:.0%}" for k, v in w.items()))
    print(f"  (el Fondo A tiene del orden de 15% en acciones locales, no 50%)")
    print(f"\n  correlacion mensual con el Fondo A real   {corr:.3f}")
    print(f"  varianza sin explicar                     {1 - corr ** 2:.0%}")
    print(f"  error de seguimiento                      {te:.2%} al mes = {te * np.sqrt(12):.1%} anual")
    print(f"  volatilidad del propio Fondo A            {vol:.2%} al mes")
    print(f"\n  desacuerdo de senal contra el fondo real:")
    for n, x in desac.items():
        print(f"    media de {n:2} meses: {x:.0%} de los meses")
    print(f"\n  **La ventaja que se busca es de 0,5 a 1,6 puntos anuales y el error")
    print(f"  de seguimiento es de 8 puntos.** La replica no puede sustituir al")
    print(f"  fondo ni, por lo tanto, extender la historia.")

    d = datos()
    print("\n" + "#" * 78)
    print("# 2. LA ARQUITECTURA, PROBADA SIN REPLICA")
    print("#" * 78)
    print(f"  {len(d)} meses, {d.index.min().date()} a {d.index.max().date()}")
    print(f"  seleccion {INI.date()}..2013-12  |  evaluacion 2014-01..{d.index.max().date()}")
    cfg = configuraciones(d)
    print(f"  {len(cfg)} configuraciones\n")

    ref = {"HOY (Fondo E)": d.E, "2027 (Etapa 10)": ETAPA10 * d.A + (1 - ETAPA10) * d.E}
    guardado = {}
    for mundo, refugio in ref.items():
        print("#" * 78)
        print(f"# 3. SELECCION -> EVALUACION   [{mundo}]")
        print("#" * 78)
        filas = []
        for nombre, fuera in cfg.items():
            s = correr(fuera, d, refugio)
            filas.append({"regla": nombre,
                          "sel_cagr": cagr(tramo(s, INI, CORTE)), "sel_caida": caida(tramo(s, INI, CORTE)),
                          "eva_cagr": cagr(tramo(s, CORTE)), "eva_caida": caida(tramo(s, CORTE))})
        t = pd.DataFrame(filas).set_index("regla")
        a = d.A[d.index >= INI]
        t.loc["FONDO A"] = [cagr(tramo(a, INI, CORTE)), caida(tramo(a, INI, CORTE)),
                            cagr(tramo(a, CORTE)), caida(tramo(a, CORTE))]
        rf = refugio[refugio.index >= INI]
        t.loc["REFUGIO"] = [cagr(tramo(rf, INI, CORTE)), caida(tramo(rf, INI, CORTE)),
                            cagr(tramo(rf, CORTE)), caida(tramo(rf, CORTE))]
        print(t.to_string(float_format=lambda v: f"{v:+.2%}"))
        reglas = t.drop(index=["FONDO A", "REFUGIO"])
        a_sel, a_eva = t.loc["FONDO A", "sel_cagr"], t.loc["FONDO A", "eva_cagr"]
        dd_eva = t.loc["FONDO A", "eva_caida"]
        print("\n--- que elige cada criterio en SELECCION ---")
        eleg = {"solo retorno": reglas.sel_cagr.idxmax(), "solo caida": reglas.sel_caida.idxmax()}
        aptas = reglas[reglas.sel_cagr >= a_sel - PISO_CAGR]
        if len(aptas):
            eleg["COMBINADO (pre-registrado)"] = (aptas.sel_cagr / aptas.sel_caida.abs()).idxmax()
        for crit, nombre in eleg.items():
            e = t.loc[nombre]
            print(f"\n  {crit}: **{nombre}**")
            print(f"    seleccion : {pct(e.sel_cagr)}  caida {pct(e.sel_caida)}   "
                  f"(Fondo A {pct(a_sel)} / {pct(t.loc['FONDO A','sel_caida'])})")
            print(f"    EVALUACION: {pct(e.eva_cagr)}  caida {pct(e.eva_caida)}   "
                  f"(Fondo A {pct(a_eva)} / {pct(dd_eva)})")
            print(f"    -> retorno {pct(e.eva_cagr - a_eva)} "
                  f"{'GANA' if e.eva_cagr > a_eva else 'PIERDE'} | "
                  f"caida {pct(e.eva_caida - dd_eva)} "
                  f"{'MEJORA' if e.eva_caida > dd_eva else 'EMPEORA'}")
        print(f"\n  ganan en retorno en EVALUACION: {int((reglas.eva_cagr > a_eva).sum())}/{len(reglas)}"
              f"   mejoran la caida: {int((reglas.eva_caida > dd_eva).sum())}/{len(reglas)}")
        guardado[mundo] = (t, eleg, refugio)
        print()

    # --- aporte de cada pieza, y episodios ---------------------------------
    t, eleg, refugio = guardado["HOY (Fondo E)"]
    print("#" * 78)
    print("# 4. QUE APORTA CADA PIEZA (evaluacion, refugio Fondo E)")
    print("#" * 78)
    a_eva, dd_eva = t.loc["FONDO A", "eva_cagr"], t.loc["FONDO A", "eva_caida"]
    lento_solo = {f"solo lento {n}": voto_lento(d.A, n) for n in (6, 9, 12)}
    rapido_solo = {f"solo rapido {int(u*100)}": voto_rapido(d.rv_ext, u) for u in (.04, .06, .08)}
    colchon_solo = {"solo colchon": voto_colchon(d)}
    print(f"{'pieza':20} {'anual':>10} {'peor caida':>12} {'vs A':>10} {'vs caida A':>12}")
    for nombre, f in {**lento_solo, **rapido_solo, **colchon_solo}.items():
        s = correr(f, d, refugio)
        print(f"{nombre:20} {pct(cagr(tramo(s, CORTE))):>10} {pct(caida(tramo(s, CORTE))):>12} "
              f"{pct(cagr(tramo(s, CORTE)) - a_eva):>10} {pct(caida(tramo(s, CORTE)) - dd_eva):>12}")
    print(f"{'FONDO A':20} {pct(a_eva):>10} {pct(dd_eva):>12}")

    print("\n" + "#" * 78)
    print("# 5. LOS EPISODIOS")
    print("#" * 78)
    nivel = (1 + d.A[d.index >= INI]).cumprod()
    pico, eps, ini = nivel.cummax(), [], None
    for f, v in (nivel < pico).items():
        if v and ini is None:
            ini = f
        elif not v and ini is not None:
            x = nivel.loc[ini:f]
            if 1 - x.min() / nivel.loc[:ini].max() >= .10:
                eps.append((ini, x.idxmin()))
            ini = None
    if ini is not None:
        x = nivel.loc[ini:]
        if 1 - x.min() / nivel.loc[:ini].max() >= .10:
            eps.append((ini, x.idxmin()))
    comb = eleg.get("COMBINADO (pre-registrado)")
    s_comb = correr(cfg[comb], d, refugio)
    print(f"{'episodio':24} {'meses':>6} {'velocidad':>10} {'Fondo A':>10} {'Fondo E':>10} {'elegida':>10}")
    for x, y in eps:
        m = (y.to_period("M") - x.to_period("M")).n
        vel = "rapida" if m <= 3 else ("media" if m <= 9 else "lenta")
        print(f"{str(x.date()) + ' a ' + str(y.date()):24} {m:>6} {vel:>10} "
              f"{pct(nivel.loc[y] / nivel.loc[:x].max() - 1):>10} "
              f"{pct((1 + d.E.loc[x:y]).prod() - 1):>10} "
              f"{pct((1 + s_comb.loc[x:y]).prod() - 1):>10}")

    print("\n" + "#" * 78)
    print("# 6. SENSIBILIDAD AL REZAGO (meses)")
    print("#" * 78)
    print(f"{'regla':18}" + "".join(f"{k:>13}m" for k in (1, 2, 3)))
    for nombre in [comb] + [k for k in list(cfg)[:5] if k != comb]:
        c = [cagr(tramo(correr(cfg[nombre], d, refugio, k), CORTE)) for k in (1, 2, 3)]
        print(f"{nombre:18}" + "".join(f"{pct(x):>14}" for x in c)
              + ("  <- elegida" if nombre == comb else ""))
    print(f"{'FONDO A':18}" + "".join(f"{pct(a_eva):>14}" for _ in (1, 2, 3)))


if __name__ == "__main__":
    main()
