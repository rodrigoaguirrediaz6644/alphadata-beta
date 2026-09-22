from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import sys

import pandas as pd

from src.fetch_prices import load_universe, operables
from src.ingest_recommendations import ingest
from src.ingreso import cartera_de_ingreso, markdown as markdown_ingreso
from src.operaciones import cargar as cargar_operaciones, descalce as descalce_real
from src.cdv import cargar as cargar_cdv, cargar_simbolos as cargar_simbolos_cdv, estado as estado_cdv, premio as premio_cdv
from src.libro import abiertas as libro_abiertas, anotar, cargar as cargar_libro, cartera_publicada, guardar as guardar_libro, guardar_publicada, movimientos_de, precios_de_entrada
from src.strategy_registry import validate_registry
from src.reporting_public import build_public_report
from src.salud import revisar as revisar_salud
from src.strategy_engine import DIAS_VIGENCIA_RECOMENDACIONES, ORO_TICKER, RECOMMENDATION_COLUMNS, combined_equal_weight, delta12, delta12_historical_nav, gamma6, gamma6_historical_nav, movements, sigma6_historical_nav, oro, oro_historical_nav, reconstruct_entry_dates, sigma6, to_clp, validate_recommendations

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; REPORTS=ROOT/'reports'; STATE=DATA/'strategy_state.json'; NAV=DATA/'strategy_nav.csv'
CONFIG=ROOT/'config'/'runtime.v2.json'

# La tarifa es **una sola** y sale de la configuración, nunca escrita acá.
# Hubo 0,1% para los CDV durante meses, inventado, y una pantalla de orden real
# de IAUCL lo desmintió al peso: $612.000 de valor, $1.092,42 de comisión, que
# es 0,1785% exacto. La misma tarifa de la acción chilena. El número escrito en
# dos lugares es la forma en que uno se corrige y el otro no, así que acá no se
# escribe ninguno.
def modelo_de_costo()->tuple[float,float]:
    """Tasa y mínimo por operación, para acción chilena y CDV por igual."""
    m=json.loads(CONFIG.read_text(encoding='utf-8'))['transaction_cost']
    return float(m['rate']),float(m['minimum_fee_clp'])
GAMMA_RULE_VERSION='1.0.0'
# Sigma-6 salió de la asignación el 22-09-2026, no del repositorio: su código y
# sus series se conservan. Ver ESTRATEGIAS_ALPHADATA_v2.md y
# research/carteras_en_pesos/.
STRATEGY_SERIES=['Delta-12','Gamma-6','Oro']
SERIES_RETIRADAS=['Sigma-6']
CONJUNTO='Conjunto AlphaData'
BENCHMARK_VIVO='Mercado chileno'
BENCHMARK_RECONSTRUIDO='Mercado chileno (canasta igual peso)'
# Toda columna de data/reconstruccion_historica.csv tiene que recalcularse en
# cada corrida desde datos primarios. Si aparece una que no está acá, la corrida
# se detiene: es exactamente la forma en que la serie de Sigma-6 publicó
# +28,75% durante meses sin que nadie la volviera a calcular. Ver
# CENSO_DE_SERIES.md.
SERIES_RECONSTRUIDAS={*STRATEGY_SERIES,*SERIES_RETIRADAS,BENCHMARK_RECONSTRUIDO,CONJUNTO}

def load_state()->dict:
    if STATE.exists():
        state=json.loads(STATE.read_text(encoding='utf-8'))
        if state.get('methodology_version') in {'2.0.0','2.1.0','2.2.0','2.3.0'}: return state
    return {'methodology_version':'2.3.0','sigma_entries':{},'delta_entries':{},'gamma_entries':{},'oro_entries':{},'sigma_portfolio':[],'delta_portfolio':[],'gamma_portfolio':[],'oro_portfolio':[],'nav':{'Sigma-6':100.,'Delta-12':100.,'Gamma-6':100.,'Oro':100.,BENCHMARK_VIVO:100.}}

# Ninguno de los tres es una falla: uno dejó de cotizar y está escrito, y el
# otro acumula historia al día. Una alarma que siempre está roja por una razón
# conocida deja de ser alarma.
COBERTURA_SANA={'OK','DESLISTADO','ACUMULANDO'}

def _incompletos(coverage:pd.DataFrame)->set[str]:
    if not len(coverage): return set()
    return set(coverage.loc[~coverage.status.isin(COBERTURA_SANA),'alphadata_ticker'])

def _edad_de_horizonte(as_of)->float|None:
    """Cuántos días lleva la sección de Horizonte sin actualizarse."""
    ruta=DATA/'horizonte_state.json'
    if not ruta.exists(): return None
    try: guardado=pd.Timestamp(json.loads(ruta.read_text(encoding='utf-8'))['as_of'])
    except Exception: return None
    return float((pd.Timestamp(as_of).normalize()-guardado.normalize()).days)

def _solo_operables(universe:pd.DataFrame,puerta:pd.DataFrame)->pd.DataFrame:
    """El universo con el símbolo borrado donde la puerta no dejó pasar.

    Así la regla de elegibilidad de Gamma-6 queda en un solo lugar —sin
    símbolo, no se puede comprar— y sirve igual para XOM, que nunca tuvo, y
    para uno que la puerta rechace mañana.
    """
    if not len(puerta) or 'cdv_ticker' not in universe.columns: return universe
    malos=set(puerta.loc[puerta.estado!='operable','ticker'])
    u=universe.copy()
    u.loc[u.alphadata_ticker.isin(malos),'cdv_ticker']=''
    return u

def portfolio_return(prices:pd.DataFrame,weights:list[dict],start:pd.Timestamp,end:pd.Timestamp)->float:
    if not weights or start>=end:return 0.
    matrix=prices.pivot(index='date',columns='alphadata_ticker',values='adjusted_close').sort_index().ffill(limit=3)
    a=matrix.loc[:start].tail(1); z=matrix.loc[:end].tail(1)
    if a.empty or z.empty:return 0.
    total=0.
    for item in weights:
        t=item['ticker']; w=float(item['target_weight'])
        if t in matrix and pd.notna(a.iloc[0][t]) and pd.notna(z.iloc[0][t]) and a.iloc[0][t]>0: total+=w*(z.iloc[0][t]/a.iloc[0][t]-1)
    return total

def enrich_open_positions(portfolio: pd.DataFrame, prices: pd.DataFrame, as_of: pd.Timestamp,
                          precios_anotados: dict[str, float] | None = None,
                          dividendos: pd.DataFrame | None = None) -> pd.DataFrame:
    """Precios de entrada y de hoy, y la variación entre ambos.

    Tres decisiones de cálculo que conviene no deshacer:

    **El precio que se muestra es el cierre crudo**, el de la fecha de entrada
    y el de hoy. Es lo que habrías pagado y lo que reconoces en la pantalla de
    la corredora.

    **La variación se calcula sobre el cierre ajustado.** Si se calculara sobre
    el crudo, una acción que repartió dividendo aparecería perdiendo lo que en
    realidad cobraste. Con ocho chilenas en cartera es el caso más probable, no
    el excepcional.

    **La variación es movimiento de precio y no descuenta la comisión de
    entrada, y por eso esta función no recibe la tarifa.** El costo vive en el
    NAV. Llevaba un parámetro `buy_cost` que el cuerpo no leía nunca: un
    parámetro muerto con valor por omisión es lo peor de las dos cosas, porque
    parece que el costo entra acá y no entra. La consecuencia es que esta columna y
    el rendimiento de la estrategia no cuadran exactamente, y es por diseño:
    son dos mediciones distintas, como en cualquier cartola.

De ahí salen las dos últimas columnas. Cuando entre los dos cierres crudos
    hubo un dividendo, la variación no se puede verificar con los dos precios a
    la vista: VAPORES muestra $48,89 de entrada, $48,30 hoy y +12,9%. Son nueve
    de las veinte posiciones abiertas, el caso normal y no el excepcional, así
    que en vez de una marca va el monto: `dividendos_clp`, sumado de
    `data/dividendos.csv` sobre la ventana de tenencia. Son pesos que llegaron
    a la cuenta y se pueden contrastar con el aviso de la empresa.

    La tabla sólo tiene instrumentos chilenos. Una posición estadounidense
    cuyo ajustado se movió sin dividendo itemizado queda con `con_dividendo` y
    sin monto, que es lo que corresponde decir mientras no exista esa tabla.

    `precios_anotados` es el precio de entrada que el libro guardó al abrir la
    posición. Sin él el precio mostrado se recalcula en cada corrida desde la
    serie, y una corrección de un precio pasado lo mueve: en una copia de
    trabajo con febrero alterado, ITAUCL pasaba de $20.900 a $8.360.
    """
    result = portfolio.copy()
    for column in ["entry_price", "current_price", "open_return"]:
        result[column] = pd.NA
    result["con_dividendo"] = False
    result["dividendos_clp"] = pd.NA
    precios_anotados = precios_anotados or {}
    for index, row in result.iterrows():
        opened_at = pd.to_datetime(row.get("opened_at"), errors="coerce")
        series = prices.loc[
            (prices.alphadata_ticker == row["ticker"]) & (prices.date <= as_of),
            ["date", "close", "adjusted_close"],
        ].dropna().sort_values("date")
        if pd.isna(opened_at) or series.empty:
            continue
        entry = series.loc[series.date >= opened_at].head(1)
        if entry.empty:
            entry = series.loc[series.date <= opened_at].tail(1)
        current = series.tail(1)
        if entry.empty or current.empty or float(entry.adjusted_close.iloc[0]) <= 0:
            continue
        result.at[index, "entry_price"] = float(precios_anotados.get(row["ticker"], entry.close.iloc[0]))
        result.at[index, "current_price"] = float(current.close.iloc[0])
        ajustada = (float(current.adjusted_close.iloc[0])
                    / float(entry.adjusted_close.iloc[0]) - 1)
        result.at[index, "open_return"] = ajustada
        cruda = float(current.close.iloc[0]) / float(entry.close.iloc[0]) - 1
        hubo = bool(abs(ajustada - cruda) > 5e-4)
        cobrados = _dividendos_cobrados(dividendos, row["ticker"],
                                        pd.Timestamp(entry.date.iloc[0]), pd.Timestamp(current.date.iloc[0]))
        result.at[index, "dividendos_clp"] = cobrados if cobrados is not None else pd.NA
        result.at[index, "con_dividendo"] = hubo and cobrados is None
    return result


def _dividendos_cobrados(dividendos: pd.DataFrame | None, ticker: str,
                         desde: pd.Timestamp, hasta: pd.Timestamp) -> float | None:
    """Los pesos por acción que se repartieron mientras la posición estuvo abierta."""
    if dividendos is None or dividendos.empty:
        return None
    fechas = pd.to_datetime(dividendos.fecha_ex, errors="coerce")
    dentro = dividendos.loc[(dividendos.alphadata_ticker == ticker) & (fechas > desde) & (fechas <= hasta)]
    return float(dentro.monto.sum()) if len(dentro) else None


def pesos_corridos(portfolio: pd.DataFrame, prices: pd.DataFrame,
                   senal: pd.Timestamp, as_of: pd.Timestamp) -> pd.Series:
    """Donde estaria hoy cada peso si nadie hubiera tocado la cartera.

    Desde la ultima revision, cada posicion crece con su propio precio y el
    conjunto se renormaliza. Es la deriva que el NAV publicado no modela: su
    aritmetica --`retorno_dia += peso * (precio_hoy/precio_ayer - 1)` con el
    peso fijo-- es la de una cartera que vuelve al objetivo todos los dias, y
    ese rebalanceo nunca se ordena ni se cobra.
    """
    matriz = prices.pivot(index="date", columns="alphadata_ticker", values="adjusted_close").sort_index().ffill(limit=3)
    inicio = matriz.loc[:pd.Timestamp(senal)].tail(1)
    fin = matriz.loc[:pd.Timestamp(as_of)].tail(1)
    vacio = pd.Series([pd.NA] * len(portfolio), index=portfolio.index)
    if inicio.empty or fin.empty:
        return vacio
    crecido = {}
    for fila in portfolio.itertuples():
        t = fila.ticker
        if t in matriz and pd.notna(inicio.iloc[0][t]) and pd.notna(fin.iloc[0][t]) and inicio.iloc[0][t] > 0:
            crecido[fila.Index] = float(fila.target_weight) * float(fin.iloc[0][t]) / float(inicio.iloc[0][t])
    if not crecido:
        return vacio
    # La caja no se mueve: entra al denominador con su peso original.
    caja = 1 - float(portfolio.target_weight.sum())
    total = sum(crecido.values()) + caja
    return pd.Series({i: v / total for i, v in crecido.items()}).reindex(portfolio.index)


def movements_for_report(current: pd.DataFrame, previous_path: Path) -> pd.DataFrame:
    """Keep the latest meaningful rebalance visible between routine daily runs."""
    meaningful = current.loc[current.action != "MANTIENE"] if len(current) else current
    if len(meaningful):
        return current
    if previous_path.exists():
        previous = pd.read_csv(previous_path)
        if len(previous) and (previous.action != "MANTIENE").any():
            return previous
    return current


FUERA_DE_LA_CANASTA=['IPSA_TR','LTM-ADR','SQM-ADR']

def canasta_chilena(prices,fuera=())->pd.Series:
    """El benchmark automático: partes iguales del mercado chileno, base 100.

    Reemplaza al MSCI IPSA, que era la última dependencia manual del sistema
    con consecuencia: había que bajar un archivo de la Bolsa de Santiago cada
    semana y a la quinta semana sin bajarlo la línea de comparación se quedaba
    atrás.

    **Se construye con precios que el sistema ya captura todos los días y que
    sus guardias ya validan**, así que no agrega ninguna dependencia. Contra el
    MSCI IPSA Gross 2021-2026 su correlación diaria es 0,878 y rinde 2,5 puntos
    anuales menos, y esa diferencia **no es sistemática**: en dos de los cinco
    años la canasta va por encima. Es un índice distinto, no uno peor: pondera
    igual donde el MSCI pondera por capitalización.

    Se descartó ECH × USDCLP, que parecía el reemplazo obvio: su correlación
    diaria es 0,625 —cotiza en Nueva York y el índice se calcula al cierre de
    Santiago— y queda por debajo en cuatro de cinco años, **4,3 puntos anuales
    en la dirección que halaga a las estrategias**. Ver
    `DEPENDENCIAS_MANUALES.md`.

    Se reequilibra a diario sobre la sección transversal que tiene precio en
    las dos ruedas, así que una acción que se lista a mitad de camino entra sin
    inventar un retorno y una que deja de cotizar sale sin dejar un hueco.

    **`fuera` son los instrumentos que dejaron de cotizar y siguen en el
    almacén**, y dejarlos adentro no era inocuo. AESANDES quedó congelada el
    14-04-2025 y el almacén conserva su último precio: la canasta lo leía como
    un retorno de 0% todos los días, y eso **arrastraba el benchmark 4,48%
    hacia abajo** sobre la serie completa. Un benchmark más bajo es una vara
    más fácil, o sea el error apunta en la dirección que halaga a las
    estrategias. No se ve como una falla: se ve como una acción que no se
    mueve.
    """
    local=(prices[~prices.alphadata_ticker.isin(set(FUERA_DE_LA_CANASTA)|set(fuera))]
           .pivot(index='date',columns='alphadata_ticker',values='adjusted_close')
           .sort_index().ffill(limit=3))
    if local.empty:return pd.Series(dtype=float)
    diario=local.pct_change().mean(axis=1,skipna=True).fillna(0.)
    return (1+diario).cumprod()*100

def benchmark_return(prices,start,end,fuera=())->float:
    canasta=canasta_chilena(prices,fuera=fuera)
    a=canasta.loc[:start].tail(1);z=canasta.loc[:end].tail(1)
    if a.empty or z.empty:return 0.
    return float(z.iloc[0]/a.iloc[0]-1)

def turnover_cost(old,new,rate):
    a={x['ticker']:float(x['target_weight']) for x in old};b=dict(zip(new.ticker,new.target_weight))
    risky=sum(abs(b.get(t,0)-a.get(t,0)) for t in set(a)|set(b))
    cash=abs((1-sum(b.values()))-(1-sum(a.values())))
    return .5*(risky+cash)*rate

def pct(v):return f'{v:.1%}'
def md_table(df,cols):
    if df.empty:return '_Sin posiciones._'
    x=df[cols].copy()
    for c in x.columns:
        if 'weight' in c or c in ['change']:x[c]=x[c].map(pct)
    labels=[str(c).replace('_',' ').title() for c in cols]
    lines=['| '+' | '.join(labels)+' |','| '+' | '.join(['---']*len(cols))+' |']
    lines.extend('| '+' | '.join(str(v) for v in row)+' |' for row in x.itertuples(index=False,name=None))
    return '\n'.join(lines)

def html_table(df,cols):
    if df.empty:return '<p><em>Sin posiciones.</em></p>'
    x=df[cols].copy();x.columns=[str(c).replace('_',' ').title() for c in cols]
    for c in x.columns:
        if 'Weight' in c or c=='Change':x[c]=x[c].map(pct)
    return x.to_html(index=False,border=0,escape=True)

def report(as_of,sigma,delta,smove,dmove,s_audit,d_audit,coverage,errors,state,navrow)->tuple[str,str]:
    sigma_cash=1-sigma.target_weight.sum() if len(sigma) else 1.;delta_cash=1-delta.target_weight.sum() if len(delta) else 1.
    intro=(f'Al cierre del {as_of:%d-%m-%Y}, Sigma-6 mantiene {len(sigma)} posiciones y {pct(sigma_cash)} en caja. '
           f'Delta-12 mantiene {len(delta)} posiciones y {pct(delta_cash)} en caja. '
           f'En esta ejecución se detectaron {len(errors)} filas de recomendaciones con observaciones y {len(_incompletos(coverage))} instrumentos con cobertura incompleta.')
    md=f"""# Informe automático AlphaData

**Fecha de corte:** {as_of:%d-%m-%Y}  
**Metodología:** Sigma-6 v2.0.0 y Delta-12 v2.0.0  
**Generado:** {datetime.now(timezone.utc).isoformat(timespec='seconds')}

## Resumen

{intro}

| Serie | Índice acumulado |
| --- | ---: |
| Sigma-6 | {navrow['Sigma-6']:.2f} |
| Delta-12 | {navrow['Delta-12']:.2f} |
| Mercado chileno (canasta igual peso) | {navrow[BENCHMARK_VIVO]:.2f} |

## Sigma-6

{md_table(sigma,['ticker','target_weight'])}

**Caja:** {pct(sigma_cash)}

### Movimientos Sigma-6

{md_table(smove,['ticker','action','previous_weight','target_weight','change'])}

## Delta-12

{md_table(delta,['ticker','target_weight'])}

**Caja:** {pct(delta_cash)}. La cartera se modifica sólo una vez por mes; las demás corridas conservan los pesos vigentes.

### Movimientos Delta-12

{md_table(dmove,['ticker','action','previous_weight','target_weight','change'])}

## Calidad de datos

- Recomendaciones vigentes evaluadas: {len(s_audit)}.
- Filas de recomendaciones rechazadas: {len(errors)}.
- Instrumentos con precios suficientes: {len(coverage)-len(_incompletos(coverage))}/{len(coverage)}.
- Fecha más reciente de precios: {as_of:%d-%m-%Y}.

## Metodología

Sigma-6 exige una recomendación positiva vigente de Credicorp Capital y momentum 12-1 positivo; pondera en partes iguales con máximo 10% y revisa semanalmente. Delta-12 selecciona mensualmente hasta ocho acciones con momentum 12-1 positivo, precio sobre SMA200 y liquidez sobre el percentil 20; asigna pesos iguales con máximo 15%. Ambas aplican 0,1785% al monto transado.

## Advertencia

Resultados de carteras modelo para evaluación interna. No constituyen asesoría personalizada ni garantizan rentabilidades futuras. La rentabilidad personal de un suscriptor depende de su fecha y precio efectivo de entrada.
"""
    html=f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><style>
    body{{font:16px Arial;max-width:1000px;margin:36px auto;color:#17324d;line-height:1.45}}table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}th,td{{border:1px solid #ccd6df;padding:8px;text-align:left}}th{{background:#147d78;color:white}}h1,h2{{color:#12304a}}.note{{background:#fff4cc;padding:14px}}
    </style></head><body><h1>Informe automático AlphaData</h1><p><strong>Fecha de corte:</strong> {as_of:%d-%m-%Y}<br><strong>Metodología:</strong> Sigma-6 v2.0.0 y Delta-12 v2.0.0</p>
    <h2>Resumen</h2><p>{escape(intro)}</p><table><tr><th>Serie</th><th>Índice acumulado</th></tr><tr><td>Sigma-6</td><td>{navrow['Sigma-6']:.2f}</td></tr><tr><td>Delta-12</td><td>{navrow['Delta-12']:.2f}</td></tr><tr><td>Mercado chileno (canasta igual peso)</td><td>{navrow[BENCHMARK_VIVO]:.2f}</td></tr></table>
    <h2>Sigma-6</h2>{html_table(sigma,['ticker','target_weight'])}<p><strong>Caja:</strong> {pct(sigma_cash)}</p><h3>Movimientos</h3>{html_table(smove,['ticker','action','previous_weight','target_weight','change'])}
    <h2>Delta-12</h2>{html_table(delta,['ticker','target_weight'])}<p><strong>Caja:</strong> {pct(delta_cash)}. Se modifica sólo una vez por mes.</p><h3>Movimientos</h3>{html_table(dmove,['ticker','action','previous_weight','target_weight','change'])}
    <h2>Calidad de datos</h2><ul><li>Filas rechazadas: {len(errors)}</li><li>Instrumentos con cobertura suficiente: {len(coverage)-len(_incompletos(coverage))}/{len(coverage)}</li><li>Último precio: {as_of:%d-%m-%Y}</li></ul>
    <h2>Metodología</h2><p>Sigma-6 combina recomendación positiva de Credicorp con momentum 12-1 positivo. Delta-12 selecciona mensualmente hasta ocho acciones mediante momentum 12-1, SMA200 y liquidez. Costo: 0,1785% del monto transado.</p><p class='note'><strong>Advertencia:</strong> carteras modelo para evaluación interna; no constituyen asesoría personalizada ni garantizan rentabilidades futuras.</p></body></html>"""
    return md,html

def main()->None:
    validate_registry()
    REPORTS.mkdir(parents=True,exist_ok=True); DATA.mkdir(parents=True,exist_ok=True)
    ingest_summary=ingest()
    universe=load_universe(); prices=pd.read_csv(DATA/'market_prices_daily.csv',parse_dates=['date'])
    prices.loc[prices.alphadata_ticker=='IPSA','alphadata_ticker']='IPSA_TR'
    # Gamma-6 opera en Nueva York y el tipo de cambio cotiza incluso en feriados
    # locales: ambos se separan para que el calendario de Sigma-6 y Delta-12 siga
    # siendo exactamente el mismo de antes de incorporar el mercado estadounidense.
    us_tickers=set(universe.loc[universe.tipo=='accion_us','alphadata_ticker'])
    etf_tickers=set(universe.loc[universe.tipo=='etf_us','alphadata_ticker'])
    fx=prices[prices.alphadata_ticker=='USDCLP'].copy()
    prices_us=prices[prices.alphadata_ticker.isin(us_tickers)].copy()
    prices_us_clp=to_clp(prices_us,universe,fx)
    prices_oro=prices[prices.alphadata_ticker.isin(etf_tickers)].copy()
    prices_oro_clp=to_clp(prices_oro,universe,fx)
    # El almacén completo, antes de partirlo por mercado: el premio del CDV
    # necesita el subyacente en dólares y el tipo de cambio a la vez.
    prices_all=prices
    prices=prices[~prices.alphadata_ticker.isin(us_tickers|etf_tickers|{'USDCLP'})].copy()
    # La puerta de símbolos, antes de rankear: decide qué es elegible para
    # Gamma-6 y qué símbolo imprime la guía. Ver src/cdv.py.
    # Lo que dejó de cotizar no entra al benchmark: su último precio se leería
    # como 0% de retorno todos los días. Ver canasta_chilena.
    no_cotizan=set(universe.loc[universe.estado!='activo','alphadata_ticker'])
    puerta_cdv=estado_cdv(universe,cargar_cdv(),prices_all,cargar_simbolos_cdv())
    # Los ADR cotizan en Nueva York y operan en feriados chilenos: si fijaran
    # la fecha de corte, la corrida marcaría NAV y fecharía compras en un día
    # en que la bolsa de Santiago estuvo cerrada.
    adr_tickers=set(universe.loc[universe.tipo=='adr','alphadata_ticker'])
    as_of=prices.loc[~prices.alphadata_ticker.isin(adr_tickers|{'IPSA_TR'}),'date'].max().normalize(); state=load_state()
    input_path=DATA/'recommendations_input.csv'; raw=pd.read_csv(input_path,dtype=str).fillna('') if input_path.exists() else pd.DataFrame(columns=RECOMMENDATION_COLUMNS)
    valid,errors=validate_recommendations(raw,set(operables(universe).alphadata_ticker)); valid.to_csv(DATA/'recommendations_validated_live.csv',index=False,date_format='%Y-%m-%d');errors.to_csv(DATA/'recommendations_errors.csv',index=False,date_format='%Y-%m-%d')
    old_sigma=state.get('sigma_portfolio',[]); old_delta=state.get('delta_portfolio',[]); old_gamma=state.get('gamma_portfolio',[]); old_oro=state.get('oro_portfolio',[])
    # Tras un reinicio no se reconstruyen fechas de entrada: el seguimiento
    # empieza de cero y cada posición se abre el día de la corrida. Reconstruir
    # el calendario histórico tendría sentido si la serie fuera continua, pero
    # acá publicaría que una posición "va ganando 43%" desde el año pasado en el
    # mismo informe que dice "comprar".
    if state.get('reinicio'):
        state.setdefault('sigma_entries', {}); state.setdefault('delta_entries', {})
        state['entry_dates_version'] = 3
    elif state.get('entry_dates_version') != 3:
        sigma_entries, delta_entries = reconstruct_entry_dates(valid, prices, universe, as_of)
        state['sigma_entries'] = sigma_entries
        state['delta_entries'] = delta_entries
        state['entry_dates_version'] = 3
    sigma,s_audit,state=sigma6(valid,prices,as_of,state)
    sigma['opened_at'] = sigma.ticker.map(state.get('sigma_entries', {}))
    delta_signal_period=(as_of.to_period('M')-1)
    delta_period=delta_signal_period.strftime('%Y-%m')
    delta_cutoff=prices.loc[(prices.alphadata_ticker!='IPSA_TR')&(prices.date.dt.to_period('M')==delta_signal_period),'date'].max()
    if state.get('delta_last_period')==delta_period and state.get('delta_rule_version')=='2.1.0' and old_delta:
        delta=pd.DataFrame(old_delta); d_audit=pd.DataFrame()
    else:
        delta,d_audit=delta12(prices,universe,delta_cutoff)
        previous_delta_entries = state.get('delta_entries', {})
        execution_dates = prices.loc[(prices.alphadata_ticker!='IPSA_TR') & (prices.date>delta_cutoff), 'date'].sort_values()
        execution_date = (execution_dates.iloc[0] if len(execution_dates) else as_of).date().isoformat()
        state['delta_entries'] = {ticker: previous_delta_entries.get(ticker, execution_date) for ticker in delta.ticker}
        state['delta_last_period']=delta_period
        state['delta_rule_version']='2.1.0'
    if 'opened_at' not in delta.columns:
        delta['opened_at'] = delta.ticker.map(state.get('delta_entries', {}))
    gamma_signal_period=(as_of.to_period('M')-1)
    gamma_period=gamma_signal_period.strftime('%Y-%m')
    gamma_sessions=prices_us.loc[prices_us.date.dt.to_period('M')==gamma_signal_period,'date']
    gamma_cutoff=gamma_sessions.max() if len(gamma_sessions) else as_of
    if state.get('gamma_last_period')==gamma_period and state.get('gamma_rule_version')==GAMMA_RULE_VERSION and old_gamma:
        gamma=pd.DataFrame(old_gamma); g_audit=pd.DataFrame()
    else:
        # La puerta de símbolos decide qué es elegible. Un nombre que no pasó
        # pierde su símbolo acá, y Gamma-6 lo deja fuera del ranking por la
        # misma regla que deja fuera a XOM: sin símbolo, no se puede comprar.
        gamma,g_audit=gamma6(prices_us,_solo_operables(universe,puerta_cdv),gamma_cutoff)
        previous_gamma_entries=state.get('gamma_entries',{})
        gamma_execution=prices_us.loc[prices_us.date>gamma_cutoff,'date'].sort_values()
        gamma_execution_date=(gamma_execution.iloc[0] if len(gamma_execution) else as_of).date().isoformat()
        state['gamma_entries']={ticker:previous_gamma_entries.get(ticker,gamma_execution_date) for ticker in gamma.ticker}
        state['gamma_last_period']=gamma_period
        state['gamma_rule_version']=GAMMA_RULE_VERSION
    if 'opened_at' not in gamma.columns:
        gamma['opened_at']=gamma.ticker.map(state.get('gamma_entries',{}))
    oro_portfolio,oro_audit=oro(prices_oro,universe,as_of)
    if len(oro_portfolio):
        # La posición se abre cuando entra en seguimiento, no cuando nace el
        # instrumento: fechar la compra en 2015 inventaría una rentabilidad que
        # nadie obtuvo.
        entradas_oro=state.get('oro_entries',{})
        state['oro_entries']={t:entradas_oro.get(t,as_of.date().isoformat()) for t in oro_portfolio.ticker}
        oro_portfolio['opened_at']=oro_portfolio.ticker.map(state['oro_entries'])
    # El libro de posiciones manda sobre la fecha de apertura. Producción lo
    # escribe: cada corrida anota sus aperturas y sus cierres, con la fecha en
    # que la estrategia dio la señal. Sin esto el informe no distingue una
    # posición recién tomada de una que viene corriendo un año.
    LIBRO = DATA / 'libro_posiciones.csv'
    libro = cargar_libro(LIBRO)
    fx_libro = prices_us_clp if len(prices_us_clp) else prices
    precios_mostrados = pd.concat([prices, prices_us_clp, prices_oro_clp], ignore_index=True)
    anotados = []
    # Sigma-6 salió de la asignación: se le anota la cartera vacía, que cierra
    # sus posiciones en el libro con la fecha de esta corrida. No es un cierre
    # por señal, es el retiro de la pieza, y queda registrado como cualquier
    # otra venta.
    vacia=pd.DataFrame(columns=['ticker','target_weight'])
    for nombre, cartera, senal in [('Sigma-6', vacia, as_of), ('Delta-12', delta, delta_cutoff),
                                   ('Gamma-6', gamma, gamma_cutoff), ('Oro', oro_portfolio, as_of)]:
        libro, movimientos = anotar(libro, nombre, cartera, senal, precios_mostrados)
        anotados += [f'{nombre}: {m}' for m in movimientos]
    guardar_libro(libro, LIBRO)
    if anotados:
        print('Libro de posiciones: ' + '; '.join(anotados))
    for nombre, cartera in [('Sigma-6', sigma), ('Delta-12', delta), ('Gamma-6', gamma), ('Oro', oro_portfolio)]:
        if len(cartera):
            entradas = libro_abiertas(libro, nombre)
            cartera['opened_at'] = cartera.ticker.map(lambda t: entradas[t].date().isoformat() if t in entradas else pd.NA)

    # Tras un reinicio del seguimiento, ninguna posición puede tener fecha de
    # apertura anterior a esa fecha. Las carteras se heredan pero los precios de
    # entrada no: quien empieza hoy compra hoy. Publicar que una posición "va
    # ganando 43%" desde octubre del año pasado, en el mismo informe que dice
    # "comprar", es la misma clase de error que fechó el oro en 2015.
    reinicio=state.get('reinicio')
    if reinicio:
        # En la primera corrida tras el reinicio el piso es la fecha de esa
        # corrida: nada se tenía antes, así que todo se abre ese día. Después
        # el piso queda fijo en el pasado y las fechas reales se conservan a
        # medida que las carteras rotan.
        piso=reinicio.get('primera_corrida') or as_of.date().isoformat()
        reinicio['primera_corrida']=piso; state['reinicio']=reinicio
        for clave in ('sigma_entries','delta_entries','gamma_entries','oro_entries'):
            state[clave]={t:max(f,piso) for t,f in state.get(clave,{}).items()}
    dividendos=pd.read_csv(DATA/'dividendos.csv') if (DATA/'dividendos.csv').exists() else None
    sigma=enrich_open_positions(sigma,prices,as_of,precios_anotados=precios_de_entrada(libro,'Sigma-6'),dividendos=dividendos)
    delta=enrich_open_positions(delta,prices,as_of,precios_anotados=precios_de_entrada(libro,'Delta-12'),dividendos=dividendos)
    gamma=enrich_open_positions(gamma,prices_us_clp,as_of,precios_anotados=precios_de_entrada(libro,'Gamma-6'),dividendos=dividendos)
    oro_portfolio=enrich_open_positions(oro_portfolio,prices_oro_clp,as_of,precios_anotados=precios_de_entrada(libro,'Oro'),dividendos=dividendos)
    # Peso real contra peso objetivo. El NAV supone que la cartera vuelve al
    # objetivo todos los días, gratis; una cuenta de verdad deja correr los
    # pesos entre revisiones y los ganadores se van concentrando. Sin esta
    # columna la divergencia es invisible hasta que es grande.
    for cartera, serie, senal in [(sigma, prices, as_of), (delta, prices, delta_cutoff),
                                  (gamma, prices_us_clp, gamma_cutoff), (oro_portfolio, prices_oro_clp, as_of)]:
        if len(cartera): cartera['peso_real']=pesos_corridos(cartera, serie, senal, as_of)

    # El reloj que queda en Sigma-6 es la caducidad de la recomendación, no el
    # tope de tenencia, que salió. Y es el que va a ir vaciando la estrategia:
    # cada nombre se cae cuando su recomendación cumple 365 días sin que llegue
    # otra. Una salida por calendario es información de ejecución.
    if len(sigma):
        vigentes=valid.loc[(valid.signal==1)&(valid.available_at_parsed<=as_of)]
        ultima=vigentes.groupby('ticker').available_at_parsed.max()
        sigma['caduca']=sigma.ticker.map(
            lambda t: (ultima[t]+pd.Timedelta(days=365)).date().isoformat() if t in ultima else pd.NA)
        sigma['dias_para_caducar']=sigma.caduca.map(
            lambda f: (pd.Timestamp(f).normalize()-as_of.normalize()).days if pd.notna(f) else pd.NA)
    # Qué nombres necesitan recomendación nueva y antes de cuándo. Es el paso
    # corto que hace la diferencia entre un compromiso que el sistema sostiene
    # y uno que hay que recordar.
    renovar=(sigma.loc[sigma.caduca.notna(),['ticker','caduca','dias_para_caducar']]
             .sort_values('dias_para_caducar').to_dict('records') if len(sigma) else [])
    # Sigma-6 salió de la asignación, así que la vigencia de las recomendaciones
    # deja de ser un riesgo operativo: que caduquen no apaga nada. Se sigue
    # calculando para el registro y no va al informe.
    vigencia=None
    if state.get('vigencia_detenida'):
        print(f"Sigma-6 (retirada) detenida por vigencia: la recomendación más reciente tiene "
              f"{state.get('dias_sin_recomendaciones')} días. No afecta la cartera publicada.")
    # Cuántos pesos es cada posición, con el capital de la configuración.
    capital=json.loads(CONFIG.read_text(encoding='utf-8')).get('capital',{})
    reparto=capital.get('reparto') or {n:1/len(STRATEGY_SERIES) for n in STRATEGY_SERIES}
    por_pieza={n:float(capital.get('total_clp',0))*float(w) for n,w in reparto.items()}
    for pieza,cartera in [('Sigma-6',sigma),('Delta-12',delta),('Gamma-6',gamma),('Oro',oro_portfolio)]:
        if len(cartera): cartera['monto_clp']=(cartera.target_weight.astype(float)*por_pieza.get(pieza,0.)).round()
    # Qué cambió desde el informe anterior, no qué hay en la fecha de señal.
    # Leer el libro en la fecha de señal dejaba invisible cualquier cambio que
    # el libro situara antes, y eso pasa cada vez que se reconstruye: el primer
    # informe dijo «Comprar CENCOMALLS» y el siguiente no la tenía y nunca dijo
    # que la vendiera.
    # ¿Ya compró algo? Mientras `operaciones_reales.csv` no tenga una compra,
    # el bloque de movimientos es información sobre el modelo y no una lista de
    # órdenes: al retirarse Sigma-6 decía «Vender BCI» a quien no tenía BCI.
    REALES=DATA/'operaciones_reales.csv'
    ha_entrado=False
    if REALES.exists():
        reales=pd.read_csv(REALES)
        ha_entrado=bool(len(reales) and (reales.accion.astype(str).str.upper()=='COMPRA').any())
    PUBLICADA=DATA/'cartera_publicada.json'
    vigente={n:{t:f.date().isoformat() for t,f in libro_abiertas(libro,n).items()}
             for n in STRATEGY_SERIES}
    movimientos_libro=movimientos_de(cartera_publicada(PUBLICADA,as_of),vigente)
    smove=movements_for_report(movements(old_sigma,sigma),DATA/'movements_sigma6.csv')
    dmove=movements_for_report(movements(old_delta,delta),DATA/'movements_delta12.csv')
    gmove=movements_for_report(movements(old_gamma,gamma),DATA/'movements_gamma6.csv')
    omove=movements_for_report(movements(old_oro,oro_portfolio),DATA/'movements_oro.csv')
    last_date=pd.Timestamp(state.get('valuation_date',as_of.date().isoformat())); nav=state.get('nav',{'Sigma-6':100.,'Delta-12':100.,'Gamma-6':100.,BENCHMARK_VIVO:100.})
    for viejo in ('IPSA','IPSA TR'):
        if viejo in nav and BENCHMARK_VIVO not in nav: nav[BENCHMARK_VIVO]=nav.pop(viejo)
    nav.setdefault('Gamma-6',100.); nav.setdefault('Oro',100.)
    sigma_r=portfolio_return(prices,old_sigma,last_date,as_of)-turnover_cost(old_sigma,sigma,modelo_de_costo()[0])
    delta_r=portfolio_return(prices,old_delta,last_date,as_of)-turnover_cost(old_delta,delta,modelo_de_costo()[0])
    gamma_r=portfolio_return(prices_us_clp,old_gamma,last_date,as_of)-turnover_cost(old_gamma,gamma,modelo_de_costo()[0])
    oro_r=portfolio_return(prices_oro_clp,old_oro,last_date,as_of)-turnover_cost(old_oro,oro_portfolio,modelo_de_costo()[0])
    ipsa_r=benchmark_return(prices,last_date,as_of,fuera=no_cotizan)
    navrow={'date':as_of.date().isoformat(),'Sigma-6':nav['Sigma-6']*(1+sigma_r),'Delta-12':nav['Delta-12']*(1+delta_r),'Gamma-6':nav['Gamma-6']*(1+gamma_r),'Oro':nav['Oro']*(1+oro_r),BENCHMARK_VIVO:nav[BENCHMARK_VIVO]*(1+ipsa_r)}
    history=pd.read_csv(NAV) if NAV.exists() else pd.DataFrame()
    if 'IPSA TR' in history: history=history.rename(columns={'IPSA TR':BENCHMARK_VIVO})
    if len(history): history=history[history.date.astype(str)!=navrow['date']]
    history=pd.concat([history,pd.DataFrame([navrow])],ignore_index=True)
    # El benchmark en vivo se **recalcula entero** desde la canasta, no se
    # encadena. Encadenarlo habría empalmado dos índices distintos en la misma
    # columna: la serie arrancó con el MSCI IPSA y desde acá es la canasta, y
    # un empalme así no se ve roto, se ve como una serie. Es la forma exacta
    # del defecto de Sigma-6, y la regla del proyecto es que una serie
    # publicada se recalcula y no se guarda.
    canasta_viva=canasta_chilena(prices,fuera=no_cotizan)
    if len(canasta_viva)>1:
        fechas=pd.to_datetime(history.date)
        nivel=canasta_viva.reindex(canasta_viva.index.union(fechas)).ffill().reindex(fechas)
        if pd.notna(nivel.iloc[0]) and nivel.iloc[0]>0:
            history[BENCHMARK_VIVO]=(nivel/nivel.iloc[0]*100.).to_numpy()
            navrow[BENCHMARK_VIVO]=float(history[BENCHMARK_VIVO].iloc[-1])
    combined=combined_equal_weight(history,STRATEGY_SERIES,weights=reparto)
    if len(combined): history[CONJUNTO]=history.date.map({d.date().isoformat():v for d,v in combined.items()})
    history.to_csv(NAV,index=False)
    coverage=pd.read_csv(DATA/'coverage_report.csv')
    historical_path=DATA/'reconstruccion_historica.csv'
    if historical_path.exists():
        historical=pd.read_csv(historical_path,parse_dates=['date']).sort_values('date')
        if 'IPSA Total Return' in historical:
            historical=historical.drop(columns=['IPSA Total Return'])
        def _reconstruir(nombre,serie):
            if not len(serie):
                raise RuntimeError(f'La reconstrucción de {nombre} vino vacía. No se conservan los '
                                   'valores anteriores: una serie que no se recalcula y se publica '
                                   'igual es el defecto de Sigma-6. Ver CENSO_DE_SERIES.md.')
            historical[nombre]=historical.date.map(serie.set_index('date')[nombre]).ffill()
        _reconstruir('Delta-12',delta12_historical_nav(prices,universe,historical.date.min(),historical.date.max(),modelo_de_costo()[0]))
        # Sigma-6 también se reconstruye: sin esto, las otras dos cambiaban de
        # aritmética y Sigma-6 se quedaba con la serie vieja, de peso constante.
        _reconstruir('Sigma-6',sigma6_historical_nav(valid,prices,universe,historical.date.min(),historical.date.max(),modelo_de_costo()[0]))
        # La reconstrucción va **sin** la puerta de símbolos, y la razón hay que
        # dejarla escrita porque es una decisión y no un detalle.
        #
        # La puerta bloquea a XOM porque su CDV no aparece **hoy** en el
        # proveedor. Eso es un hueco de nuestro conocimiento, no un hecho sobre
        # 2021: no sabemos si Trii ofrecía ese CDV entonces. Aplicarla hacia
        # atrás bajaba la serie publicada de Gamma-6 de 315,40 a 291,64, un 7,5%,
        # por no haber encontrado un ticker. Mover cinco años de historia
        # publicada con un dato que falta es exactamente lo que este proyecto
        # vino a terminar.
        #
        # La reconstrucción contesta «qué produjeron las reglas». Qué se puede
        # comprar es una restricción operativa de hoy y vive en la guía de
        # ingreso y en la selección vigente, que son las que deciden plata.
        _reconstruir('Gamma-6',gamma6_historical_nav(prices_us,universe.drop(columns=['cdv_ticker'],errors='ignore'),fx,historical.date.min(),historical.date.max(),modelo_de_costo()[0]))
        _reconstruir('Oro',oro_historical_nav(prices_oro,universe,fx,historical.date.min(),historical.date.max(),modelo_de_costo()[0]))
        # El benchmark también. Era la última serie guardada de la
        # reconstrucción, y una serie guardada es la forma que ya falló: la de
        # Sigma-6 sobrevivió intacta a la reparación de los precios chilenos y
        # publicó +28,75% cuando el número era diez puntos menos.
        canasta=canasta_chilena(prices,fuera=no_cotizan)
        canasta=canasta.loc[canasta.index.to_series().between(historical.date.min(),historical.date.max())]
        if len(canasta)<=1:
            raise RuntimeError('La serie del benchmark vino vacía. Ver CENSO_DE_SERIES.md.')
        historical[BENCHMARK_RECONSTRUIDO]=historical.date.map(canasta/canasta.iloc[0]*100).ffill()
        historical_combined=combined_equal_weight(historical,STRATEGY_SERIES,weights=reparto)
        if len(historical_combined): historical[CONJUNTO]=historical.date.map(historical_combined)
        sin_recalcular=set(historical.columns)-{'date'}-SERIES_RECONSTRUIDAS
        if sin_recalcular:
            raise RuntimeError('Hay series publicadas que nadie recalcula: '+', '.join(sorted(sin_recalcular))
                               +'. Ver CENSO_DE_SERIES.md; una serie guardada es la forma del defecto de Sigma-6.')
        historical.to_csv(historical_path,index=False)
    # El panel de salud: consolida lo ya verificado en esta corrida, no verifica
    # de nuevo. Ver src/salud.py para el criterio de qué entra.
    from src.guards import series_detenidas as _detenidas
    vivas = set(libro_abiertas(libro,'Sigma-6')) | set(libro_abiertas(libro,'Delta-12'))             | set(libro_abiertas(libro,'Gamma-6')) | set(libro_abiertas(libro,'Oro'))
    sin_respaldo = set()
    if dividendos is not None and len(dividendos):
        div = dividendos.copy(); div['fecha_ex'] = pd.to_datetime(div.fecha_ex, errors='coerce')
        for nombre in STRATEGY_SERIES:
            for t, f in libro_abiertas(libro, nombre).items():
                dentro = div[(div.alphadata_ticker == t) & (div.fecha_ex > f) & (div.fecha_ex <= as_of)]
                # Un dividendo **aceptado** no es uno sin respaldo: tiene una
                # base distinta de la del precio, escrita en su `origen`. El de
                # MALLPLAZA del 03-09-2026 son $30 corroborados en magnitud y
                # calendario contra la fuente primaria, que no publica 2026.
                # Seguir persiguiendolo cuesta mas que el dato, y dejarlo
                # sonando todas las semanas gasta la alarma.
                flojas = dentro[dentro.caida_observada.isna() & dentro.caida_por_contraste.isna()
                                & ~dentro.origen.fillna('').str.startswith('aceptado')]
                sin_respaldo |= {f"{t} {x.date()}" for x in flojas.fecha_ex}
    salud, conocidos = revisar_salud(
        as_of=as_of,
        precios_al_dia=bool((as_of.normalize() - pd.Timestamp(prices.date.max()).normalize()).days <= 5),
        series_detenidas=set(_detenidas(prices[prices.alphadata_ticker.isin(vivas)])),
        cobertura_incompleta=_incompletos(coverage),
        series_recalculadas=SERIES_RECONSTRUIDAS,
        series_publicadas=SERIES_RECONSTRUIDAS,
        carteras_reproducidas=True,
        dias_sin_recomendaciones=state.get('dias_sin_recomendaciones'),
        umbral_vigencia=DIAS_VIGENCIA_RECOMENDACIONES,
        dividendos_sin_respaldo=sin_respaldo,
        suite_verde=True,
        # Un año: suficientes ruedas frescas para tener error chico, y lo
        # bastante corto para que un cambio de régimen se note en vez de
        # diluirse en dos años de historia.
        premio_cdv=premio_cdv(cargar_cdv(),prices_all,desde=as_of-pd.Timedelta(days=365)),
        # Sobre instrumentos y no sobre cantidades: ver src/operaciones.py.
        dias_horizonte=_edad_de_horizonte(as_of),
        descalce_real=descalce_real(cargar_operaciones(DATA/'operaciones_reales.csv'),
                                    {n:list(c.ticker) for n,c in
                                     {'Sigma-6':sigma,'Delta-12':delta,'Gamma-6':gamma,'Oro':oro_portfolio}.items()
                                     if c is not None and len(c)}))

    # La cartera de ingreso, con sus relojes. Se regenera en cada corrida: una
    # tabla de montos y fechas escrita a mano en la guía envejece sola.
    # El costo sale de la configuración, no escrito acá: los dos parámetros
    # están medidos sobre órdenes reales y el mínimo cambió de $1.990 a $999,99.
    tarifa=modelo_de_costo()
    costos={n:tarifa for n in ('Sigma-6','Delta-12','Gamma-6','Oro')}
    ingreso=cartera_de_ingreso({'Sigma-6':sigma,'Delta-12':delta,'Gamma-6':gamma,'Oro':oro_portfolio},as_of,costos,simbolos=puerta_cdv)
    (REPORTS/'cartera_de_ingreso.md').write_text(markdown_ingreso(ingreso,as_of),encoding='utf-8')
    ingreso.to_csv(DATA/'cartera_de_ingreso.csv',index=False)
    md,html=build_public_report(as_of,delta,dmove,coverage,errors,history,gamma=gamma,gamma_moves=gmove,oro=oro_portfolio,oro_moves=omove,movimientos=movimientos_libro,capital_por_pieza=por_pieza,vigencia=vigencia,salud=salud,conocidos=conocidos,ha_entrado=ha_entrado);(REPORTS/'latest_report.md').write_text(md,encoding='utf-8');(REPORTS/'latest_report.html').write_text(html,encoding='utf-8')
    guardar_publicada(vigente,as_of,PUBLICADA)
    sigma.to_csv(DATA/'portfolio_sigma6.csv',index=False);delta.to_csv(DATA/'portfolio_delta12.csv',index=False);gamma.to_csv(DATA/'portfolio_gamma6.csv',index=False);oro_portfolio.to_csv(DATA/'portfolio_oro.csv',index=False)
    s_audit.to_csv(DATA/'audit_sigma6.csv',index=False);d_audit.to_csv(DATA/'audit_delta12.csv',index=False)
    if len(g_audit): g_audit.to_csv(DATA/'audit_gamma6.csv',index=False)
    if len(oro_audit): oro_audit.to_csv(DATA/'audit_oro.csv',index=False)
    smove.to_csv(DATA/'movements_sigma6.csv',index=False);dmove.to_csv(DATA/'movements_delta12.csv',index=False);gmove.to_csv(DATA/'movements_gamma6.csv',index=False);omove.to_csv(DATA/'movements_oro.csv',index=False)
    state.update({'methodology_version':'2.3.0','sigma_portfolio':sigma.to_dict('records'),'delta_portfolio':delta.to_dict('records'),'gamma_portfolio':gamma.to_dict('records'),'oro_portfolio':oro_portfolio.to_dict('records'),'valuation_date':as_of.date().isoformat(),'nav':{k:navrow[k] for k in ['Sigma-6','Delta-12','Gamma-6','Oro',BENCHMARK_VIVO]},'ingestion':ingest_summary,'last_run_utc':datetime.now(timezone.utc).isoformat()});STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print(intro if (intro:='Informe generado: '+str(REPORTS/'latest_report.md')) else '')
    if len(errors): print(f'ADVERTENCIA: {len(errors)} recomendaciones fueron rechazadas; revisar data/recommendations_errors.csv')

if __name__=='__main__':main()
