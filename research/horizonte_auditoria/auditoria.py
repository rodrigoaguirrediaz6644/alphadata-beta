"""Auditoria de Horizonte. No la disena: la revisa contra lo que ya publica.

El orden es el de que invalida el resultado si esta mal. Todo lo que hace es
leer y medir; **no toca produccion ni escribe nada del repositorio**.

Usa las funciones de `src.horizonte` donde puede, para que lo que se audita sea
el codigo que corre y no una reimplementacion que se le parezca.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from src.horizonte import START, TEST_START, backtest, metrics, monthly_features

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/horizonte")


def cargar():
    c = pd.read_csv(SP / "cuotas_crudas.csv", parse_dates=["date"])
    c = c[["date", "a", "e"]].dropna().sort_values("date")
    ext = pd.read_csv(SP / "fred.csv", parse_dates=["date"])
    return c, ext


def pct(v):
    return f"{v:+.2%}".replace(".", ",")


def _resumen(serie, desde, hasta=None):
    m = metrics(serie, desde, hasta)
    return m["cagr"], m["max_drawdown"], m["cumulative_return"]


# --- 3. Reproduce? ---------------------------------------------------------

def reproduce(cuotas, ext):
    print("#" * 70)
    print("# 3. REPRODUCE?")
    print("#" * 70)
    f = monthly_features(cuotas, ext)
    r, trades = backtest(cuotas, f)
    publicado = pd.read_csv("data/horizonte_backtest_summary.csv")
    filas = []
    alternativas = {
        "Estrategia Horizonte": r,
        "Fondo A Cuprum": cuotas.set_index("date")["a"].pct_change().fillna(0),
        "Fondo E Cuprum": cuotas.set_index("date")["e"].pct_change().fillna(0),
        "Cuprum 50/50": cuotas.set_index("date")[["a", "e"]].pct_change().mean(axis=1).fillna(0),
    }
    for nombre, serie in alternativas.items():
        for periodo, desde in [("completo_desde_2012", START), ("fuera_muestra_2021+", TEST_START)]:
            m = metrics(serie, desde)
            p = publicado[(publicado.strategy == nombre) & (publicado.period == periodo)]
            filas.append({
                "estrategia": nombre, "periodo": periodo,
                "cagr_recalculado": m["cagr"],
                "cagr_publicado": float(p.cagr.iloc[0]) if len(p) else np.nan,
            })
    d = pd.DataFrame(filas)
    d["desvio"] = d.cagr_recalculado - d.cagr_publicado
    print(d.to_string(index=False, float_format=lambda v: f"{v:.6f}"))
    peor = d.desvio.abs().max()
    print(f"\nDesvio maximo: {peor:.2e}  ->  {'REPRODUCE' if peor < 1e-6 else 'NO REPRODUCE'}")
    return f, r, trades


# --- 4. El rezago del cambio de fondo --------------------------------------

def _backtest_con_rezago(cuotas, features, rezago):
    """El mismo backtest de produccion con otro rezago de ejecucion.

    Produccion usa `searchsorted(..., 'right') + 3`, o sea la cuarta fecha
    posterior a la senal. Las cuotas son **diarias de calendario**, asi que
    eso son 4 dias corridos y no 4 habiles.
    """
    daily = cuotas.set_index("date").sort_index()
    returns = daily[["a", "e"]].pct_change().fillna(0)
    objetivos, actual = {}, None
    for fecha, fila in features.dropna(subset=["recommendation"]).iterrows():
        destino = str(fila["recommendation"])
        if destino == actual:
            continue
        pos = daily.index.searchsorted(fecha, side="right") + rezago - 1
        if pos >= len(daily):
            continue
        objetivos[daily.index[pos]] = destino
        actual = destino
    eventos = pd.Series(objetivos, dtype="object").sort_index()
    tenencia = eventos.reindex(daily.index).ffill().dropna()
    return pd.Series(np.where(tenencia.eq("A"), returns.loc[tenencia.index, "a"],
                              returns.loc[tenencia.index, "e"]), index=tenencia.index)


def rezago(cuotas, features):
    print("\n" + "#" * 70)
    print("# 4. EL REZAGO DEL CAMBIO DE FONDO")
    print("#" * 70)
    print("Produccion ejecuta al 4o dia corrido tras la senal.\n")
    filas = []
    for d in [1, 2, 3, 4, 5, 7, 10, 15]:
        s = _backtest_con_rezago(cuotas, features, d)
        for etiqueta, desde in [("completo", START), ("fuera de muestra", TEST_START)]:
            cagr, dd, _ = _resumen(s, desde)
            filas.append({"rezago_dias": d, "ventana": etiqueta, "cagr": cagr, "peor_caida": dd})
    t = pd.DataFrame(filas)
    print(t.pivot(index="rezago_dias", columns="ventana", values="cagr")
          .to_string(float_format=lambda v: f"{v:.4%}"))
    return t


# --- 5. La prueba nula, con 2008 adentro -----------------------------------

def nula(cuotas, ext):
    print("\n" + "#" * 70)
    print("# 5. LA PRUEBA NULA, Y LA DECADA QUE EL BACKTEST NO MIRA")
    print("#" * 70)
    f = monthly_features(cuotas, ext)
    r, _ = backtest(cuotas, f)
    daily = cuotas.set_index("date")
    alt = {
        "Horizonte": r,
        "Fondo A": daily["a"].pct_change().fillna(0),
        "Fondo E": daily["e"].pct_change().fillna(0),
        "50/50": daily[["a", "e"]].pct_change().mean(axis=1).fillna(0),
    }
    ventanas = [
        ("todo lo medible (2003-08+)", pd.Timestamp("2003-08-01"), None),
        ("la decada excluida (2003-2012)", pd.Timestamp("2003-08-01"), START),
        ("la crisis (2007-2010)", pd.Timestamp("2007-01-01"), pd.Timestamp("2010-01-01")),
        ("el backtest publicado (2012-08+)", START, None),
        ("fuera de muestra (2021+)", TEST_START, None),
    ]
    filas = []
    for etiqueta, desde, hasta in ventanas:
        for nombre, serie in alt.items():
            s = serie[serie.index >= desde]
            if hasta is not None:
                s = s[s.index < hasta]
            if len(s) < 60:
                continue
            m = metrics(s, s.index.min())
            filas.append({"ventana": etiqueta, "cartera": nombre,
                          "anual": m["cagr"], "peor_caida": m["max_drawdown"]})
    t = pd.DataFrame(filas)
    for etiqueta in t.ventana.unique():
        sub = t[t.ventana == etiqueta].set_index("cartera")
        print(f"\n--- {etiqueta} ---")
        print(sub[["anual", "peor_caida"]].to_string(float_format=lambda v: f"{v:+.2%}"))
        h, a = sub.loc["Horizonte", "anual"], sub.loc["Fondo A", "anual"]
        print(f"    Horizonte contra Fondo A: {h - a:+.2%} anual  "
              f"-> {'GANA' if h > a else 'PIERDE'}")
    return t


# --- Sensibilidad de los umbrales ------------------------------------------

def _con_umbrales(cuotas, ext, vix=30, corte=2, ventana_ma=6, momento=12):
    q = cuotas.set_index("date").resample("ME").last().dropna()
    q = q[q.index.to_period("M") < cuotas["date"].max().to_period("M")]
    x = q.join(ext.set_index("date").resample("ME").last(), how="left")
    ra, re = x["a"].pct_change(momento, fill_method=None), x["e"].pct_change(momento, fill_method=None)
    s = pd.DataFrame({
        "relative_momentum": ra > re,
        "absolute_momentum": ra > 0,
        "cuprum_a_trend": x["a"] > x["a"].rolling(ventana_ma).mean(),
        "nasdaq_trend": x["nasdaq"] > x["nasdaq"].rolling(ventana_ma).mean(),
        "vix_below_30": x["vix"] < vix,
    })
    x["score"] = s.astype(int).sum(axis=1)
    valido = x[["a", "e", "nasdaq", "vix"]].notna().all(axis=1) & ra.notna() & re.notna()
    x["recommendation"] = pd.NA
    x.loc[valido, "recommendation"] = np.where(x.loc[valido, "score"] >= corte, "A", "E")
    return backtest(cuotas, x)[0]


def sensibilidad(cuotas, ext):
    print("\n" + "#" * 70)
    print("# SENSIBILIDAD DE LOS UMBRALES")
    print("#" * 70)
    print("Sin registro de donde salieron, la unica forma de sondear si estan")
    print("afinados es ver si el resultado depende mucho de ellos.\n")
    base = metrics(_con_umbrales(cuotas, ext), START)["cagr"]
    fondo_a = metrics(cuotas.set_index("date")["a"].pct_change().fillna(0), START)["cagr"]
    print(f"base (VIX 30, corte 2, MA 6, momento 12): {base:+.2%} anual "
          f"| Fondo A: {fondo_a:+.2%}\n")
    for nombre, variantes in [
        ("umbral del VIX", [("VIX 20", dict(vix=20)), ("VIX 25", dict(vix=25)),
                            ("VIX 30", dict(vix=30)), ("VIX 35", dict(vix=35)),
                            ("VIX 40", dict(vix=40))]),
        ("corte del score", [(f"score >= {k}", dict(corte=k)) for k in (1, 2, 3, 4)]),
        ("ventana de la media", [(f"MA {k}", dict(ventana_ma=k)) for k in (3, 6, 9, 12)]),
        ("ventana de momento", [(f"momento {k}", dict(momento=k)) for k in (6, 9, 12, 15)]),
    ]:
        print(f"--- {nombre} ---")
        for etiqueta, kw in variantes:
            s = _con_umbrales(cuotas, ext, **kw)
            c = metrics(s, START)["cagr"]
            f = metrics(s, TEST_START)["cagr"]
            marca = "  <- produccion" if not kw or list(kw.values())[0] in (30, 2, 6, 12) and len(kw) == 1 and etiqueta in ("VIX 30", "score >= 2", "MA 6", "momento 12") else ""
            print(f"  {etiqueta:14} completo {c:+.2%}   fuera de muestra {f:+.2%}"
                  f"   contra Fondo A {c - fondo_a:+.2%}{marca}")
        print()


def main():
    cuotas, ext = cargar()
    print(f"cuotas: {len(cuotas)} dias, {cuotas.date.min().date()} a {cuotas.date.max().date()}")
    print(f"FRED:   {len(ext)} dias, {ext.date.min().date()} a {ext.date.max().date()}\n")
    features, _, trades = reproduce(cuotas, ext)
    rezago(cuotas, features)
    nula(cuotas, ext)
    sensibilidad(cuotas, ext)
    print("\n" + "#" * 70)
    print(f"# Cambios de fondo en todo el backtest: {int(trades.is_switch.sum())}")
    print("#" * 70)


if __name__ == "__main__":
    main()
