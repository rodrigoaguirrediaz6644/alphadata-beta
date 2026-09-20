"""Busca candidatos de ETF poco correlacionados con las estrategias oficiales.

Investigación paralela, NO metodología oficial. No escribe en `data/`, `reports/`
ni `strategy_state.json`; todo queda en `research/etf_multiactivo/results/`.

Qué hace, en orden:

1. Descarga los 56 instrumentos de `config/universe_etf.csv`. Los ETF de EE.UU.
   se piden por su símbolo original: el CDV que se transa en Chile replica ese
   precio, sólo cambia la nomenclatura. Los ETF locales se piden con sufijo
   `.SN`; si Yahoo no los tiene, se informan como faltantes en vez de abortar.
2. Los pasa a pesos con el tipo de cambio `USDCLP` que ya descarga la corrida
   oficial, porque la correlación que importa es la que ve un inversionista
   local: el dólar es parte del riesgo, no un detalle contable.
3. Mide, contra las series de Sigma-6, Delta-12, Gamma-6 y el conjunto
   (`data/historical_model_nav.csv`), la correlación de retornos mensuales y
   semanales en la ventana común.
4. Ordena los candidatos por correlación con el conjunto y por retorno ajustado
   por riesgo, y marca los redundantes (los que replican lo que ya se tiene).
5. Calcula, sólo como referencia de lo que el universo puede dar, dos rotaciones
   mensuales simples sobre los candidatos con historia suficiente.

El resultado es un informe para decidir con datos qué instrumentos merecen una
estrategia propia. No propone todavía una metodología.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.common.engine import download_prices, equal_weights, performance_metrics, run_backtest, to_panel

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "results"
UNIVERSE_PATH = ROOT / "config" / "universe_etf.csv"
PRICES_OFICIALES = ROOT / "data" / "market_prices_daily.csv"
NAV_HISTORICO = ROOT / "data" / "historical_model_nav.csv"

PRICES_START = "2013-01-01"
MIN_SESIONES = 252
ESTRATEGIAS = ["Sigma-6", "Delta-12", "Gamma-6", "Conjunto AlphaData"]
COSTO = 0.001
N_ROTACION = 5


# --------------------------------------------------------------------------
# Funciones puras
# --------------------------------------------------------------------------

def serie_fx(prices_oficiales: pd.DataFrame) -> pd.Series:
    """Tipo de cambio USD/CLP diario, tomado del archivo de precios oficial."""
    fx = prices_oficiales.loc[prices_oficiales.alphadata_ticker == "USDCLP", ["date", "adjusted_close"]]
    if fx.empty:
        return pd.Series(dtype=float)
    return fx.set_index(pd.to_datetime(fx["date"]))["adjusted_close"].sort_index()


def a_pesos(panel: pd.DataFrame, fx: pd.Series, columnas_usd: list[str]) -> pd.DataFrame:
    """Convierte a pesos las columnas cotizadas en dólares, arrastrando el último
    tipo de cambio conocido cuando el mercado local no publicó dato ese día."""
    if fx.empty:
        return panel.copy()
    factor = fx.reindex(panel.index.union(fx.index)).ffill().reindex(panel.index)
    salida = panel.copy()
    presentes = [c for c in columnas_usd if c in salida.columns]
    salida[presentes] = salida[presentes].mul(factor, axis=0)
    return salida


def correlaciones(panel_clp: pd.DataFrame, navs: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """Correlación de retornos entre cada instrumento y cada estrategia, sobre la
    ventana en que ambos tienen datos. Devuelve una fila por instrumento."""
    precios = panel_clp.resample(freq).last().pct_change(fill_method=None)
    estrategias = navs.resample(freq).last().pct_change(fill_method=None)
    filas = []
    for ticker in precios.columns:
        fila: dict[str, object] = {"ticker": ticker}
        serie = precios[ticker]
        for nombre in estrategias.columns:
            pareja = pd.concat([serie, estrategias[nombre]], axis=1).dropna()
            fila[nombre] = float(pareja.iloc[:, 0].corr(pareja.iloc[:, 1])) if len(pareja) >= 12 else np.nan
            if nombre == estrategias.columns[0]:
                fila["meses_comunes"] = int(len(pareja))
        filas.append(fila)
    return pd.DataFrame(filas).set_index("ticker")


def metricas_por_instrumento(panel_clp: pd.DataFrame) -> pd.DataFrame:
    """Retorno anualizado, volatilidad, peor caída y sesiones disponibles, en pesos."""
    filas = []
    for ticker in panel_clp.columns:
        serie = panel_clp[ticker].dropna()
        if len(serie) < 2:
            filas.append({"ticker": ticker, "sesiones": len(serie), "cagr": np.nan, "vol": np.nan, "mdd": np.nan, "desde": ""})
            continue
        metricas = performance_metrics(serie.reset_index(drop=True), pd.Series(serie.index))
        filas.append({
            "ticker": ticker,
            "sesiones": int(len(serie)),
            "desde": serie.index.min().date().isoformat(),
            "cagr": metricas["cagr"],
            "vol": metricas["vol"],
            "mdd": metricas["mdd"],
        })
    return pd.DataFrame(filas).set_index("ticker")


def clasificar(tabla: pd.DataFrame, columna_conjunto: str = "Conjunto AlphaData", umbral_redundante: float = .75) -> pd.Series:
    """Etiqueta cada instrumento según cuánto aporta al conjunto actual."""
    correlacion = tabla[columna_conjunto]
    return pd.Series(
        np.select(
            [correlacion.isna(), correlacion >= umbral_redundante, correlacion >= .45, correlacion >= .15],
            ["sin historia suficiente", "redundante", "aporta poco", "aporta"],
            default="diversifica",
        ),
        index=tabla.index,
    )


def selector_rotacion(n: int = N_ROTACION, solo_tendencia: bool = True):
    """Rotación mensual: top-N por momentum compuesto 3/6/12, igual ponderado.

    Es la misma señal de Gamma-6, aplicada al universo de ETF sólo para ver qué
    da este conjunto de activos; no es una metodología propuesta.
    """
    def selector(panel: pd.DataFrame, review: pd.Timestamp):
        close = panel.loc[:review]
        if len(close) < MIN_SESIONES:
            return pd.Series(dtype=float), 0
        lag = lambda k: close.shift(k).iloc[-1]  # noqa: E731
        historia = close.notna().sum() >= MIN_SESIONES
        r3, r6, r12 = close.iloc[-1] / lag(63) - 1, lag(21) / lag(126) - 1, lag(21) / lag(252) - 1
        marco = pd.DataFrame({"r3": r3, "r6": r6, "r12": r12})[historia].dropna()
        if marco.empty:
            return pd.Series(dtype=float), 0
        z = lambda s: (s - s.mean()) / s.std() if s.std() else s * 0.0  # noqa: E731
        score = (2 * z(marco.r3) + z(marco.r6) + z(marco.r12)) / 4
        if solo_tendencia:
            sma200 = close.rolling(200, min_periods=200).mean().iloc[-1]
            score = score[close.iloc[-1].reindex(score.index) > sma200.reindex(score.index)]
        if score.empty:
            return pd.Series(dtype=float), 0
        return equal_weights(score.sort_values(ascending=False).head(n).index), int(len(score))
    return selector


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------

def _fmt(valor, pct=True, dec=1):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    return f"{valor:.{dec}%}" if pct else f"{valor:+.2f}"


def construir_informe(universo: pd.DataFrame, panel_clp: pd.DataFrame, faltantes: list[str], corr_mensual: pd.DataFrame, corr_semanal: pd.DataFrame, metricas: pd.DataFrame, rotaciones: dict[str, dict]) -> str:
    tabla = metricas.join(corr_mensual, how="left")
    tabla = tabla.join(universo.set_index("alphadata_ticker")[["nombre", "categoria"]], how="left")
    tabla["aporte"] = clasificar(tabla)
    tabla = tabla.sort_values("Conjunto AlphaData", na_position="last")
    tabla.to_csv(OUT / "candidatos.csv")

    lineas = [
        "# Candidatos de ETF para una cuarta estrategia", "",
        f"Generado automáticamente. Universo: {len(universo)} instrumentos; con datos utilizables: {panel_clp.shape[1]}.",
        "Todo está medido **en pesos**: los precios en dólares se convierten con el tipo de cambio diario, porque la correlación que importa es la que enfrenta un inversionista local.", "",
    ]
    if faltantes:
        lineas += [f"**Sin datos en Yahoo ({len(faltantes)}):** {', '.join(faltantes)}. Para los ETF locales esto sólo significa que el símbolo supuesto no existe; hay que buscar el correcto o descartarlos.", ""]

    lineas += ["## Los que más diversifican", "", "Correlación de retornos mensuales contra cada estrategia. Mientras más baja, más aporta al conjunto.", "",
               "| ETF | Qué es | Categoría | Corr. conjunto | Sigma-6 | Delta-12 | Gamma-6 | Retorno anual | Peor caída | Meses |",
               "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for ticker, fila in tabla.head(15).iterrows():
        lineas.append(f"| {ticker} | {fila.nombre} | {fila.categoria} | {_fmt(fila['Conjunto AlphaData'], False)} | {_fmt(fila['Sigma-6'], False)} | {_fmt(fila['Delta-12'], False)} | {_fmt(fila['Gamma-6'], False)} | {_fmt(fila.cagr)} | {_fmt(fila.mdd)} | {int(fila.meses_comunes) if pd.notna(fila.get('meses_comunes')) else '—'} |")

    lineas += ["", "## Los redundantes", "", "Replican lo que el conjunto ya tiene; agregarlos sube el riesgo sin diversificar.", "",
               "| ETF | Qué es | Corr. conjunto | Retorno anual |", "| --- | --- | ---: | ---: |"]
    for ticker, fila in tabla[tabla.aporte == "redundante"].sort_values("Conjunto AlphaData", ascending=False).head(12).iterrows():
        lineas.append(f"| {ticker} | {fila.nombre} | {_fmt(fila['Conjunto AlphaData'], False)} | {_fmt(fila.cagr)} |")

    lineas += ["", "## Resumen por categoría", "", "| Categoría | Instrumentos | Corr. conjunto (mediana) | Retorno anual (mediana) |", "| --- | ---: | ---: | ---: |"]
    for categoria, grupo in tabla.groupby("categoria"):
        lineas.append(f"| {categoria} | {len(grupo)} | {_fmt(grupo['Conjunto AlphaData'].median(), False)} | {_fmt(grupo.cagr.median())} |")

    lineas += ["", "## Qué daría una rotación sobre este universo", "",
               "Referencia, no propuesta: la misma señal de Gamma-6 (momentum compuesto 3/6/12) aplicada a los ETF, para ver qué hay acá.", "",
               "| Variante | Retorno anual | Volatilidad | Peor caída | Sharpe | Posiciones |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for nombre, datos in rotaciones.items():
        m = datos["metricas"]
        lineas.append(f"| {nombre} | {_fmt(m['cagr'])} | {_fmt(m['vol'])} | {_fmt(m['mdd'])} | {_fmt(m['sharpe'], False)} | {datos['posiciones']:.1f} |")

    lineas += ["", "## Cómo leer esto", "",
               "- La correlación se mide sobre la ventana común con el seguimiento de las estrategias, que parte en julio de 2021. Son pocos años: sirve para descartar lo obviamente redundante, no para afinar.",
               "- Un ETF con correlación baja **no** es por sí solo una buena estrategia; puede ser simplemente un activo malo que se mueve distinto. Hay que mirar juntas las dos columnas: correlación y retorno.",
               "- `candidatos.csv` trae la tabla completa con los 56, la correlación semanal y las métricas por instrumento.",
               "- Los ETF locales aparecen sólo si Yahoo tiene su símbolo; su mandato está por confirmar y hay que verificarlo antes de usarlos.", ""]
    return "\n".join(lineas)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    universo = pd.read_csv(UNIVERSE_PATH, dtype=str).fillna("")
    tickers = universo["yahoo_ticker"].tolist()

    print(f"Descargando {len(tickers)} instrumentos...")
    precios = download_prices(tickers, start=PRICES_START)
    precios.to_csv(OUT / "prices_daily.csv", index=False)
    panel = to_panel(precios)
    panel.columns = [universo.set_index("yahoo_ticker")["alphadata_ticker"].get(c, c) for c in panel.columns]
    faltantes = sorted(set(universo["alphadata_ticker"]) - set(panel.columns))
    if faltantes:
        print(f"Sin datos: {faltantes}")

    oficiales = pd.read_csv(PRICES_OFICIALES, parse_dates=["date"])
    fx = serie_fx(oficiales)
    if fx.empty:
        raise RuntimeError("No se encontró la serie USDCLP en data/market_prices_daily.csv; la corrida oficial debe haberla descargado antes.")
    usd = universo.loc[universo.moneda == "USD", "alphadata_ticker"].tolist()
    panel_clp = a_pesos(panel, fx, usd)
    panel_clp.to_csv(OUT / "precios_clp.csv")

    navs = pd.read_csv(NAV_HISTORICO, parse_dates=["date"]).rename(columns={"IPSA Total Return": "IPSA TR"}).set_index("date").sort_index()
    navs = navs[[c for c in ESTRATEGIAS if c in navs.columns]]
    if navs.empty:
        raise RuntimeError("data/historical_model_nav.csv no tiene las series de estrategias esperadas.")

    corr_mensual = correlaciones(panel_clp, navs, "ME")
    corr_semanal = correlaciones(panel_clp, navs, "W-FRI")
    corr_mensual.to_csv(OUT / "correlacion_mensual.csv")
    corr_semanal.to_csv(OUT / "correlacion_semanal.csv")
    metricas = metricas_por_instrumento(panel_clp)

    elegibles = [c for c in panel_clp.columns if panel_clp[c].notna().sum() >= MIN_SESIONES * 2]
    inicio = pd.Timestamp("2016-01-04")
    rotaciones: dict[str, dict] = {}
    for nombre, solo_tendencia in [(f"Top {N_ROTACION} con filtro de tendencia", True), (f"Top {N_ROTACION} sin filtro", False)]:
        nav, señales = run_backtest(panel_clp[elegibles], inicio, panel_clp.index.max(), selector_rotacion(N_ROTACION, solo_tendencia), COSTO)
        nav.to_csv(OUT / f"nav_rotacion_{'tendencia' if solo_tendencia else 'simple'}.csv", index=False)
        señales.to_csv(OUT / f"signals_rotacion_{'tendencia' if solo_tendencia else 'simple'}.csv", index=False)
        rotaciones[nombre] = {"metricas": performance_metrics(nav["nav"], nav["date"]), "posiciones": señales["n_selected"].mean() if len(señales) else 0.0}

    informe = construir_informe(universo, panel_clp, faltantes, corr_mensual, corr_semanal, metricas, rotaciones)
    (OUT / "RESULTS.md").write_text(informe, encoding="utf-8")
    resumen = {"instrumentos_con_datos": int(panel_clp.shape[1]), "faltantes": faltantes, "rotaciones": {k: v["metricas"] for k, v in rotaciones.items()}}
    (OUT / "summary.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(informe)


if __name__ == "__main__":
    main()
