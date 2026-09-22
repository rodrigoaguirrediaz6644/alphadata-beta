"""Estudio de corredoras con los datos completos.

Reglas congeladas y cortes fijados en la orden, antes de mirar nada:

- **Universo**: solo acciones locales. Fuera los 406 ADR y las 98 extranjeras,
  porque el efecto cambiario no esta incorporado.
- **Reglas**: Sigma-6 v2.3.0, las que estan corriendo. Recomendacion vigente
  +1, momentum 12-1 > 0, sobre SMA200, tope 10% por accion, revision semanal,
  sin tope de tenencia. Identicas para todas las corredoras.
- **Cortes**: seleccion 08-07-2021 a 31-12-2023; evaluacion 01-01-2024 a
  15-07-2026.
- **Costos**: Trii, 0,1785% sobre el monto con **minimo $999,99** por
  operacion. El minimo no es neutral entre variantes: castiga a las que se
  diversifican mas, asi que el capital se declara. Referencia $5.000.000 por
  pieza; sensibilidad a $2.500.000 (los $10 millones totales), donde nada llega
  al umbral de $560.218 y el orden puede cambiar.
- **Consenso-6** como control: las seis de v1.0.0, suma de senales, entrada con
  puntaje neto positivo, peso proporcional al puntaje con tope 10%, salida
  cuando el neto deja de ser positivo o a los 365 dias. No selecciona a nadie.

Dos precisiones sobre los datos:

- `available_at` no existe en el archivo: se usa la fecha de publicacion, que
  es el supuesto optimista —disponible el mismo dia—. Aplica igual a todas las
  variantes.
- Los precios son los del repositorio, reparados para 2025-2026, no los del
  zip. Son estrictamente mejores y el defecto comun se cancela en un estudio
  relativo.
"""
import warnings

warnings.filterwarnings("ignore")

import pandas as pd

from src.fetch_prices import load_universe
from src.nav_historico import _reasignar
from src.strategy_engine import ALIAS_TICKERS, capped_pro_rata, sigma6

ZIP = ("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
       "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/corredoras/data/"
       "final_validated_recommendations.csv")
INICIO, CORTE, FIN = pd.Timestamp("2021-07-08"), pd.Timestamp("2024-01-01"), pd.Timestamp("2026-07-15")
TASA, MINIMO = .001785, 999.99
CAPITALES = {"$5.000.000 por pieza": 5_000_000., "$2.500.000 por pieza": 2_500_000.}
SEIS = ["Credicorp Capital", "BICE", "Itaú", "BTG Pactual", "MBI", "LarrainVial Estudios"]
MINIMO_RECOMENDACIONES = 100


def correr(panel, sesiones, objetivos, capital):
    """NAV base 100 con la politica de pesos de produccion y la comision real."""
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
                    costo += max(TASA * monto, MINIMO); ops += 1
            valor *= 1 - costo / cartera if cartera > 0 else 1
            pesos, caja = nuevos, nueva_caja
        filas.append((s, valor)); anterior = s
    return pd.Series(dict(filas)), ops


def anual(s):
    return (s.iloc[-1] / s.iloc[0]) ** (365.25 / (s.index[-1] - s.index[0]).days) - 1


def mdd(s):
    return float((s / s.cummax() - 1).min())


def objetivos_sigma6(valid, precios, revisiones):
    estado, salida = {"sigma_entries": {}}, []
    for f in revisiones:
        cart, _, estado = sigma6(valid, precios.loc[precios.date <= f], pd.Timestamp(f), estado)
        salida.append((f, dict(zip(cart.ticker, cart.target_weight))))
    return salida


def objetivos_consenso(reco, revisiones):
    """v1.0.0: suma de senales de las seis, peso proporcional al puntaje.

    Sin filtros de precio, que es lo que la distingue. Una recomendacion vale
    365 dias, igual que en v2.3.0.
    """
    salida = []
    for f in revisiones:
        vigentes = reco[(reco.fecha <= f) & (reco.fecha >= f - pd.Timedelta(days=365))]
        ultima = vigentes.sort_values("fecha").drop_duplicates(["tk", "broker"], keep="last")
        neto = ultima.groupby("tk").score.sum()
        positivos = neto[neto > 0]
        salida.append((f, dict(capped_pro_rata(positivos.astype(float), .10)) if len(positivos) else {}))
    return salida


def main():
    u = load_universe()
    p = pd.read_csv("data/market_prices_daily.csv", parse_dates=["date"])
    d = pd.read_csv(ZIP, dtype=str)
    loc = d[d.instrument_type.isin({"accion_local", "accion_local_historica"})].copy()
    loc["tk"] = loc.ticker.str.strip().str.upper().map(lambda t: ALIAS_TICKERS.get(t, t))
    loc["fecha"] = pd.to_datetime(loc.date, errors="coerce")
    loc["score"] = pd.to_numeric(loc.score, errors="coerce")
    con_precio = set(p.alphadata_ticker.unique())
    loc["tiene_precio"] = loc.tk.isin(con_precio)

    print(f"locales {len(loc)}; con serie de precios {int(loc.tiene_precio.sum())} "
          f"({loc.tiene_precio.mean():.1%}); tickers {loc.tk.nunique()}, con precio "
          f"{loc.loc[loc.tiene_precio, 'tk'].nunique()}")
    cob = (loc.groupby("broker").agg(recomendaciones=("tk", "size"), con_precio=("tiene_precio", "sum"))
           .assign(cobertura=lambda x: x.con_precio / x.recomendaciones)
           .sort_values("recomendaciones", ascending=False))
    grandes = cob[cob.recomendaciones >= MINIMO_RECOMENDACIONES]
    print(f"\ncorredoras con {MINIMO_RECOMENDACIONES}+ recomendaciones: {len(grandes)}")
    print(grandes.assign(cobertura=lambda x: x.cobertura.map("{:.1%}".format)).to_string())

    locales = set(u.loc[u.tipo.isin({"accion_local", "accion_sigma"}), "alphadata_ticker"])
    panel = (p[p.alphadata_ticker.isin(locales) & p.date.between(INICIO - pd.Timedelta(days=400), FIN)]
             .pivot(index="date", columns="alphadata_ticker", values="adjusted_close")
             .sort_index().ffill(limit=3))
    ses = panel.index[panel.index >= INICIO]
    revisiones = sorted({f for f in pd.Series(ses, index=ses).groupby(ses.to_period("W-FRI")).max()})
    usable = loc[loc.tiene_precio]
    print(f"\n{len(revisiones)} revisiones semanales\n", flush=True)

    variantes = {}
    for corredora in grandes.index:
        sub = usable[usable.broker == corredora]
        valid = pd.DataFrame({"ticker": sub.tk, "broker_normalized": corredora,
                              "signal": sub.score.fillna(0).astype(int),
                              "row_number": range(len(sub)), "available_at_parsed": sub.fecha})
        variantes[corredora] = objetivos_sigma6(valid, p, revisiones)
        print(f"  objetivos listos: {corredora}", flush=True)
    variantes["Consenso-6 (v1.0.0)"] = objetivos_consenso(usable[usable.broker.isin(SEIS)], revisiones)
    print("  objetivos listos: Consenso-6", flush=True)

    for etiqueta, capital in CAPITALES.items():
        filas = []
        for nombre, objetivos in variantes.items():
            serie, ops = correr(panel, ses, objetivos, capital)
            sel, ev = serie.loc[:CORTE], serie.loc[CORTE:]
            filas.append({"variante": nombre,
                          "cobertura": cob.cobertura.get(nombre),
                          "posiciones": pd.Series([len(o) for _, o in objetivos]).mean(),
                          "sel_anual": anual(sel), "sel_mdd": mdd(sel),
                          "ev_anual": anual(ev), "ev_mdd": mdd(ev), "ops": ops})
        t = pd.DataFrame(filas)
        t["rango_sel"] = t.sel_anual.rank(ascending=False).astype(int)
        t["rango_ev"] = t.ev_anual.rank(ascending=False).astype(int)
        t = t.sort_values("sel_anual", ascending=False)
        print(f"\n########## capital {etiqueta} ##########")
        print(f"{'variante':24} {'cob':>6} {'pos':>5} {'seleccion 21-23':>18} {'#':>3} "
              f"{'evaluacion 24-26':>18} {'#':>3} {'ops':>5}")
        for r in t.itertuples():
            c = f"{r.cobertura:.0%}" if pd.notna(r.cobertura) else "—"
            print(f"{r.variante:24} {c:>6} {r.posiciones:>5.1f} "
                  f"{r.sel_anual:>+9.2%} {r.sel_mdd:>7.1%} {r.rango_sel:>3} "
                  f"{r.ev_anual:>+9.2%} {r.ev_mdd:>7.1%} {r.rango_ev:>3} {r.ops:>5}")
        mejor = t.iloc[0]
        print(f"\n  mejor de la seleccion: {mejor.variante} ({mejor.sel_anual:+.2%})")
        print(f"  su resultado en la evaluacion: {mejor.ev_anual:+.2%}, "
              f"puesto {mejor.rango_ev} de {len(t)}  <== la estimacion honesta")
        print(f"  correlacion de rangos entre ventanas: {t.rango_sel.corr(t.rango_ev, method='spearman'):+.3f}")
        print(f"  dispersion en la evaluacion: {t.ev_anual.min():+.2%} a {t.ev_anual.max():+.2%}")
        t.to_csv(f"../corredoras_{int(capital)}.csv", index=False)


if __name__ == "__main__":
    main()
