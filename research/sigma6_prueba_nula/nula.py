"""Parte 1 del protocolo: Sigma-6 sin el filtro de corredora.

La pregunta no es cual corredora es mejor, sino **si aporta algo la
recomendacion de una corredora por encima de lo que ya aporta el momentum**.

Reglas congeladas, fijadas antes de mirar:

- Mismo universo, misma revision semanal W-FRI, mismo tope de 10% por posicion,
  misma SMA200, mismas salidas. Lo unico que cambia es el filtro de corredora.
- La variante nula elige **las diez de mayor momentum 12-1 entre las elegibles
  por las condiciones de produccion**. El top 10 no es un parametro nuevo:
  reproduce la forma que Sigma-6 tiene cuando el filtro de corredora ata (diez
  nombres al 10%). Sin el, la nula tendria cuarenta posiciones al 2,5% y no
  seria comparable en concentracion.

  Primera version descartada: fabricar una recomendacion semanal para el top 10
  y dejar que `sigma6` filtrara. No servia, porque una recomendacion vale 365
  dias: la union de los top 10 de un ano daba **15,5 posiciones promedio contra
  7,8** de la variante con Credicorp. La nula ganaba, pero con el doble de
  nombres, que es otra estrategia y no una comparacion.
- El corte esta fijado por el protocolo: seleccion 2021-07 a 2023-12,
  evaluacion 2024-01 a 2026-07. En una prueba nula no hay seleccion, asi que se
  informan las dos mitades.
- Misma politica de pesos que produccion —corren entre revisiones, limite de
  concentracion del 25%— y misma comision, con el minimo real de $1.990 sobre
  $5.000.000.
- Los datos anteriores a 2025 no estan reparados. Los defectos conocidos
  afectan por igual a las dos variantes, asi que **la comparacion es valida
  aunque los niveles absolutos no sean exactos**: es un estudio relativo y ahi
  el defecto comun se cancela.
"""
import warnings

warnings.filterwarnings("ignore")

import pandas as pd

from src.fetch_prices import load_universe
from src.nav_historico import nav_corrido
from src.strategy_engine import sigma6, validate_recommendations

INICIO, CORTE, FIN = pd.Timestamp("2021-07-08"), pd.Timestamp("2024-01-01"), pd.Timestamp("2026-07-15")
TASA, TOPE = .001785, 10


def recomendaciones_de_todo(tickers, revisiones) -> pd.DataFrame:
    """Recomendacion de compra vigente para todo el universo, en toda revision.

    Neutraliza el filtro de corredora sin tocar nada mas: `sigma6` sigue
    aplicando momentum, SMA200 y el tope de 10% sobre el universo completo.
    """
    filas, n = [], 0
    for fecha in revisiones:
        for ticker in sorted(tickers):
            n += 1
            filas.append({"ticker": ticker, "broker_normalized": "Credicorp Capital",
                          "signal": 1, "row_number": n, "available_at_parsed": fecha})
    return pd.DataFrame(filas)


def main():
    u = load_universe()
    p = pd.read_csv("data/market_prices_daily.csv", parse_dates=["date"])
    crudo = pd.read_csv("data/recommendations_input.csv", dtype=str).fillna("")
    reales, _ = validate_recommendations(crudo, set(u.alphadata_ticker))
    loc = set(u.loc[u.tipo.isin({"accion_local", "accion_sigma"}), "alphadata_ticker"])
    panel = (p[p.alphadata_ticker.isin(loc) & p.date.between(INICIO - pd.Timedelta(days=400), FIN)]
             .pivot(index="date", columns="alphadata_ticker", values="adjusted_close")
             .sort_index().ffill(limit=3))
    ses = panel.index[panel.index >= INICIO]
    revisiones = sorted({f for f in pd.Series(ses, index=ses).groupby(ses.to_period("W-FRI")).max()})
    nulas = recomendaciones_de_todo(loc, revisiones)
    print(f"{len(revisiones)} revisiones; universo de la nula: {len(loc)} instrumentos")

    from src.strategy_engine import capped_pro_rata

    def top_diez(audit, tope=TOPE):
        """Las `tope` de mayor momentum entre las elegibles, al 10% cada una."""
        e = audit[audit.eligible]
        if not len(e):
            return {}
        w = capped_pro_rata(pd.Series(1., index=e.nlargest(tope, "momentum_12_1").ticker), .10)
        return dict(zip(w.index, w.values))

    series = {}
    for etiqueta, valid, recortar in [("con Credicorp", reales, False),
                                      ("sin corredora (nula)", nulas, True)]:
        estado = {"sigma_entries": {}}

        def elegir(f, _v=valid, _r=recortar):
            nonlocal estado
            cart, audit, estado = sigma6(_v, p.loc[p.date <= f], pd.Timestamp(f), estado)
            if not _r:
                return dict(zip(cart.ticker, cart.target_weight))
            objetivo = top_diez(audit)
            # El estado de tenencia tiene que reflejar lo que de verdad se tiene.
            estado = {**estado, "sigma_entries": {t: estado["sigma_entries"].get(t, str(pd.Timestamp(f).date()))
                                                  for t in objetivo}}
            return objetivo

        d = nav_corrido(panel, ses, "W-FRI", elegir, TASA, "Sigma-6")
        series[etiqueta] = d.set_index("date")["Sigma-6"]
        print(f"  {etiqueta:22} final {series[etiqueta].iloc[-1]:8.2f}", flush=True)

    def anual(s):
        return (s.iloc[-1] / s.iloc[0]) ** (365.25 / (s.index[-1] - s.index[0]).days) - 1

    def mdd(s):
        return float((s / s.cummax() - 1).min())

    print(f"\n{'tramo':26} " + " ".join(f"{e:>26}" for e in series))
    for etiqueta, tramo in [("completa", slice(None)), ("1a mitad (2021-07/2023-12)", slice(None, CORTE)),
                            ("2a mitad (2024-01/2026-07)", slice(CORTE, None))]:
        celdas = [f"{anual(s.loc[tramo]):+9.2%} anual {mdd(s.loc[tramo]):7.1%}" for s in series.values()]
        print(f"{etiqueta:26} " + " ".join(f"{c:>26}" for c in celdas))
    print()
    for etiqueta, tramo in [("1a", slice(None, CORTE)), ("2a", slice(CORTE, None))]:
        orden = sorted(series, key=lambda k: -anual(series[k].loc[tramo]))
        print(f"  orden por retorno ({etiqueta}): {' > '.join(orden)}")
        brecha = anual(series["con Credicorp"].loc[tramo]) - anual(series["sin corredora (nula)"].loc[tramo])
        print(f"     brecha a favor de Credicorp: {brecha:+.2%} anual")
    # Cuantas posiciones sostiene cada variante, que es parte de la comparacion.
    print()
    for etiqueta, valid, recortar in [("con Credicorp", reales, False), ("sin corredora (nula)", nulas, True)]:
        estado, cuenta = {"sigma_entries": {}}, []
        for f in revisiones:
            cart, audit, estado = sigma6(valid, p.loc[p.date <= f], pd.Timestamp(f), estado)
            if recortar:
                objetivo = top_diez(audit)
                estado = {**estado, "sigma_entries": {t: estado["sigma_entries"].get(t, str(pd.Timestamp(f).date()))
                                                      for t in objetivo}}
                cuenta.append(len(objetivo))
            else:
                cuenta.append(len(cart))
        s = pd.Series(cuenta)
        print(f"  {etiqueta:22} posiciones por revision: media {s.mean():.2f}, "
              f"mediana {s.median():.0f}, minimo {s.min()}, maximo {s.max()}")


if __name__ == "__main__":
    main()
