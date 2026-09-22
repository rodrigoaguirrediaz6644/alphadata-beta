"""Aporte marginal al conjunto: cual cuarta pieza suma, si alguna.

Sigma-6 no es una estrategia independiente: es una de cuatro piezas. Un
retroceso alto no es un defecto si no coincide con los de las otras tres.

Los cuatro candidatos, fijados antes de medir:

- A  Sigma-6 v2.3.0, la actual: Credicorp, momentum 12-1 > 0, sobre SMA200,
     tope 10%, semanal.
- B  Consenso-6: las seis de v1.0.0, suma de senales, entrada con neto
     positivo, peso proporcional, tope 10%, salida con neto no positivo o 365
     dias.
- C  Formula inicial del libro v6: calidad historica con shrinkage hacia 50%,
     decaimiento de vigencia a 180 dias, confianza, liquidez, tope 12%, tope
     5% para baja liquidez, maximo 12 posiciones. **Con las catorce corredoras
     de cien recomendaciones o mas**, no con las seis.
- D  Sin corredora: solo momentum 12-1 y SMA200, top 10 al 10%. Es el piso.
- CAJA  El control: la cuarta pieza al 25% en caja y nada mas. La firma de los
     cuatro candidatos es la misma —bajan el retorno y suben el Sharpe— y eso
     es lo que hace agregar caja. Si el control da el mismo Sharpe, lo que
     aporta la cuarta pieza es la caja y no la seleccion.

**Las dos convenciones, que hasta ahora no estaban escritas en ninguna parte:**

- **La caja rinde 0%.** El NAV solo se mueve con las posiciones; el peso en caja
  no acredita nada. Vale para las cuatro piezas y para el control.
- **El Sharpe usa tasa libre de riesgo 0**: media de los retornos diarios por
  252, dividida por la desviacion tipica anualizada.

No es un detalle de forma. Con esas dos convenciones, agregar caja escala
retorno y volatilidad por el mismo factor y **deberia ser neutro al Sharpe por
construccion**. Si el control vuelve plano, los aportes de A, B y D son
seleccion de verdad; si sube, son caja.

Cortes: seleccion hasta 31-12-2023, evaluacion desde 01-01-2024.
Costos: Trii 0,1785% con minimo $999,99; en lo estadounidense 0,1% sin minimo.
Capital: $20 millones, $5.000.000 por pieza, con $10 millones de sensibilidad.

Dos desviaciones que hay que declarar:

1. El archivo no trae precio objetivo. El termino de precision de target (peso
   0,2) y la penalizacion por dispersion de targets **no se pueden calcular**.
   Sustituirlos por sus valores por defecto —0,5 y 0,75— hunde la confianza por
   debajo de su propio umbral de 0,50 y la formula no abre ninguna posicion en
   cinco anos. Lo correcto al faltar un termino es **renormalizar los pesos**
   (0,5 acierto + 0,5 exceso) y no penalizar una dispersion que no se conoce.
   Aun asi, C corre sin uno de sus tres componentes y eso hay que tenerlo
   presente al leer su resultado.
2. La formula original rebalancea a diario. Aca corre sobre el mismo calendario
   semanal que los demas candidatos, para que el modelo de costo sea
   comparable.
"""
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from src.fetch_prices import load_universe
from src.nav_historico import _reasignar
from src.strategy_engine import (ALIAS_TICKERS, capped_pro_rata, combined_equal_weight,
                                 delta12, gamma6, oro, sigma6, to_clp)

ZIP = ("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
       "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/corredoras/data/"
       "final_validated_recommendations.csv")
INICIO, CORTE, FIN = pd.Timestamp("2021-07-08"), pd.Timestamp("2024-01-01"), pd.Timestamp("2026-07-15")
TASA_CL, MIN_CL, TASA_US = .001785, 999.99, .001
SEIS = ["Credicorp Capital", "BICE", "Itaú", "BTG Pactual", "MBI", "LarrainVial Estudios"]
DECAIMIENTO, SHRINK, CONF_MIN, MIN_OPINIONES, MAX_POS, TOPE_C, TOPE_ILIQUIDO = 180, 20, .50, 2, 12, .12, .05


def correr(panel, sesiones, objetivos, capital, tasa, minimo):
    pesos, caja, valor = {}, 1., 100.
    por_fecha, filas, ops = dict(objetivos), [], 0
    anterior = None
    for s in sesiones:
        if anterior is None:
            filas.append((s, valor)); anterior = s; continue
        r = {t: panel.at[s, t] / panel.at[anterior, t] - 1 for t in pesos
             if t in panel.columns and pd.notna(panel.at[anterior, t])
             and pd.notna(panel.at[s, t]) and panel.at[anterior, t] > 0}
        dia = sum(w * r.get(t, 0.) for t, w in pesos.items())
        valor *= 1 + dia
        if pesos:
            f = 1 + dia
            pesos = {t: w * (1 + r.get(t, 0.)) / f for t, w in pesos.items()}
            caja /= f
        if s in por_fecha:
            nuevos, nueva_caja = _reasignar(pesos, caja, por_fecha[s])
            cartera, costo = valor / 100 * capital, 0.
            for t in set(pesos) | set(nuevos):
                monto = abs(nuevos.get(t, 0.) - pesos.get(t, 0.)) * cartera
                if monto > 1:
                    costo += max(tasa * monto, minimo); ops += 1
            valor *= 1 - costo / cartera if cartera > 0 else 1
            pesos, caja = nuevos, nueva_caja
        filas.append((s, valor)); anterior = s
    return pd.Series(dict(filas)), ops


def anual(s):
    s = s.dropna()
    return (s.iloc[-1] / s.iloc[0]) ** (365.25 / (s.index[-1] - s.index[0]).days) - 1


def mdd(s):
    s = s.dropna()
    return float((s / s.cummax() - 1).min())


def sharpe(s):
    r = s.dropna().pct_change().dropna()
    v = r.std() * np.sqrt(252)
    return float(r.mean() * 252 / v) if v else np.nan


def peores_caidas(s, n=3):
    """Las n mayores caidas y el mes en que tocaron fondo."""
    s = s.dropna()
    dd = s / s.cummax() - 1
    fondos, restante = [], dd.copy()
    for _ in range(n):
        if restante.empty or restante.min() >= -1e-9:
            break
        f = restante.idxmin()
        fondos.append((f, float(restante.loc[f])))
        restante = restante.drop(restante.loc[f - pd.Timedelta(days=90):f + pd.Timedelta(days=90)].index)
    return fondos


def calidad_historica(ev, mercado):
    """Calidad por corredora, con shrinkage hacia 0,5. Sin precio objetivo."""
    ev = ev.sort_values("fecha").reset_index(drop=True)
    resultados = []
    for e in ev.itertuples():
        fin = e.fecha + pd.Timedelta(days=365)
        serie = mercado.get(e.tk)
        if serie is None:
            continue
        a = serie[serie.index <= e.fecha]
        z = serie[serie.index >= fin]
        if a.empty or z.empty:
            continue
        sr = z.iloc[0] / a.iloc[-1] - 1
        signed = sr if e.score == 1 else (-sr if e.score == -1 else -abs(sr))
        resultados.append({"broker": e.broker, "vence": z.index[0], "acierto": float(signed > 0),
                           "exceso": signed})
    hist = pd.DataFrame(resultados)
    calidades = []
    for e in ev.itertuples():
        h = hist[(hist.broker == e.broker) & (hist.vence <= e.fecha)] if len(hist) else hist
        n = len(h)
        if n:
            A = h.acierto.mean()
            E = float(np.clip(.5 + h.exceso.mean() / .50, 0, 1))
            crudo = .5 * A + .5 * E      # sin precio objetivo: se renormaliza 0,4/0,4
        else:
            crudo = .5
        calidades.append(n / (n + SHRINK) * crudo + SHRINK / (n + SHRINK) * .5)
    return ev.assign(calidad=calidades)


def pesos_formula(scores, liquidez):
    if scores.sum() <= 0:
        return {}
    topes = pd.Series(TOPE_C, index=scores.index)
    topes[liquidez.reindex(scores.index).fillna(.5) < .60] = TOPE_ILIQUIDO
    fijos, salida, resto = pd.Series(False, index=scores.index), pd.Series(0., index=scores.index), 1.
    for _ in range(20):
        libres = ~fijos
        if not libres.any() or scores[libres].sum() <= 0:
            break
        ensayo = scores[libres] / scores[libres].sum() * resto
        pega = ensayo > topes[libres] + 1e-12
        if not pega.any():
            salida[libres] = ensayo; break
        idx = ensayo[pega].index
        salida[idx] = topes[idx]; fijos[idx] = True; resto = 1 - salida.sum()
    return {t: float(w) for t, w in salida.items() if w > 0}


def main():
    u = load_universe()
    p = pd.read_csv("data/market_prices_daily.csv", parse_dates=["date"])
    d = pd.read_csv(ZIP, dtype=str)
    loc = d[d.instrument_type.isin({"accion_local", "accion_local_historica"})].copy()
    loc["tk"] = loc.ticker.str.strip().str.upper().map(lambda t: ALIAS_TICKERS.get(t, t))
    loc["fecha"] = pd.to_datetime(loc.date, errors="coerce")
    loc["score"] = pd.to_numeric(loc.score, errors="coerce").fillna(0)
    con_precio = set(p.alphadata_ticker.unique())
    loc = loc[loc.tk.isin(con_precio)]
    catorce = loc.broker.value_counts()
    catorce = sorted(catorce[catorce >= 100].index)

    locales = set(u.loc[u.tipo.isin({"accion_local", "accion_sigma"}), "alphadata_ticker"])
    panel = (p[p.alphadata_ticker.isin(locales) & p.date.between(INICIO - pd.Timedelta(days=400), FIN)]
             .pivot(index="date", columns="alphadata_ticker", values="adjusted_close")
             .sort_index().ffill(limit=3))
    ses = panel.index[panel.index >= INICIO]
    revisiones = sorted({f for f in pd.Series(ses, index=ses).groupby(ses.to_period("W-FRI")).max()})
    mercado = {t: panel[t].dropna() for t in panel.columns}
    volumen = (p[p.alphadata_ticker.isin(locales)].assign(g=lambda x: x.close * x.volume)
               .pivot(index="date", columns="alphadata_ticker", values="g").sort_index().ffill())
    liquidez = volumen.rolling(60, min_periods=20).median().rank(axis=1, pct=True)
    print(f"{len(loc)} recomendaciones locales con precio; {len(catorce)} corredoras de 100+; "
          f"{len(revisiones)} revisiones", flush=True)

    # --- A: Sigma-6 v2.3.0 con Credicorp
    cre = loc[loc.broker == "Credicorp Capital"]
    valid_a = pd.DataFrame({"ticker": cre.tk, "broker_normalized": "Credicorp Capital",
                            "signal": cre.score.astype(int), "row_number": range(len(cre)),
                            "available_at_parsed": cre.fecha})
    estado, A = {"sigma_entries": {}}, []
    for f in revisiones:
        cart, _, estado = sigma6(valid_a, p.loc[p.date <= f], pd.Timestamp(f), estado)
        A.append((f, dict(zip(cart.ticker, cart.target_weight))))
    print("  A listo", flush=True)

    # --- D: sin corredora, top 10 por momentum entre las elegibles
    todo = pd.DataFrame([{"ticker": t, "broker_normalized": "x", "signal": 1, "row_number": i,
                          "available_at_parsed": f}
                         for i, (f, t) in enumerate((f, t) for f in revisiones for t in sorted(locales))])
    estado, D = {"sigma_entries": {}}, []
    for f in revisiones:
        _, audit, estado = sigma6(todo, p.loc[p.date <= f], pd.Timestamp(f), estado)
        e = audit[audit.eligible]
        obj = (dict(capped_pro_rata(pd.Series(1., index=e.nlargest(10, "momentum_12_1").ticker), .10))
               if len(e) else {})
        estado = {**estado, "sigma_entries": {t: estado["sigma_entries"].get(t, str(pd.Timestamp(f).date()))
                                              for t in obj}}
        D.append((f, obj))
    print("  D listo", flush=True)

    # --- B: Consenso-6, suma de senales de las seis
    seis = loc[loc.broker.isin(SEIS)]
    B = []
    for f in revisiones:
        v = seis[(seis.fecha <= f) & (seis.fecha >= f - pd.Timedelta(days=365))]
        ultima = v.sort_values("fecha").drop_duplicates(["tk", "broker"], keep="last")
        neto = ultima.groupby("tk").score.sum()
        pos = neto[neto > 0]
        B.append((f, dict(capped_pro_rata(pos.astype(float), .10)) if len(pos) else {}))
    print("  B listo", flush=True)

    # --- C: formula inicial, con las catorce
    ev = calidad_historica(loc[loc.broker.isin(catorce)], mercado)
    C, abiertas = [], {}
    for f in revisiones:
        v = ev[(ev.fecha <= f) & (ev.fecha >= f - pd.Timedelta(days=365))]
        ultima = v.sort_values("fecha").drop_duplicates(["tk", "broker"], keep="last")
        metricas = {}
        for tk, g in ultima.groupby("tk"):
            dec = np.exp(-(f - g.fecha).dt.days / DECAIMIENTO)
            den = float((g.calidad * dec).sum())
            if den <= 0:
                continue
            cons = float((g.score * g.calidad * dec).sum()) / den
            direccion = 1 if cons > 0 else (-1 if cons < 0 else 0)
            acuerdo = (float((g.calidad * dec)[np.sign(g.score) == direccion].sum()) / den) if direccion else 0.
            calidad = float((g.calidad * dec).sum() / dec.sum())
            confianza = min(len(g) / 2, 1) * acuerdo * calidad   # sin target no hay penalizacion por dispersion
            lf = .5 + .5 * (liquidez.at[f, tk] if tk in liquidez.columns and pd.notna(liquidez.at[f, tk]) else .5)
            metricas[tk] = {"cons": cons, "n": len(g), "conf": confianza,
                            "liq": lf, "score": max(0., cons * confianza * lf)}
        for tk in list(abiertas):
            m = metricas.get(tk, {})
            if m.get("cons", 0) <= 0 or (f - abiertas[tk]).days >= 365:
                abiertas.pop(tk)
        elegibles = {t: m for t, m in metricas.items()
                     if m["cons"] > 0 and m["n"] >= MIN_OPINIONES and m["conf"] >= CONF_MIN and m["score"] > 0}
        for tk in sorted(elegibles, key=lambda t: -elegibles[t]["score"])[:MAX_POS]:
            abiertas.setdefault(tk, f)
        scores = pd.Series({t: metricas.get(t, {}).get("score", 0.) for t in abiertas})
        liq = pd.Series({t: metricas.get(t, {}).get("liq", .5) for t in abiertas})
        C.append((f, pesos_formula(scores, liq) if len(scores) else {}))
    print("  C listo", flush=True)

    # --- las otras tres piezas, con su propio modelo de costo
    fx = p[p.alphadata_ticker == "USDCLP"]
    us = set(u.loc[u.tipo == "accion_us", "alphadata_ticker"])
    etf = set(u.loc[u.tipo == "etf_us", "alphadata_ticker"])
    panel_us = (to_clp(p[p.alphadata_ticker.isin(us)], u, fx)
                .pivot(index="date", columns="alphadata_ticker", values="adjusted_close").sort_index().ffill(limit=3))
    panel_oro = (to_clp(p[p.alphadata_ticker.isin(etf)], u, fx)
                 .pivot(index="date", columns="alphadata_ticker", values="adjusted_close").sort_index().ffill(limit=3))
    ses_us = panel_us.index[panel_us.index >= INICIO]
    meses_cl = sorted({f for f in pd.Series(ses, index=ses).groupby(ses.to_period("M")).max()})
    meses_us = sorted({f for f in pd.Series(ses_us, index=ses_us).groupby(ses_us.to_period("M")).max()})
    obj_delta = [(f, dict(zip(*[delta12(p.loc[p.date <= f], u, pd.Timestamp(f))[0][c]
                                for c in ("ticker", "target_weight")]))) for f in meses_cl]
    obj_gamma = [(f, dict(zip(*[gamma6(p.loc[p.date <= f], u, pd.Timestamp(f))[0][c]
                                for c in ("ticker", "target_weight")]))) for f in meses_us]
    obj_oro = [(ses_us[1], {"IAU": 1.0})]   # la primera sesion no aplica objetivos
    print("  las otras tres listas", flush=True)

    for etiqueta, capital in [("$5.000.000 por pieza", 5_000_000.), ("$2.500.000 por pieza", 2_500_000.)]:
        piezas = {"Delta-12": correr(panel, ses, obj_delta, capital, TASA_CL, MIN_CL)[0],
                  "Gamma-6": correr(panel_us, ses_us, obj_gamma, capital, TASA_US, 0.)[0],
                  "Oro": correr(panel_oro, ses_us, obj_oro, capital, TASA_US, 0.)[0]}
        candidatos = {}
        for nombre, obj in [("A Sigma-6 actual", A), ("B Consenso-6", B),
                            ("C Formula inicial", C), ("D Sin corredora", D)]:
            candidatos[nombre] = correr(panel, ses, obj, capital, TASA_CL, MIN_CL)[0]
        # El control: una pieza que es solo caja, al 0%.
        candidatos["CAJA (control)"] = pd.Series(100., index=piezas["Delta-12"].index)

        print(f"\n{'#'*20} capital {etiqueta} {'#'*20}")
        fechas = piezas["Delta-12"].index
        def mensual(s):
            return s.reindex(fechas).ffill().resample("ME").last().pct_change().dropna()
        print(f"\n{'candidato':20} " + " ".join(f"{k:>10}" for k in piezas) + "   solape Δ12   posiciones")
        for nombre, serie in candidatos.items():
            cors = [f"{mensual(serie).corr(mensual(s)):>10.2f}" for s in piezas.values()]
            obj = dict([("A Sigma-6 actual", A), ("B Consenso-6", B),
                        ("C Formula inicial", C), ("D Sin corredora", D)]).get(nombre)
            if obj is None:
                print(f"{nombre:20} " + " ".join(f"{'—':>10}" for _ in piezas) + f"   {'—':>9}   {0.0:>10.1f}")
                continue
            jac = []
            for (f, o), (_, od) in zip(obj, [(f, dict(obj_delta[min(range(len(meses_cl)),
                 key=lambda i: abs((meses_cl[i]-f).days))][1])) for f, _ in obj]):
                a, b = set(o), set(od)
                if a | b:
                    jac.append(len(a & b) / len(a | b))
            pos = pd.Series([len(o) for _, o in obj]).mean()
            print(f"{nombre:20} " + " ".join(cors) + f"   {np.median(jac):>9.2f}   {pos:>10.1f}")

        print(f"\n{'candidato':20} {'peores tres caidas (fondo y magnitud)':>60}")
        for nombre, serie in {**candidatos, **piezas}.items():
            caidas = ", ".join(f"{f:%m-%Y} {v:+.0%}" for f, v in peores_caidas(serie))
            print(f"{nombre:20} {caidas:>60}")

        base = pd.DataFrame(piezas)
        tres = combined_equal_weight(base.reset_index().rename(columns={"index": "date"}),
                                     list(piezas), date_column="date")
        print(f"\n{'conjunto':24} {'retorno anual':>14} {'peor caida':>12} {'Sharpe':>8}   aporte")
        for tramo, etiq in [(slice(None, CORTE), "seleccion"), (slice(CORTE, None), "evaluacion")]:
            print(f"\n  --- {etiq} ---")
            t3 = tres.loc[tramo]
            print(f"  {'tres piezas (sin 4a)':24} {anual(t3):>+13.2%} {mdd(t3):>12.1%} {sharpe(t3):>8.2f}")
            for nombre, serie in candidatos.items():
                cuatro = pd.DataFrame({**piezas, "cuarta": serie})
                c4 = combined_equal_weight(cuatro.reset_index().rename(columns={"index": "date"}),
                                           list(cuatro), date_column="date").loc[tramo]
                print(f"  {'+ ' + nombre:24} {anual(c4):>+13.2%} {mdd(c4):>12.1%} {sharpe(c4):>8.2f}   "
                      f"{anual(c4)-anual(t3):>+7.2%} ret  {mdd(c4)-mdd(t3):>+6.1%} caida  "
                      f"{sharpe(c4)-sharpe(t3):>+6.2f} Sharpe")


if __name__ == "__main__":
    main()
