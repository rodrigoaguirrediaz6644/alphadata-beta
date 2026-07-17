from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json, re, unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BROKERS = ["Credicorp Capital"]
BROKER_KEYS = {"credicorpcapital": "Credicorp Capital", "credicorp": "Credicorp Capital"}
SIGNALS = {
    "comprar": 1, "compra": 1, "sobreponderar": 1, "outperform": 1, "superior al mercado": 1,
    "mantener": 0, "neutral": 0, "market perform": 0, "igual al mercado": 0,
    "vender": -1, "venta": -1, "subponderar": -1, "underperform": -1, "inferior al mercado": -1,
}
RECOMMENDATION_COLUMNS = ["published_at", "available_at", "broker", "ticker", "recommendation", "target_price_min", "target_price_max", "currency", "source_url", "notes"]


def _key(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"[^a-z0-9]", "", value)


def normalize_broker(value: str) -> str | None:
    return BROKER_KEYS.get(_key(value))


def normalize_signal(value: str) -> int | None:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower().strip()
    text = re.sub(r"\s+", " ", text)
    return SIGNALS.get(text)


def validate_recommendations(raw: pd.DataFrame, allowed_tickers: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = set(RECOMMENDATION_COLUMNS).difference(raw.columns)
    if missing: raise ValueError(f"Faltan columnas en recommendations_input.csv: {sorted(missing)}")
    valid, errors = [], []
    for idx, row in raw.fillna("").iterrows():
        if not any(str(row[c]).strip() for c in RECOMMENDATION_COLUMNS): continue
        broker = normalize_broker(row["broker"]); signal = normalize_signal(row["recommendation"]); ticker = str(row["ticker"]).strip().upper()
        published = pd.to_datetime(row["published_at"], errors="coerce"); available = pd.to_datetime(row["available_at"], errors="coerce")
        reasons=[]
        if broker is None: reasons.append("corredora no permitida o mal escrita")
        if signal is None: reasons.append("recomendación sin acción reconocida")
        if ticker not in allowed_tickers: reasons.append("ticker fuera del catálogo")
        if pd.isna(published): reasons.append("fecha de publicación inválida")
        if pd.isna(available): available=published
        if pd.notna(published) and pd.notna(available) and available < published: reasons.append("available_at anterior a published_at")
        base={**row.to_dict(),"row_number":int(idx)+2,"ticker":ticker,"broker_normalized":broker,"signal":signal,"published_at_parsed":published,"available_at_parsed":available}
        if reasons: errors.append({**base,"errors":"; ".join(reasons)})
        else: valid.append(base)
    valid_columns=RECOMMENDATION_COLUMNS+["row_number","broker_normalized","signal","published_at_parsed","available_at_parsed"]
    error_columns=valid_columns+["errors"]
    return pd.DataFrame(valid,columns=valid_columns), pd.DataFrame(errors,columns=error_columns)


def capped_pro_rata(scores: pd.Series, cap: float) -> pd.Series:
    scores=pd.to_numeric(scores,errors="coerce").fillna(0).clip(lower=0); result=pd.Series(0.,index=scores.index); active=scores[scores>0].copy(); remaining=1.
    while len(active) and remaining>1e-12:
        proposal=remaining*active/active.sum(); hit=proposal>=cap-1e-12
        if not hit.any(): result.loc[proposal.index]+=proposal; break
        result.loc[proposal[hit].index]=cap; remaining=1-result.sum(); active=active[~hit]
    return result


def sigma6(valid: pd.DataFrame, prices: pd.DataFrame, as_of: pd.Timestamp, previous: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if valid.empty:
        active=pd.DataFrame(columns=["ticker","broker_normalized","signal","available_at_parsed"])
    else:
        cutoff=as_of-pd.Timedelta(days=365)
        active=valid[(valid.available_at_parsed<=as_of)&(valid.available_at_parsed>=cutoff)].sort_values(["available_at_parsed","row_number"]).drop_duplicates(["ticker","broker_normalized"],keep="last")
    close=prices.loc[prices.date<=as_of].pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index()
    momentum=(close.shift(21).iloc[-1]/close.shift(252).iloc[-1]-1) if len(close)>=252 else pd.Series(dtype=float)
    audit=[]
    for ticker,g in active.groupby("ticker"):
        signal=int(g.iloc[-1].signal); mom=float(momentum.get(ticker,np.nan))
        audit.append({"ticker":ticker,"credicorp_signal":signal,"momentum_12_1":mom,"history_rows":int(close[ticker].notna().sum()) if ticker in close else 0,"latest_signal_at":g.available_at_parsed.max(),"eligible":bool(signal==1 and pd.notna(mom) and mom>0)})
    scores=pd.DataFrame(audit)
    candidates=scores[scores.eligible].set_index("ticker") if len(scores) else pd.DataFrame()
    entries=previous.get("sigma_entries",{}); eligible={}
    if len(candidates):
        for ticker,row in candidates.iterrows():
            entered=pd.Timestamp(entries.get(ticker,as_of.date().isoformat()))
            if (as_of.normalize()-entered.normalize()).days>=365:
                continue
            eligible[ticker]=1.0
    weights=capped_pro_rata(pd.Series(eligible,dtype=float),.10)
    portfolio=pd.DataFrame({"ticker":weights.index,"target_weight":weights.values}) if len(weights) else pd.DataFrame(columns=["ticker","target_weight"])
    old=set(entries); new=set(portfolio.ticker); new_entries={t:(entries[t] if t in entries else as_of.date().isoformat()) for t in new}
    state={**previous,"sigma_entries":new_entries}
    return portfolio.sort_values("target_weight",ascending=False), scores.sort_values(["eligible","momentum_12_1"],ascending=[False,False]) if len(scores) else scores, state


def delta12(prices: pd.DataFrame, universe: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    local=set(universe.loc[universe.tipo=="accion_local","alphadata_ticker"])
    p=prices[prices.alphadata_ticker.isin(local)&(prices.date<=as_of)].copy()
    close=p.pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index().ffill(limit=3)
    volume=p.pivot(index="date",columns="alphadata_ticker",values="volume").sort_index()
    if len(close)<252: return pd.DataFrame(columns=["ticker","target_weight"]),pd.DataFrame(columns=["ticker","reason"])
    momentum=close.shift(21).iloc[-1]/close.shift(252).iloc[-1]-1
    sma=close.rolling(200,min_periods=200).mean().iloc[-1]; last=close.iloc[-1]
    turnover=(close*volume).rolling(60,min_periods=30).median().iloc[-1]; liquidity_pct=turnover.rank(pct=True)*100
    obs=close.notna().sum(); audit=pd.DataFrame({"ticker":close.columns,"adjusted_close":last,"momentum_12_1":momentum,"sma200":sma,"liquidity_percentile":liquidity_pct,"history_rows":obs}).set_index("ticker")
    audit["eligible"]=(audit.momentum_12_1>0)&(audit.adjusted_close>audit.sma200)&(audit.liquidity_percentile>=20)&(audit.history_rows>=252)
    audit["reason"]=np.select([audit.history_rows<252,audit.momentum_12_1<=0,audit.adjusted_close<=audit.sma200,audit.liquidity_percentile<20],["historia insuficiente","momentum no positivo","bajo SMA200","liquidez inferior al percentil 20"],default="elegible")
    selected=audit[audit.eligible].nlargest(8,"momentum_12_1"); weights=capped_pro_rata(pd.Series(1.,index=selected.index),.15)
    portfolio=pd.DataFrame({"ticker":weights.index,"target_weight":weights.values}) if len(weights) else pd.DataFrame(columns=["ticker","target_weight"])
    return portfolio.sort_values("target_weight",ascending=False),audit.reset_index().sort_values(["eligible","momentum_12_1"],ascending=[False,False])


def movements(previous: list[dict[str, Any]], current: pd.DataFrame) -> pd.DataFrame:
    old={x["ticker"]:float(x["target_weight"]) for x in previous}; new=dict(zip(current.ticker,current.target_weight)); rows=[]
    for ticker in sorted(set(old)|set(new)):
        before=old.get(ticker,0.); after=new.get(ticker,0.); action="ENTRA" if before==0 and after>0 else "SALE" if before>0 and after==0 else "AUMENTA" if after>before+1e-9 else "REDUCE" if after<before-1e-9 else "MANTIENE"
        rows.append({"ticker":ticker,"action":action,"previous_weight":before,"target_weight":after,"change":after-before})
    return pd.DataFrame(rows)
