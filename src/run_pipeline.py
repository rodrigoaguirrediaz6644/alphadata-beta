from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from src.fetch_prices import load_universe
from src.ingest_recommendations import ingest
from src.strategy_registry import validate_registry
from src.reporting_public import build_public_report
from src.strategy_engine import RECOMMENDATION_COLUMNS, delta12, delta12_historical_nav, movements, reconstruct_entry_dates, sigma6, validate_recommendations

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; REPORTS=ROOT/'reports'; STATE=DATA/'strategy_state.json'

def load_state()->dict:
    if STATE.exists():
        state=json.loads(STATE.read_text(encoding='utf-8'))
        if state.get('methodology_version') in {'2.0.0','2.1.0'}: return state
    return {'methodology_version':'2.1.0','sigma_entries':{},'delta_entries':{},'sigma_portfolio':[],'delta_portfolio':[]}

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
    coverage=pd.read_csv(DATA/'coverage_report.csv')
    historical_path=DATA/'historical_model_nav.csv'
    if historical_path.exists():
        historical=pd.read_csv(historical_path,parse_dates=['date']).sort_values('date')
        rebuilt=delta12_historical_nav(prices,universe,historical.date.min(),historical.date.max())
        if len(rebuilt):
            values=rebuilt.set_index('date')['Delta-12']
            historical['Delta-12']=historical.date.map(values)
            historical.to_csv(historical_path,index=False)
    md,html=build_public_report(as_of,sigma,delta,smove,dmove,coverage,errors);(REPORTS/'latest_report.md').write_text(md,encoding='utf-8');(REPORTS/'latest_report.html').write_text(html,encoding='utf-8')
    sigma.to_csv(DATA/'portfolio_sigma6.csv',index=False);delta.to_csv(DATA/'portfolio_delta12.csv',index=False);s_audit.to_csv(DATA/'audit_sigma6.csv',index=False);d_audit.to_csv(DATA/'audit_delta12.csv',index=False);smove.to_csv(DATA/'movements_sigma6.csv',index=False);dmove.to_csv(DATA/'movements_delta12.csv',index=False)
    state.pop('valuation_date',None);state.pop('nav',None)
    state.update({'methodology_version':'2.1.0','sigma_portfolio':sigma.to_dict('records'),'delta_portfolio':delta.to_dict('records'),'ingestion':ingest_summary,'last_run_utc':datetime.now(timezone.utc).isoformat()});STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print(intro if (intro:='Informe generado: '+str(REPORTS/'latest_report.md')) else '')
    if len(errors): print(f'ADVERTENCIA: {len(errors)} recomendaciones fueron rechazadas; revisar data/recommendations_errors.csv')

if __name__=='__main__':main()
