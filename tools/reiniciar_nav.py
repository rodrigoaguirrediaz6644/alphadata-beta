"""Reinicia el seguimiento en vivo y separa la reconstrucción, estructuralmente.

    PYTHONPATH=. python -m tools.reiniciar_nav              # ensayo
    PYTHONPATH=. python -m tools.reiniciar_nav --confirmar  # escribe

## Por qué reiniciar

El NAV en vivo nació el 16-07-2026, un día después de que el feed chileno se
congelara, y nunca tuvo una sola jornada de valorización con precios vivos. Lo
que publicó —+30,2% de Delta-12, +20,8% del conjunto— era el mismo movimiento
contabilizado una vez por corrida. No se repara: se archiva y se empieza de
nuevo, porque tampoco las carteras de ese periodo son las que las reglas
habrían elegido con datos reales.

## Por qué separar en archivos distintos

La reconstrucción histórica y el seguimiento en vivo son cosas distintas: una
aplica las reglas hacia atrás sobre el universo de hoy, la otra ejecuta hacia
adelante. Encadenarlas en un gráfico fue lo que hizo que un +30% inventado se
leyera como resultado.

La separación tiene que ser **estructural y no visual**. Un corte dibujado se
borra; dos archivos con nombres que dicen lo que son no se juntan solos. Por
eso `historical_model_nav.csv` pasa a llamarse `reconstruccion_historica.csv`,
y el encadenamiento en memoria que hacía el gráfico se elimina.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARCHIVO = DATA / "archivo"
PIEZAS = ["Sigma-6", "Delta-12", "Gamma-6", "Oro"]
BENCHMARK = "IPSA TR"
# Estas claves guardan carteras, fechas de entrada y NAV del periodo
# contaminado. Si alguna sobrevive, la corrida nueva heredaría posiciones que
# nunca se eligieron con datos buenos.
CLAVES_A_LIMPIAR = ["sigma_entries", "delta_entries", "gamma_entries", "oro_entries",
                    "sigma_portfolio", "delta_portfolio", "gamma_portfolio", "oro_portfolio",
                    "delta_last_period", "gamma_last_period", "entry_dates_version",
                    "valuation_date", "nav", "ingestion", "last_run_utc"]


def fecha_de_reinicio(precios: pd.DataFrame, universo: pd.DataFrame) -> pd.Timestamp:
    """La última rueda chilena con dato, que es el primer día confiable."""
    locales = set(universo.loc[universo.tipo.isin({"accion_local", "accion_sigma"}), "alphadata_ticker"])
    fechas = precios.loc[precios.alphadata_ticker.isin(locales), "date"]
    return pd.Timestamp(fechas.max()).normalize()


def main(confirmar: bool = False) -> int:
    precios = pd.read_csv(DATA / "market_prices_daily.csv", parse_dates=["date"])
    universo = pd.read_csv(ROOT / "config" / "tickers.csv")
    corte = fecha_de_reinicio(precios, universo)

    vivo_path = DATA / "strategy_nav.csv"
    recon_path = DATA / "historical_model_nav.csv"
    vivo = pd.read_csv(vivo_path, parse_dates=["date"]) if vivo_path.exists() else pd.DataFrame()
    recon = pd.read_csv(recon_path, parse_dates=["date"]) if recon_path.exists() else pd.DataFrame()
    estado = json.loads((DATA / "strategy_state.json").read_text(encoding="utf-8"))

    print(f"Fecha de reinicio: {corte.date()} (última rueda chilena con dato)")
    print(f"  NAV en vivo a archivar: {len(vivo)} filas, "
          f"{vivo.date.min().date() if len(vivo) else '-'} a {vivo.date.max().date() if len(vivo) else '-'}")
    if len(vivo):
        ultimos = vivo.iloc[-1]
        print("  últimos valores publicados: " + ", ".join(
            f"{c} {ultimos[c]:.1f}" for c in [*PIEZAS, BENCHMARK] if c in vivo and pd.notna(ultimos[c])))
    print(f"  reconstrucción a renombrar: {len(recon)} filas, "
          f"{recon.date.min().date() if len(recon) else '-'} a {recon.date.max().date() if len(recon) else '-'}")
    presentes = [k for k in CLAVES_A_LIMPIAR if k in estado]
    print(f"  claves de estado a limpiar: {len(presentes)} ({', '.join(presentes[:6])}...)")

    if not confirmar:
        print("\nEnsayo: no se escribió nada. Repetir con --confirmar.")
        return 0

    ARCHIVO.mkdir(parents=True, exist_ok=True)
    if len(vivo):
        vivo.to_csv(ARCHIVO / "strategy_nav_incidente_2026.csv", index=False, date_format="%Y-%m-%d")
    (ARCHIVO / "strategy_state_incidente_2026.json").write_text(
        json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")

    # La reconstrucción no se archiva: se renombra, porque sigue siendo válida
    # como backtest. Lo que cambia es que su nombre diga lo que es.
    if len(recon):
        recon.to_csv(DATA / "reconstruccion_historica.csv", index=False, date_format="%Y-%m-%d")
        recon_path.unlink()

    nuevo = pd.DataFrame([{"date": corte.date().isoformat(),
                           **{p: 100.0 for p in PIEZAS}, BENCHMARK: 100.0,
                           "Conjunto AlphaData": 100.0}])
    nuevo.to_csv(vivo_path, index=False)

    limpio = {k: v for k, v in estado.items() if k not in CLAVES_A_LIMPIAR}
    limpio.update({"methodology_version": "2.3.0",
                   "sigma_entries": {}, "delta_entries": {}, "gamma_entries": {}, "oro_entries": {},
                   "sigma_portfolio": [], "delta_portfolio": [], "gamma_portfolio": [], "oro_portfolio": [],
                   "valuation_date": corte.date().isoformat(),
                   "nav": {**{p: 100.0 for p in PIEZAS}, BENCHMARK: 100.0},
                   "reinicio": {"fecha": corte.date().isoformat(),
                                "motivo": "feed chileno detenido entre el 17-07 y el 16-09 de 2026",
                                "series_archivadas": ["strategy_nav_incidente_2026.csv",
                                                      "strategy_state_incidente_2026.json"]}})
    (DATA / "strategy_state.json").write_text(json.dumps(limpio, ensure_ascii=False, indent=2), encoding="utf-8")

    (ARCHIVO / "reinicio_nav.md").write_text(f"""# Reinicio del seguimiento en vivo — {pd.Timestamp.now():%d-%m-%Y}

## Qué se archivó

| archivo | filas | desde | hasta |
|---|---|---|---|
| `strategy_nav_incidente_2026.csv` | {len(vivo)} | {vivo.date.min():%d-%m-%Y} | {vivo.date.max():%d-%m-%Y} |
| `strategy_state_incidente_2026.json` | — | — | {estado.get('valuation_date', '-')} |

Últimos valores que llegó a publicar esa serie:
{chr(10).join(f'- {c}: {vivo.iloc[-1][c]:.2f}' for c in [*PIEZAS, BENCHMARK] if c in vivo and pd.notna(vivo.iloc[-1][c]))}

Ninguno es real. El NAV nació el 16-07-2026, un día después de que el feed
chileno se congelara, y nunca tuvo una jornada de valorización con precios
vivos.

## Desde cuándo corre la serie nueva

**{corte:%d-%m-%Y}**, con las cuatro piezas en 100 en esa misma fecha.

## Qué se limpió del estado

{', '.join(presentes)}.

Ninguna cartera, fecha de entrada ni NAV del periodo contaminado sobrevive: las
carteras de esas semanas tampoco son las que las reglas habrían elegido con
datos reales, así que heredarlas sería arrastrar el mismo problema.

## La separación

`historical_model_nav.csv` pasa a llamarse `reconstruccion_historica.csv`. No
se archiva porque sigue siendo válida como backtest; lo que cambia es que su
nombre diga lo que es. El gráfico deja de encadenarla con el seguimiento en
vivo: son dos series distintas en dos archivos distintos y se dibujan por
separado.
""", encoding="utf-8")
    print(f"\nEscrito. Serie anterior en {(ARCHIVO / 'strategy_nav_incidente_2026.csv').relative_to(ROOT)}, "
          f"registro en {(ARCHIVO / 'reinicio_nav.md').relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--confirmar" in sys.argv))
