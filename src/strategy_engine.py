from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json, re, unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.nav_historico import nav_corrido

BROKERS = ["Credicorp Capital"]
BROKER_KEYS = {"credicorpcapital": "Credicorp Capital", "credicorp": "Credicorp Capital"}
SIGNALS = {
    "comprar": 1, "compra": 1, "sobreponderar": 1, "outperform": 1, "superior al mercado": 1,
    "mantener": 0, "neutral": 0, "market perform": 0, "igual al mercado": 0,
    "vender": -1, "venta": -1, "subponderar": -1, "underperform": -1, "inferior al mercado": -1,
}
# Cencosud Shopping se renombró Cenco Malls. Las recomendaciones históricas de
# Credicorp vienen bajo el nombre viejo y son de la misma empresa: sin este
# alias, veintidós señales reales quedaban rechazadas como "fuera del catálogo"
# y Sigma-6 perdía un instrumento que sí puede operar.
ALIAS_TICKERS = {"CENCOSHOPP": "CENCOMALLS"}
RECOMMENDATION_COLUMNS = ["published_at", "available_at", "broker", "ticker", "recommendation", "target_price_min", "target_price_max", "currency", "source_url", "notes"]


class Sigma6DataQualityError(RuntimeError):
    """Impide convertir indicadores ausentes en órdenes económicas."""



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
        broker = normalize_broker(row["broker"]); signal = normalize_signal(row["recommendation"]); ticker = str(row["ticker"]).strip().upper(); ticker = ALIAS_TICKERS.get(ticker, ticker)
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


# Guardia de vigencia de las recomendaciones. Si en una revision la mas reciente
# tiene mas de noventa dias, Sigma-6 conserva la cartera, no abre nada y el
# informe lo dice. **No vende**: es la misma regla que para los precios, porque
# una venta disparada por la ausencia del insumo no es una senal, es un hueco.
#
# El argumento es que un mes saltado tiene que ser ruidoso y no silencioso. Todo
# lo que este proyecto reparo en septiembre de 2026 fue algo que dejo de
# actualizarse sin avisar: el feed chileno, las fechas de entrada, el grafico
# publicado, la serie de Sigma-6.
#
# El umbral de 90 dias no es arbitrario ni ajustado: en 2021-2026 el hueco mas
# largo entre recomendaciones fue de 29 dias, asi que la guardia nunca se
# habria activado y no cambia ninguna serie publicada. Separa el ritmo normal
# de una carga que dejo de ocurrir.
DIAS_VIGENCIA_RECOMENDACIONES=90


def recomendaciones_vencidas(valid: pd.DataFrame, as_of: pd.Timestamp,
                             dias: int = DIAS_VIGENCIA_RECOMENDACIONES) -> int | None:
    """Cuantos dias lleva la recomendacion mas reciente. None si no hay ninguna."""
    if valid.empty: return None
    disponibles=valid.loc[valid.available_at_parsed<=as_of,"available_at_parsed"]
    if disponibles.empty: return None
    return int((pd.Timestamp(as_of).normalize()-disponibles.max().normalize()).days)


def _sostiene_el_precio(ticker, momentum, sma200, ultimo, exigir_sma200: bool) -> bool:
    """Si las condiciones de precio siguen sosteniendo una posicion ya abierta.

    Se usa cuando la guardia de vigencia esta activa: las recomendaciones no
    llegan, pero los precios si, y un insumo fresco si puede quitar riesgo.
    """
    mom=momentum.get(ticker,np.nan) if len(momentum) else np.nan
    if pd.isna(mom) or mom<=0: return False
    if not exigir_sma200: return True
    referencia,precio=sma200.get(ticker,np.nan) if len(sma200) else np.nan, ultimo.get(ticker,np.nan) if len(ultimo) else np.nan
    return bool(pd.notna(referencia) and pd.notna(precio) and precio>referencia)


def sigma6(valid: pd.DataFrame, prices: pd.DataFrame, as_of: pd.Timestamp, previous: dict[str, Any], exigir_sma200: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Sigma-6: recomendacion de Credicorp vigente mas momentum 12-1 positivo.

    `exigir_sma200` es la condicion `adjusted_close > sma200`, la misma que
    Delta-12 y Gamma-6 ya usan. Entro el 21-09-2026 porque Sigma-6 era la unica
    estrategia accionaria sin ninguna salida que mirara el precio de hoy: el
    momentum 12-1 salta las ultimas 21 ruedas, asi que una caida del ultimo mes
    le era invisible.

    El argumento que mas pesa no es el del backtest --donde el retorno se da
    vuelta entre submuestras y por lo tanto no se distingue-- sino que tapa un
    hueco estructural con una condicion que el sistema ya usa en dos de tres
    piezas. La caida si mejora de forma consistente. Ver
    `research/sma200_sigma6/`.

    El parametro sigue existiendo para poder medir con y sin.
    """
    if valid.empty:
        active=pd.DataFrame(columns=["ticker","broker_normalized","signal","available_at_parsed"])
    else:
        cutoff=as_of-pd.Timedelta(days=365)
        active=valid[(valid.available_at_parsed<=as_of)&(valid.available_at_parsed>=cutoff)].sort_values(["available_at_parsed","row_number"]).drop_duplicates(["ticker","broker_normalized"],keep="last")
    close=prices.loc[prices.date<=as_of].pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index()
    # Los calendarios bursátiles no coinciden. Una fila global puede existir por un
    # ADR aunque Chile no haya transado; completar sólo hasta tres ruedas evita
    # que ese desfase transforme posiciones válidas en ventas.
    close=close.ffill(limit=3)
    momentum=(close.shift(21).iloc[-1]/close.shift(252).iloc[-1]-1) if len(close)>=252 else pd.Series(dtype=float)
    sma200=close.rolling(200,min_periods=200).mean().iloc[-1] if len(close)>=200 else pd.Series(dtype=float)
    ultimo=close.iloc[-1] if len(close) else pd.Series(dtype=float)
    audit=[]
    for ticker,g in active.groupby("ticker"):
        signal=int(g.iloc[-1].signal); mom=float(momentum.get(ticker,np.nan))
        sobre=(not exigir_sma200) or (pd.notna(sma200.get(ticker,np.nan)) and pd.notna(ultimo.get(ticker,np.nan)) and ultimo.get(ticker)>sma200.get(ticker))
        audit.append({"ticker":ticker,"credicorp_signal":signal,"momentum_12_1":mom,"sma200":float(sma200.get(ticker,np.nan)) if len(sma200) else np.nan,"history_rows":int(close[ticker].notna().sum()) if ticker in close else 0,"latest_signal_at":g.available_at_parsed.max(),"eligible":bool(signal==1 and pd.notna(mom) and mom>0 and sobre)})
    scores=pd.DataFrame(audit)
    positive=scores.loc[scores.credicorp_signal==1] if len(scores) else scores
    missing_positive=set(positive.loc[positive.momentum_12_1.isna(),"ticker"]) if len(positive) else set()
    held=set(previous.get("sigma_entries",{}))
    missing_held=missing_positive & held
    if missing_held:
        raise Sigma6DataQualityError(
            "Sigma-6 abortada: faltan indicadores para posiciones vigentes con señal positiva: "
            + ", ".join(sorted(missing_held))
        )
    if len(positive) and positive.momentum_12_1.isna().all():
        raise Sigma6DataQualityError(
            "Sigma-6 abortada: faltan todos los indicadores de momentum para las señales positivas"
        )
    candidates=scores[scores.eligible].set_index("ticker") if len(scores) else pd.DataFrame()
    # Sigma-6 no tiene tope de tenencia: rota por señal, no por calendario. El
    # de 365 días salió el 21-09-2026; ver data/archivo/cambio_aritmetica_nav.md.
    entries=previous.get("sigma_entries",{}); eligible={t:1.0 for t in candidates.index}
    antiguedad=recomendaciones_vencidas(valid,as_of)
    detenida=antiguedad is not None and antiguedad>DIAS_VIGENCIA_RECOMENDACIONES
    if detenida:
        # **Un insumo viejo no puede agregar riesgo, pero uno fresco sí puede
        # quitarlo.** Lo que falta son las recomendaciones; los precios siguen
        # llegando. Se suspende lo que depende del insumo ausente —que la
        # recomendación baje de nota, y su caducidad a los 365 días— y siguen
        # vivas la SMA200 y el momentum.
        #
        # No se abre nada: abrir sobre recomendaciones de tres meses es apostar
        # sobre información que ya no se confirma. Sí se cierra por precio:
        # suspender la SMA200 reabriría, justo en el periodo en que nadie está
        # mirando, el hueco que esa condición vino a tapar.
        #
        # La consecuencia es que durante una guardia larga la cartera sólo puede
        # encoger hacia caja. Es la dirección conservadora, y la regla de los dos
        # disparos trae la decisión de vuelta antes de que llegue lejos.
        eligible={t:1.0 for t in entries if _sostiene_el_precio(t,momentum,sma200,ultimo,exigir_sma200)}
    weights=capped_pro_rata(pd.Series(eligible,dtype=float),.10)
    portfolio=pd.DataFrame({"ticker":weights.index,"target_weight":weights.values}) if len(weights) else pd.DataFrame(columns=["ticker","target_weight"])
    old=set(entries); new=set(portfolio.ticker); new_entries={t:(entries[t] if t in entries else as_of.date().isoformat()) for t in new}
    state={**previous,"sigma_entries":new_entries,
           "vigencia_detenida":bool(detenida),"dias_sin_recomendaciones":antiguedad}
    return portfolio.sort_values("target_weight",ascending=False), scores.sort_values(["eligible","momentum_12_1"],ascending=[False,False]) if len(scores) else scores, state


def delta12(prices: pd.DataFrame, universe: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    local=set(universe.loc[universe.tipo=="accion_local","alphadata_ticker"])
    p=prices[prices.alphadata_ticker.isin(local)&(prices.date<=as_of)].copy()
    close=p.pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index().ffill(limit=3)
    volume=p.pivot(index="date",columns="alphadata_ticker",values="volume").sort_index()
    if len(close)<252: return pd.DataFrame(columns=["ticker","target_weight"]),pd.DataFrame(columns=["ticker","reason"])
    momentum=close.shift(21).iloc[-1]/close.shift(252).iloc[-1]-1
    sma=close.rolling(200,min_periods=200).mean().iloc[-1]; last=close.iloc[-1]
    delta=close.diff()
    gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rs=gain/loss.replace(0,np.nan)
    rsi14=(100-(100/(1+rs))).fillna(100).iloc[-1]
    turnover=(close*volume).rolling(60,min_periods=30).median().iloc[-1]; liquidity_pct=turnover.rank(pct=True)*100
    obs=close.notna().sum(); audit=pd.DataFrame({"ticker":close.columns,"adjusted_close":last,"momentum_12_1":momentum,"sma200":sma,"rsi14":rsi14,"liquidity_percentile":liquidity_pct,"history_rows":obs}).set_index("ticker")
    audit["eligible"]=(audit.momentum_12_1>0)&(audit.adjusted_close>audit.sma200)&(audit.rsi14<=65)&(audit.liquidity_percentile>=20)&(audit.history_rows>=252)
    audit["reason"]=np.select([audit.history_rows<252,audit.momentum_12_1<=0,audit.adjusted_close<=audit.sma200,audit.rsi14>65,audit.liquidity_percentile<20],["historia insuficiente","momentum no positivo","bajo SMA200","RSI14 superior a 65","liquidez inferior al percentil 20"],default="elegible")
    selected=audit[audit.eligible].nlargest(8,"momentum_12_1"); weights=capped_pro_rata(pd.Series(1.,index=selected.index),.15)
    portfolio=pd.DataFrame({"ticker":weights.index,"target_weight":weights.values}) if len(weights) else pd.DataFrame(columns=["ticker","target_weight"])
    return portfolio.sort_values("target_weight",ascending=False),audit.reset_index().sort_values(["eligible","momentum_12_1"],ascending=[False,False])



def gamma6(prices: pd.DataFrame, universe: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Gamma-6: momentum compuesto (3, 6-1 y 12-1 meses, pesos 2/1/1) sobre acciones de EE.UU.

    Contrato de estrategia: devuelve (portfolio[ticker,target_weight], audit).
    La señal se calcula sobre el precio ajustado en dólares; la conversión a
    pesos ocurre al valorizar la cartera, no al rankear (el tipo de cambio es
    un factor común y no altera el orden entre acciones).
    """
    us=set(universe.loc[universe.tipo=="accion_us","alphadata_ticker"])
    p=prices[prices.alphadata_ticker.isin(us)&(prices.date<=as_of)]
    close=p.pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index().ffill(limit=3)
    if len(close)<252: return pd.DataFrame(columns=["ticker","target_weight"]),pd.DataFrame(columns=["ticker","reason"])
    last=close.iloc[-1]; lag=lambda n: close.shift(n).iloc[-1]
    r3=last/lag(63)-1; r6=lag(21)/lag(126)-1; r12=lag(21)/lag(252)-1
    sma=close.rolling(200,min_periods=200).mean().iloc[-1]; obs=close.notna().sum()
    audit=pd.DataFrame({"ticker":close.columns,"adjusted_close":last,"retorno_3m":r3,"retorno_6_1":r6,"retorno_12_1":r12,"sma200":sma,"history_rows":obs}).set_index("ticker")
    audit["history_ok"]=audit.history_rows>=252; audit["sobre_sma200"]=audit.adjusted_close>audit.sma200
    base=audit[audit.history_ok].dropna(subset=["retorno_3m","retorno_6_1","retorno_12_1"])
    z=lambda x: (x-x.mean())/x.std() if len(x)>1 and x.std() else x*0.
    audit["score"]=(2*z(base.retorno_3m)+z(base.retorno_6_1)+z(base.retorno_12_1))/4 if len(base) else np.nan
    audit["eligible"]=audit.history_ok&audit.sobre_sma200&audit.score.notna()
    audit["reason"]=np.select([~audit.history_ok,audit.score.isna(),~audit.sobre_sma200],["historia insuficiente","indicadores incompletos","bajo SMA200"],default="elegible")
    selected=audit[audit.eligible].nlargest(6,"score"); weights=capped_pro_rata(pd.Series(1.,index=selected.index),1/6+1e-9)
    portfolio=pd.DataFrame({"ticker":weights.index,"target_weight":weights.values}) if len(weights) else pd.DataFrame(columns=["ticker","target_weight"])
    return portfolio.sort_values("target_weight",ascending=False),audit.reset_index().sort_values(["eligible","score"],ascending=[False,False])


def sanear_fx(rate: pd.Series, tolerancia: float = .25, ventana: int = 11) -> tuple[pd.Series, pd.Series]:
    """Descarta datos imposibles del tipo de cambio y devuelve (serie limpia, descartados).

    El proveedor publica de vez en cuando un dato roto: el 22-12-2016 entregó un
    cierre de 5 pesos por dólar con una apertura de 671. Multiplicado por un
    precio en dólares, un dato así hunde la serie en pesos un 99% y la recupera
    al día siguiente. Se compara cada valor con la mediana móvil centrada y lo
    que se aparta más de `tolerancia` se descarta, arrastrando el último valor
    bueno. El umbral es holgado: la mayor variación diaria real del dólar en la
    serie disponible es de 12%.
    """
    limpio=pd.to_numeric(rate,errors="coerce")
    referencia=limpio.rolling(ventana,center=True,min_periods=3).median()
    malos=((limpio/referencia-1).abs()>tolerancia)|(limpio<=0)
    return limpio.mask(malos).ffill().bfill(), limpio[malos]


ORO_TICKER="IAU"  # iShares Gold Trust; en Chile se transa como CDV IAUCL


def oro(prices: pd.DataFrame, universe: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Oro: posición fija, sin señal.

    No es una estrategia en el sentido de las otras tres: no predice nada ni
    rankea. Existe porque el oro fue el único activo del universo disponible que
    terminó positivo en las seis grandes caídas desde 2008, y porque un cuarto
    de la cartera en oro sube el Sharpe del conjunto y reduce casi a la mitad su
    peor retroceso. Se probó además filtrarlo por tendencia (SMA200, la misma
    regla de Gamma-6) y empeora el resultado en veinte años: el aporte viene de
    su correlación, no de acertarle a su dirección.

    Cumple el mismo contrato que las demás: devuelve (portfolio, audit).
    """
    disponible=set(universe.loc[universe.tipo=="etf_us","alphadata_ticker"])
    if ORO_TICKER not in disponible:
        return pd.DataFrame(columns=["ticker","target_weight"]),pd.DataFrame(columns=["ticker","reason"])
    serie=prices.loc[(prices.alphadata_ticker==ORO_TICKER)&(prices.date<=as_of),["date","adjusted_close"]].dropna()
    suficiente=len(serie)>=60
    audit=pd.DataFrame([{"ticker":ORO_TICKER,"history_rows":len(serie),"adjusted_close":float(serie.adjusted_close.iloc[-1]) if len(serie) else np.nan,
                         "eligible":bool(suficiente),"reason":"elegible" if suficiente else "historia insuficiente"}])
    portfolio=pd.DataFrame([{"ticker":ORO_TICKER,"target_weight":1.0}]) if suficiente else pd.DataFrame(columns=["ticker","target_weight"])
    return portfolio,audit


def oro_historical_nav(prices: pd.DataFrame, universe: pd.DataFrame, fx: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cost_rate: float = .001) -> pd.DataFrame:
    """Reconstruye la serie del oro en pesos: comprar una vez y mantener."""
    clp=to_clp(prices,universe,fx)
    serie=clp.loc[(clp.alphadata_ticker==ORO_TICKER)&clp.date.between(start,end),["date","adjusted_close"]].dropna().sort_values("date")
    if len(serie)<2: return pd.DataFrame(columns=["date","Oro"])
    nav=serie.adjusted_close/serie.adjusted_close.iloc[0]*100*(1-cost_rate)
    return pd.DataFrame({"date":serie.date.values,"Oro":nav.values})


def to_clp(prices: pd.DataFrame, universe: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """Convierte a pesos los precios de los instrumentos en dólares.

    `fx` son las filas del tipo de cambio (alphadata_ticker == "USDCLP"). Se
    arrastra el último valor conocido para los días en que Nueva York opera y
    el mercado cambiario local no publicó nuevo dato, y se descartan los datos
    imposibles antes de multiplicar.
    """
    rate=fx.set_index("date")["adjusted_close"].sort_index()
    if rate.empty: return prices.copy()
    rate,descartados=sanear_fx(rate)
    if len(descartados):
        print("ADVERTENCIA: se descartaron %d datos imposibles del tipo de cambio: %s" % (len(descartados), ", ".join(f"{d:%d-%m-%Y}={v:.2f}" for d,v in descartados.items())))
    usd=set(universe.loc[universe.moneda=="USD","alphadata_ticker"])
    out=prices.copy(); mask=out.alphadata_ticker.isin(usd)
    factor=rate.reindex(pd.DatetimeIndex(sorted(set(out.loc[mask,"date"])|set(rate.index)))).ffill()
    out.loc[mask,["open","high","low","close","adjusted_close"]]=out.loc[mask,["open","high","low","close","adjusted_close"]].mul(out.loc[mask,"date"].map(factor).to_numpy(),axis=0)
    return out


def gamma6_historical_nav(prices: pd.DataFrame, universe: pd.DataFrame, fx: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cost_rate: float = .001) -> pd.DataFrame:
    """Reconstruye Gamma-6 en pesos con los pesos corriendo. Ver delta12_historical_nav."""
    us=set(universe.loc[universe.tipo=="accion_us","alphadata_ticker"])
    clp=to_clp(prices,universe,fx)
    panel=clp.loc[clp.alphadata_ticker.isin(us)&clp.date.between(start-pd.Timedelta(days=700),end)].pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index().ffill(limit=3)
    sesiones=panel.index[panel.index>=pd.Timestamp(start)]
    return nav_corrido(panel,sesiones,"M",lambda f: dict(zip(*[gamma6(prices,universe,f)[0][c] for c in ("ticker","target_weight")])),cost_rate,"Gamma-6")


def delta12_historical_nav(prices: pd.DataFrame, universe: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cost_rate: float = .001785) -> pd.DataFrame:
    """Reconstruye Delta-12 con la política escrita: los pesos corren.

    Antes calculaba con el peso constante, que es la aritmética de una cartera
    rebalanceada a diario y gratis. Ver `src/nav_historico.py` y
    `POLITICA_REBALANCEO.md`.
    """
    local=set(universe.loc[universe.tipo=="accion_local","alphadata_ticker"])
    panel=prices.loc[prices.alphadata_ticker.isin(local)&prices.date.between(start-pd.Timedelta(days=400),end)].pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index().ffill(limit=3)
    sesiones=panel.index[panel.index>=pd.Timestamp(start)]
    return nav_corrido(panel,sesiones,"M",lambda f: dict(zip(*[delta12(prices,universe,f)[0][c] for c in ("ticker","target_weight")])),cost_rate,"Delta-12")


def sigma6_historical_nav(valid: pd.DataFrame, prices: pd.DataFrame, universe: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, cost_rate: float = .001785, exigir_sma200: bool = True) -> pd.DataFrame:
    """Reconstruye Sigma-6 semanal con los pesos corriendo.

    No existía: la serie de Sigma-6 venía congelada en
    `data/reconstruccion_historica.csv` desde antes del reinicio. Sin ella, las
    otras dos cambiaban de aritmética y Sigma-6 se quedaba con la vieja.
    """
    locales=set(universe.loc[universe.tipo.isin({"accion_local","accion_sigma"}),"alphadata_ticker"])
    panel=prices.loc[prices.alphadata_ticker.isin(locales)&prices.date.between(start-pd.Timedelta(days=400),end)].pivot(index="date",columns="alphadata_ticker",values="adjusted_close").sort_index().ffill(limit=3)
    sesiones=panel.index[panel.index>=pd.Timestamp(start)]
    estado={"sigma_entries":{}}
    def elegir(f):
        nonlocal estado
        cartera,_,estado=sigma6(valid,prices.loc[prices.date<=f],f,estado,exigir_sma200=exigir_sma200)
        return dict(zip(cartera.ticker,cartera.target_weight))
    return nav_corrido(panel,sesiones,"W-FRI",elegir,cost_rate,"Sigma-6")


def combined_equal_weight(frame: pd.DataFrame, columns: list[str], date_column: str = "date", freq: str = "M") -> pd.Series:
    """Serie del conjunto: la misma ponderación en cada estrategia.

    Se reparte el capital en partes iguales entre las estrategias disponibles en
    cada fecha y se reequilibra al cierre de cada mes; dentro del mes los pesos
    se dejan correr, igual que ocurriría en una cuenta real. Devuelve un índice
    base 100 indexado por fecha.
    """
    data=frame.copy(); data[date_column]=pd.to_datetime(data[date_column])
    present=[c for c in columns if c in data]
    if not present: return pd.Series(dtype=float)
    values=data.set_index(date_column)[present].apply(pd.to_numeric,errors="coerce").sort_index().ffill()
    values=values.dropna(how="all")
    if len(values)<2: return pd.Series(100.,index=values.index) if len(values) else pd.Series(dtype=float)
    nav=[]; level=100.; previous=None
    for _,block in values.groupby(values.index.to_period(freq)):
        if previous is not None: block=pd.concat([previous.to_frame().T,block])
        growth=block.divide(block.iloc[0])  # el mes arranca reequilibrado: las columnas sin dato quedan NaN y no entran al promedio
        period=growth.mean(axis=1)*level  # partes iguales entre las estrategias con dato
        nav.append(period.iloc[1:] if previous is not None else period)
        level=float(period.iloc[-1]); previous=block.iloc[-1]
    series=pd.concat(nav).sort_index()
    return series[~series.index.duplicated(keep="last")]


def movements(previous: list[dict[str, Any]], current: pd.DataFrame) -> pd.DataFrame:
    old={x["ticker"]:float(x["target_weight"]) for x in previous}; new=dict(zip(current.ticker,current.target_weight)); rows=[]
    for ticker in sorted(set(old)|set(new)):
        before=old.get(ticker,0.); after=new.get(ticker,0.); action="ENTRA" if before==0 and after>0 else "SALE" if before>0 and after==0 else "AUMENTA" if after>before+1e-9 else "REDUCE" if after<before-1e-9 else "MANTIENE"
        rows.append({"ticker":ticker,"action":action,"previous_weight":before,"target_weight":after,"change":after-before})
    return pd.DataFrame(rows)


def reconstruct_entry_dates(valid: pd.DataFrame, prices: pd.DataFrame, universe: pd.DataFrame, as_of: pd.Timestamp) -> tuple[dict[str, str], dict[str, str]]:
    """Rebuild the last uninterrupted entry date for every position still active.

    Entry dates come from each strategy's historical decision calendar, never
    from the date when prospective tracking happened to start.
    """
    sessions = pd.DatetimeIndex(sorted(prices.loc[(prices.alphadata_ticker != "IPSA_TR") & (prices.date <= as_of), "date"].dropna().unique()))
    if sessions.empty:
        return {}, {}

    def next_session(after: pd.Timestamp) -> pd.Timestamp:
        future = sessions[sessions > pd.Timestamp(after).normalize()]
        return future[0] if len(future) else pd.Timestamp(after).normalize()

    # Sigma-6: last session of every week, executed on the next market session.
    weekly = pd.Series(sessions, index=sessions).groupby(sessions.to_period("W-FRI")).max().tolist()
    sigma_state: dict[str, Any] = {"sigma_entries": {}}
    previous: set[str] = set()
    for review in weekly:
        if review < pd.Timestamp("2021-07-09"):
            continue
        portfolio, _, sigma_state = sigma6(valid, prices, pd.Timestamp(review), sigma_state)
        current = set(portfolio.ticker)
        execution = next_session(pd.Timestamp(review)).date().isoformat()
        for ticker in current - previous:
            sigma_state["sigma_entries"][ticker] = execution
        previous = current

    # Delta-12: month-end decision, executed on the first following session.
    delta_entries: dict[str, str] = {}
    previous = set()
    eligible_sessions = sessions[sessions.to_period("M") < as_of.to_period("M")]
    monthly = pd.Series(eligible_sessions, index=eligible_sessions).groupby(eligible_sessions.to_period("M")).max().tolist()
    for review in monthly:
        if review < pd.Timestamp("2021-07-01"):
            continue
        portfolio, _ = delta12(prices, universe, pd.Timestamp(review))
        current = set(portfolio.ticker)
        execution = next_session(pd.Timestamp(review)).date().isoformat()
        for ticker in current - previous:
            delta_entries[ticker] = execution
        for ticker in previous - current:
            delta_entries.pop(ticker, None)
        previous = current
    return sigma_state.get("sigma_entries", {}), delta_entries
