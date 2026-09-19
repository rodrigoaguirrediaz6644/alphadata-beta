from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import sys

import pandas as pd

from src.fetch_prices import load_universe
from src.ingest_recommendations import ingest
from src.strategy_registry import validate_registry
from src.reporting_public import build_public_report
from src.strategy_engine import RECOMMENDATION_COLUMNS, delta12, delta12_historical_nav, movements, reconstruct_entry_dates, sigma6, validate_recommendations

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; REPORTS=ROOT/'reports'; STATE=DATA/'strategy_state.json'; NAV=DATA/'strategy_nav.csv'

def load_state()->dict:
    if STATE.exists():
        state=json.loads(STATE.read_text(encoding='utf-8'))
        if state.get('methodology_version') in {'2.0.0','2.1.0'}: return state
    return {'methodology_version':'2.1.0','sigma_entries':{},'delta_entries':{},'sigma_portfolio':[],'delta_portfolio':[],'nav':{'Sigma-6':100.,'Delta-12':100.,'IPSA TR':100.}}

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

def enrich_open_positions(portfolio: pd.DataFrame, prices: pd.DataFrame, as_of: pd.Timestamp, buy_cost: float = .001785) -> pd.DataFrame:
    """Add entry/current prices and unrealized return for every open position."""
    result = portfolio.copy()
    for column in ["entry_price", "current_price", "open_return"]:
        result[column] = pd.NA
    for index, row in result.iterrows():
        opened_at = pd.to_datetime(row.get("opened_at"), errors="coerce")
        series = prices.loc[
            (prices.alphadata_ticker == row["ticker"]) & (prices.date <= as_of),
            ["date", "adjusted_close"],
        ].dropna().sort_values("date")
        if pd.isna(opened_at) or series.empty:
            continue
        entry = series.loc[series.date >= opened_at].head(1)
        if entry.empty:
            entry = series.loc[series.date <= opened_at].tail(1)
        current = series.tail(1)
        if entry.empty or current.empty or float(entry.adjusted_close.iloc[0]) <= 0:
            continue
        entry_price = float(entry.adjusted_close.iloc[0])
        current_price = float(current.adjusted_close.iloc[0])
        result.at[index, "opened_at"] = entry.date.iloc[0].date().isoformat()
        result.at[index, "entry_price"] = entry_price
        result.at[index, "current_price"] = current_price
        result.at[index, "open_return"] = current_price / (entry_price * (1 + buy_cost)) - 1
    return result


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


def benchmark_return(prices,start,end)->float:
    ipsa=prices[prices.alphadata_ticker=='IPSA_TR'].sort_values('date')
    if len(ipsa):
        a=ipsa[ipsa.date<=start].tail(1);z=ipsa[ipsa.date<=end].tail(1)
        if len(a) and len(z):return float(z.adjusted_close.iloc[0]/a.adjusted_close.iloc[0]-1)
    local=prices[~prices.alphadata_ticker.isin(['IPSA_TR','LTM-ADR','SQM-ADR'])].pivot(index='date',columns='alphadata_ticker',values='adjusted_close').sort_index().ffill(limit=3)
    a=local.loc[:start].tail(1);z=local.loc[:end].tail(1)
    if a.empty or z.empty:return 0.
    return float((z.iloc[0]/a.iloc[0]-1).dropna().mean())

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
           f'En esta ejecución se detectaron {len(errors)} filas de recomendaciones con observaciones y {int((coverage.status!="OK").sum())} instrumentos con cobertura incompleta.')
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
| IPSA TR proxy ETF | {navrow['IPSA TR']:.2f} |

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
- Instrumentos con precios suficientes: {int((coverage.status=='OK').sum())}/{len(coverage)}.
- Fecha más reciente de precios: {as_of:%d-%m-%Y}.

## Metodología

Sigma-6 exige una recomendación positiva vigente de Credicorp Capital y momentum 12-1 positivo; pondera en partes iguales con máximo 10% y revisa semanalmente. Delta-12 selecciona mensualmente hasta ocho acciones con momentum 12-1 positivo, precio sobre SMA200 y liquidez sobre el percentil 20; asigna pesos iguales con máximo 15%. Ambas aplican 0,1785% al monto transado.

## Advertencia

Resultados de carteras modelo para evaluación interna. No constituyen asesoría personalizada ni garantizan rentabilidades futuras. La rentabilidad personal de un suscriptor depende de su fecha y precio efectivo de entrada.
"""
    html=f"""<!doctype html><html lang='es'><head><meta charset='utf-8'><style>
    body{{font:16px Arial;max-width:1000px;margin:36px auto;color:#17324d;line-height:1.45}}table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}th,td{{border:1px solid #ccd6df;padding:8px;text-align:left}}th{{background:#147d78;color:white}}h1,h2{{color:#12304a}}.note{{background:#fff4cc;padding:14px}}
    </style></head><body><h1>Informe automático AlphaData</h1><p><strong>Fecha de corte:</strong> {as_of:%d-%m-%Y}<br><strong>Metodología:</strong> Sigma-6 v2.0.0 y Delta-12 v2.0.0</p>
    <h2>Resumen</h2><p>{escape(intro)}</p><table><tr><th>Serie</th><th>Índice acumulado</th></tr><tr><td>Sigma-6</td><td>{navrow['Sigma-6']:.2f}</td></tr><tr><td>Delta-12</td><td>{navrow['Delta-12']:.2f}</td></tr><tr><td>IPSA TR proxy ETF</td><td>{navrow['IPSA TR']:.2f}</td></tr></table>
    <h2>Sigma-6</h2>{html_table(sigma,['ticker','target_weight'])}<p><strong>Caja:</strong> {pct(sigma_cash)}</p><h3>Movimientos</h3>{html_table(smove,['ticker','action','previous_weight','target_weight','change'])}
    <h2>Delta-12</h2>{html_table(delta,['ticker','target_weight'])}<p><strong>Caja:</strong> {pct(delta_cash)}. Se modifica sólo una vez por mes.</p><h3>Movimientos</h3>{html_table(dmove,['ticker','action','previous_weight','target_weight','change'])}
    <h2>Calidad de datos</h2><ul><li>Filas rechazadas: {len(errors)}</li><li>Instrumentos con cobertura suficiente: {int((coverage.status=='OK').sum())}/{len(coverage)}</li><li>Último precio: {as_of:%d-%m-%Y}</li></ul>
    <h2>Metodología</h2><p>Sigma-6 combina recomendación positiva de Credicorp con momentum 12-1 positivo. Delta-12 selecciona mensualmente hasta ocho acciones mediante momentum 12-1, SMA200 y liquidez. Costo: 0,1785% del monto transado.</p><p class='note'><strong>Advertencia:</strong> carteras modelo para evaluación interna; no constituyen asesoría personalizada ni garantizan rentabilidades futuras.</p></body></html>"""
    return md,html

def main()->None:
    validate_registry()
    REPORTS.mkdir(parents=True,exist_ok=True); DATA.mkdir(parents=True,exist_ok=True)
    ingest_summary=ingest()
    universe=load_universe(); prices=pd.read_csv(DATA/'market_prices_daily.csv',parse_dates=['date'])
    prices.loc[prices.alphadata_ticker=='IPSA','alphadata_ticker']='IPSA_TR'
    as_of=prices.loc[prices.alphadata_ticker!='IPSA_TR','date'].max().normalize(); state=load_state()
    input_path=DATA/'recommendations_input.csv'; raw=pd.read_csv(input_path,dtype=str).fillna('') if input_path.exists() else pd.DataFrame(columns=RECOMMENDATION_COLUMNS)
    valid,errors=validate_recommendations(raw,set(universe.alphadata_ticker)); valid.to_csv(DATA/'recommendations_validated_live.csv',index=False,date_format='%Y-%m-%d');errors.to_csv(DATA/'recommendations_errors.csv',index=False,date_format='%Y-%m-%d')
    old_sigma=state.get('sigma_portfolio',[]); old_delta=state.get('delta_portfolio',[])
    if state.get('entry_dates_version') != 3:
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
    sigma=enrich_open_positions(sigma,prices,as_of)
    delta=enrich_open_positions(delta,prices,as_of)
    smove=movements_for_report(movements(old_sigma,sigma),DATA/'movements_sigma6.csv')
    dmove=movements_for_report(movements(old_delta,delta),DATA/'movements_delta12.csv')
    last_date=pd.Timestamp(state.get('valuation_date',as_of.date().isoformat())); nav=state.get('nav',{'Sigma-6':100.,'Delta-12':100.,'IPSA TR':100.})
    if 'IPSA' in nav and 'IPSA TR' not in nav: nav['IPSA TR']=nav.pop('IPSA')
    sigma_r=portfolio_return(prices,old_sigma,last_date,as_of)-turnover_cost(old_sigma,sigma,.001785)
    delta_r=portfolio_return(prices,old_delta,last_date,as_of)-turnover_cost(old_delta,delta,.001785)
    ipsa_r=benchmark_return(prices,last_date,as_of)
    navrow={'date':as_of.date().isoformat(),'Sigma-6':nav['Sigma-6']*(1+sigma_r),'Delta-12':nav['Delta-12']*(1+delta_r),'IPSA TR':nav['IPSA TR']*(1+ipsa_r)}
    history=pd.read_csv(NAV) if NAV.exists() else pd.DataFrame()
    if len(history): history=history[history.date.astype(str)!=navrow['date']]
    history=pd.concat([history,pd.DataFrame([navrow])],ignore_index=True);history.to_csv(NAV,index=False)
    coverage=pd.read_csv(DATA/'coverage_report.csv')
    historical_path=DATA/'historical_model_nav.csv'
    if historical_path.exists():
        historical=pd.read_csv(historical_path,parse_dates=['date']).sort_values('date')
        rebuilt=delta12_historical_nav(prices,universe,historical.date.min(),historical.date.max())
        if len(rebuilt):
            values=rebuilt.set_index('date')['Delta-12']
            historical['Delta-12']=historical.date.map(values)
            historical.to_csv(historical_path,index=False)
    md,html=build_public_report(as_of,sigma,delta,smove,dmove,coverage,errors,history);(REPORTS/'latest_report.md').write_text(md,encoding='utf-8');(REPORTS/'latest_report.html').write_text(html,encoding='utf-8')
    sigma.to_csv(DATA/'portfolio_sigma6.csv',index=False);delta.to_csv(DATA/'portfolio_delta12.csv',index=False);s_audit.to_csv(DATA/'audit_sigma6.csv',index=False);d_audit.to_csv(DATA/'audit_delta12.csv',index=False);smove.to_csv(DATA/'movements_sigma6.csv',index=False);dmove.to_csv(DATA/'movements_delta12.csv',index=False)
    state.update({'methodology_version':'2.1.0','sigma_portfolio':sigma.to_dict('records'),'delta_portfolio':delta.to_dict('records'),'valuation_date':as_of.date().isoformat(),'nav':{k:navrow[k] for k in ['Sigma-6','Delta-12','IPSA TR']},'ingestion':ingest_summary,'last_run_utc':datetime.now(timezone.utc).isoformat()});STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print(intro if (intro:='Informe generado: '+str(REPORTS/'latest_report.md')) else '')
    if len(errors): print(f'ADVERTENCIA: {len(errors)} recomendaciones fueron rechazadas; revisar data/recommendations_errors.csv')

if __name__=='__main__':main()
