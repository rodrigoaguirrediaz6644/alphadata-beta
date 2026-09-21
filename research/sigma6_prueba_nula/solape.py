"""Si Sigma-6 sin corredora es Delta-12 con revision semanal, deberian tener
casi las mismas posiciones. Se mide el solape en las revisiones mensuales."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd
from src.fetch_prices import load_universe
from src.strategy_engine import capped_pro_rata, delta12, sigma6, validate_recommendations
INICIO, FIN = pd.Timestamp("2021-07-08"), pd.Timestamp("2026-07-15")
u = load_universe(); p = pd.read_csv("data/market_prices_daily.csv", parse_dates=["date"])
crudo = pd.read_csv("data/recommendations_input.csv", dtype=str).fillna("")
reales, _ = validate_recommendations(crudo, set(u.alphadata_ticker))
loc = set(u.loc[u.tipo.isin({"accion_local","accion_sigma"}), "alphadata_ticker"])
ses = pd.DatetimeIndex(sorted(p.loc[p.alphadata_ticker.isin(loc) & p.date.between(INICIO, FIN), "date"].unique()))
meses = sorted({f for f in pd.Series(ses, index=ses).groupby(ses.to_period("M")).max()})
todo = pd.DataFrame([{"ticker": t, "broker_normalized": "Credicorp Capital", "signal": 1,
                      "row_number": i, "available_at_parsed": f}
                     for i, (f, t) in enumerate((f, t) for f in meses for t in sorted(loc))])
def jac(a, b):
    return len(a & b) / len(a | b) if (a | b) else float("nan")
est_n, est_c, filas = {"sigma_entries": {}}, {"sigma_entries": {}}, []
for f in meses:
    cart_d, _ = delta12(p.loc[p.date <= f], u, pd.Timestamp(f))
    d = set(cart_d.ticker)
    _, audit, est_n = sigma6(todo, p.loc[p.date <= f], pd.Timestamp(f), est_n)
    e = audit[audit.eligible]
    n = set(capped_pro_rata(pd.Series(1., index=e.nlargest(10, "momentum_12_1").ticker), .10).index) if len(e) else set()
    cart_c, _, est_c = sigma6(reales, p.loc[p.date <= f], pd.Timestamp(f), est_c)
    c = set(cart_c.ticker)
    filas.append({"fecha": f.date(), "delta": len(d), "nula": len(n), "credicorp": len(c),
                  "solape_nula_delta": jac(n, d), "solape_credicorp_delta": jac(c, d)})
t = pd.DataFrame(filas)
print(f"{len(t)} revisiones mensuales\n")
print("solape de Jaccard con la cartera de Delta-12 (1 = identicas, 0 = disjuntas):")
print(f"  Sigma-6 sin corredora : mediana {t.solape_nula_delta.median():.2f}  media {t.solape_nula_delta.mean():.2f}")
print(f"  Sigma-6 con Credicorp : mediana {t.solape_credicorp_delta.median():.2f}  media {t.solape_credicorp_delta.mean():.2f}")
print(f"\nposiciones: Delta-12 {t.delta.mean():.1f}, nula {t.nula.mean():.1f}, Credicorp {t.credicorp.mean():.1f}")
