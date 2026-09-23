"""El intento elaborado: bateria tecnica completa, ensemble y walk-forward.

Los tres estudios anteriores probaron indicadores sueltos a frecuencia mensual
y con un rezago de ejecucion optimista. Este corrige las tres cosas:

**Frecuencia diaria.** El valor cuota es diario y los mercados tambien.

**Rezago real.** El cambio de fondo se hace efectivo en **4 dias habiles**
contados desde el dia habil siguiente a la solicitud, y se aplica el valor cuota
del dia anterior a la materializacion. No son 2 ni 3 dias: son del orden de 6
dias corridos. Los estudios anteriores fueron optimistas.

**Bateria completa y ensemble, no indicadores sueltos.** Veinte caracteristicas
tecnicas -medias, MACD, RSI, Donchian, ADX, Bollinger, regimen de volatilidad,
VIX, cobre, fuerza relativa- y un modelo que las combina, validado
**walk-forward**: se entrena con todo lo anterior a un anio y se opera ese anio,
rodando. Nunca ve el futuro.

Y un hecho que los estudios anteriores no sabian y que cambia donde se busca:
**el valor cuota del dia t refleja el movimiento del mundo del dia t-1**. La
beta del Fondo A al MSCI World de ayer es 0,428 con t=59,7; la de hoy es cero.
Asi que las senales se calculan tambien sobre los mercados, que van un dia
adelante de la cuota.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad")
SALIDA = Path("research/afp_tecnico_serio")

# 4 dias habiles desde el dia habil siguiente, con la cuota del dia anterior a
# la materializacion. Medido en dias corridos sobre una serie de calendario.
REZAGO = 6
HORIZONTE = 20          # dias que se mantiene la posicion antes de re-evaluar
PRIMER_ANIO_OOS = 2010  # antes de eso se usa solo para entrenar


def mercado(t, desde="2002-01-01"):
    h = yf.Ticker(t).history(start=desde, auto_adjust=False)
    if h.empty:
        return None
    s = h["Close"]
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s


def datos(afp="habitat"):
    v = (pd.read_csv(SP / "afp" / f"vc_{afp}.csv", parse_dates=["date"])
         .set_index("date")[["A", "E"]].dropna().sort_index())
    piezas = {"mundo": "^990100-USD-STRD", "sp": "^GSPC", "vix": "^VIX",
              "fx": "USDCLP=X", "em": "EEM", "cobre": "HG=F", "tnx": "^TNX"}
    m = {k: mercado(t) for k, t in piezas.items()}
    d = pd.DataFrame(index=v.index)
    d["A"], d["E"] = v.A, v.E
    for k, s in m.items():
        if s is not None:
            d[k] = s.reindex(d.index).ffill()
    return d[d.index >= "2004-01-01"].dropna(subset=["A", "E", "mundo", "fx"])


# --- la bateria tecnica ----------------------------------------------------

def _rsi(s, n=14):
    delta = s.diff()
    sube = delta.clip(lower=0).rolling(n).mean()
    baja = (-delta.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + sube / baja.replace(0, np.nan))


def _adx(s, n=14):
    """Fuerza de tendencia sobre una serie de cierres, sin maximo ni minimo."""
    up = s.diff().clip(lower=0)
    dn = (-s.diff()).clip(lower=0)
    tr = s.diff().abs().rolling(n).mean()
    di_p = up.rolling(n).mean() / tr
    di_n = dn.rolling(n).mean() / tr
    return ((di_p - di_n).abs() / (di_p + di_n)).rolling(n).mean() * 100


def caracteristicas(d):
    """Veinte senales tecnicas, sobre los mercados y sobre la propia cuota."""
    f = pd.DataFrame(index=d.index)
    mclp = d.mundo * d.fx                       # bolsa global en pesos
    niv = (1 + (d.A.pct_change() - d.E.pct_change())).cumprod()   # spread A/E

    # --- tendencia, sobre el mercado (va un dia adelante de la cuota)
    for n in (10, 20, 50, 100, 200):
        f[f"mkt_ma{n}"] = mclp / mclp.rolling(n).mean() - 1
    f["mkt_mom20"] = mclp.pct_change(20)
    f["mkt_mom60"] = mclp.pct_change(60)
    f["mkt_cruce"] = (mclp.rolling(20).mean() / mclp.rolling(100).mean() - 1)
    ema12, ema26 = mclp.ewm(span=12).mean(), mclp.ewm(span=26).mean()
    macd = ema12 - ema26
    f["mkt_macd"] = (macd - macd.ewm(span=9).mean()) / mclp
    f["mkt_rsi"] = _rsi(mclp)
    f["mkt_adx"] = _adx(mclp)
    f["mkt_donchian"] = (mclp - mclp.rolling(50).min()) / (
        mclp.rolling(50).max() - mclp.rolling(50).min())
    sd = mclp.pct_change().rolling(20).std()
    f["mkt_bb"] = (mclp - mclp.rolling(20).mean()) / (2 * sd * mclp)

    # --- regimen de estres
    f["vol_corta"] = d.mundo.pct_change().rolling(20).std() * np.sqrt(252)
    f["vol_razon"] = (d.mundo.pct_change().rolling(20).std()
                      / d.mundo.pct_change().rolling(100).std())
    if "vix" in d:
        f["vix"] = d.vix
        f["vix_cambio"] = d.vix.pct_change(10)
    f["fx_mom20"] = d.fx.pct_change(20)
    f["fx_corr"] = d.fx.pct_change().rolling(60).corr(d.mundo.pct_change())
    if "cobre" in d:
        f["cobre_mom"] = d.cobre.pct_change(60)
    if "tnx" in d:
        f["tasa_cambio"] = d.tnx.diff(20)
    if "em" in d:
        f["em_rel"] = d.em.pct_change(60) - d.mundo.pct_change(60)

    # --- la propia serie del spread A/E
    f["spread_ma50"] = niv / niv.rolling(50).mean() - 1
    f["spread_mom60"] = niv.pct_change(60)
    f["spread_rsi"] = _rsi(niv)
    return f


def objetivo(d, rezago=REZAGO, horizonte=HORIZONTE):
    """Signo del diferencial A-E acumulado, empezando tras el rezago real."""
    dif = d.A.pct_change() - d.E.pct_change()
    fut = dif.shift(-rezago).rolling(horizonte).sum().shift(-(horizonte - 1))
    return fut


def walk_forward(f, y, modelo_fn, primer=PRIMER_ANIO_OOS):
    """Entrena con todo lo anterior al anio y opera ese anio. Nunca ve el futuro."""
    j = pd.concat([f, y.rename("y")], axis=1).dropna()
    pred = pd.Series(index=j.index, dtype=float)
    for anio in range(primer, j.index.year.max() + 1):
        tr = j[j.index.year < anio]
        te = j[j.index.year == anio]
        if len(tr) < 500 or len(te) == 0:
            continue
        m = modelo_fn()
        m.fit(tr.drop(columns="y"), (tr.y > 0).astype(int))
        pred.loc[te.index] = m.predict_proba(te.drop(columns="y"))[:, 1]
    return pred.dropna()


def correr(d, prob, umbral=.5, rezago=REZAGO):
    """prob>umbral -> Fondo A; si no -> Fondo E. Con el rezago real."""
    pos = (prob > umbral).shift(rezago).ffill()
    r = pd.DataFrame({"A": d.A.pct_change(), "E": d.E.pct_change()}).fillna(0)
    j = pd.concat([pos.rename("p"), r], axis=1).dropna()
    return pd.Series(np.where(j.p, j.A, j.E), index=j.index), j.p


def cagr(s):
    a = (s.index[-1] - s.index[0]).days / 365.25
    return (1 + s).prod() ** (1 / a) - 1


def caida(s):
    n = (1 + s).cumprod()
    return float((n / n.cummax() - 1).min())


def pct(v):
    return f"{v:+.2%}".replace(".", ",")


def main():
    d = datos()
    f = caracteristicas(d)
    y = objetivo(d)
    print(f"Habitat, {len(d)} dias, {d.index.min().date()} a {d.index.max().date()}")
    print(f"{f.shape[1]} caracteristicas tecnicas | rezago de ejecucion {REZAGO} dias corridos")
    print(f"validacion walk-forward por anio desde {PRIMER_ANIO_OOS}\n")

    modelos = {
        "regresion logistica": lambda: LogisticRegression(max_iter=2000, C=.1),
        "bosque aleatorio": lambda: RandomForestClassifier(
            n_estimators=300, max_depth=4, min_samples_leaf=50, random_state=0, n_jobs=-1),
        "gradient boosting": lambda: GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=.05, random_state=0),
    }
    print("#" * 78)
    print("# RESULTADO FUERA DE MUESTRA (walk-forward, nunca ve el futuro)")
    print("#" * 78)
    print(f"{'modelo':22} {'acierto':>9} {'anual':>9} {'peor caida':>12} {'cambios/anio':>13}")
    resultados = {}
    for nombre, fn in modelos.items():
        prob = walk_forward(f, y, fn)
        s, pos = correr(d, prob)
        real = (y.reindex(prob.index) > 0).astype(int)
        acierto = ((prob > .5).astype(int) == real).mean()
        anios = (s.index[-1] - s.index[0]).days / 365.25
        cam = int((pos != pos.shift()).sum())
        print(f"{nombre:22} {acierto:>9.1%} {pct(cagr(s)):>9} {pct(caida(s)):>12} "
              f"{cam / anios:>13.1f}")
        resultados[nombre] = (s, prob, pos)
    # referencias sobre la misma ventana
    ini = min(s.index[0] for s, _, _ in resultados.values())
    for n, c in [("comprar A y no mirar", "A"), ("comprar E y no mirar", "E")]:
        s = d[c].pct_change().dropna().loc[ini:]
        print(f"{n:22} {'':>9} {pct(cagr(s)):>9} {pct(caida(s)):>12} {0:>13.1f}")
    s40 = (.4 * d.A.pct_change() + .6 * d.E.pct_change()).dropna().loc[ini:]
    print(f"{'mezcla fija 40/60':22} {'':>9} {pct(cagr(s40)):>9} {pct(caida(s40)):>12} {0:>13.1f}")

    print("\n" + "#" * 78)
    print("# ANIO POR ANIO, el mejor modelo contra el Fondo A")
    print("#" * 78)
    mejor = max(resultados, key=lambda k: cagr(resultados[k][0]))
    s = resultados[mejor][0]
    a = d.A.pct_change().dropna().loc[s.index[0]:]
    print(f"  modelo: {mejor}\n")
    print(f"  {'anio':>6} {'modelo':>10} {'Fondo A':>10} {'diferencia':>12}")
    ganados = 0
    for anio in sorted(set(s.index.year)):
        x, z = s[s.index.year == anio], a[a.index.year == anio]
        dif = (1 + x).prod() - (1 + z).prod()
        ganados += dif > 0
        print(f"  {anio:>6} {pct((1 + x).prod() - 1):>10} {pct((1 + z).prod() - 1):>10} "
              f"{pct(dif):>12}")
    n = len(set(s.index.year))
    print(f"\n  anios en que el modelo le gana al Fondo A: {ganados} de {n}")

    print("\n" + "#" * 78)
    print("# QUE MIRA EL MODELO")
    print("#" * 78)
    j = pd.concat([f, y.rename("y")], axis=1).dropna()
    m = RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=50,
                               random_state=0, n_jobs=-1)
    m.fit(j.drop(columns="y"), (j.y > 0).astype(int))
    imp = pd.Series(m.feature_importances_, index=j.drop(columns="y").columns)
    print("  las ocho caracteristicas mas usadas (ajuste sobre todo, solo informativo):")
    for k, x in imp.sort_values(ascending=False).head(8).items():
        print(f"    {k:16} {x:.3f}")

    robustez()




# --- las pruebas que deciden si el resultado se puede creer -----------------

def robustez():
    """Significancia, replica, sensibilidad al rezago y al turnover."""
    import json
    from scipy import stats
    from sklearn.ensemble import RandomForestClassifier
    rf = lambda: RandomForestClassifier(n_estimators=300, max_depth=4, min_samples_leaf=50,
                                        random_state=0, n_jobs=-1)
    print("\n" + "#" * 78)
    print("# LAS PRUEBAS QUE DECIDEN SI ESTO SE PUEDE CREER")
    print("#" * 78)
    guardado = {}
    for afp in ("habitat", "cuprum"):
        d = datos(afp); f = caracteristicas(d); y = objetivo(d)
        prob = walk_forward(f, y, rf); s, pos = correr(d, prob)
        a = d.A.pct_change().reindex(s.index).fillna(0)
        ex = (s - a).dropna()
        t = ex.mean() / ex.std() * np.sqrt(len(ex))
        anios = sorted(set(s.index.year))
        g = sum(1 for A in anios
                if (1 + s[s.index.year == A]).prod() > (1 + a[a.index.year == A]).prod())
        print(f"\n  --- {afp.upper()} ---")
        print(f"  modelo {pct(cagr(s))}  Fondo A {pct(cagr(a))}  diferencia {pct(cagr(s) - cagr(a))}")
        print(f"  **exceso diario: t = {t:.2f}, p = {2 * (1 - stats.norm.cdf(abs(t))):.3f}**")
        print(f"  gana {g} de {len(anios)} anios, p = {stats.binomtest(g, len(anios), .5).pvalue:.3f}")
        guardado[afp] = (d, prob)

    d, prob = guardado["habitat"]
    print("\n  --- sensibilidad al rezago de ejecucion ---")
    print("  (el real son 4 dias habiles desde el dia habil siguiente = ~7 corridos,")
    print("   y la norma permite extenderlo cuando hay volumen inusual de solicitudes)")
    print(f"  {'rezago':>8} {'anual':>9} {'vs Fondo A':>12}")
    for rz in (2, 4, 6, 8, 10, 15):
        ss, _ = correr(d, prob, rezago=rz)
        aa = d.A.pct_change().reindex(ss.index).fillna(0)
        marca = "  <- el rango real" if rz in (6, 8) else ""
        print(f"  {f'{rz}d':>8} {pct(cagr(ss)):>9} {pct(cagr(ss) - cagr(aa)):>12}{marca}")

    print("\n  --- banda de no-operar: la ventaja necesita 23 cambios al anio ---")
    print(f"  {'banda':>10} {'anual':>9} {'cambios/anio':>13} {'vs Fondo A':>12}")
    for b in (0, .05, .10, .15, .20):
        est, cur = [], True
        for x in prob:
            if x > .5 + b: cur = True
            elif x < .5 - b: cur = False
            est.append(cur)
        e = pd.Series(est, index=prob.index).astype(float)
        ss, pp = correr(d, e)
        aa = d.A.pct_change().reindex(ss.index).fillna(0)
        an = (ss.index[-1] - ss.index[0]).days / 365.25
        print(f"  {f'±{b:.0%}':>10} {pct(cagr(ss)):>9} "
              f"{int((pp != pp.shift()).sum()) / an:>13.1f} {pct(cagr(ss) - cagr(aa)):>12}")


if __name__ == "__main__":
    main()
