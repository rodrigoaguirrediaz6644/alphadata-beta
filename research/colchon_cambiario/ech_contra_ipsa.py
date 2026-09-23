"""Las dos corridas cortas que deciden si hay algo que rehacer.

**Primera: la comparacion anterior estaba mal hecha.** Comparo ECH sobre 11
episodios de 2007-2026 contra IPSA sobre 5 episodios de 2015-2026, y de ahi
deduje que la contaminacion empujaba en contra. Son dos poblaciones distintas
de episodios, y lo que las distingue no es aleatorio: los dos fracasos mas
profundos -2011 y 2007-08- quedan fuera de la ventana del IPSA por
construccion. **El «5 de 5» excluia los dos casos que ya sabiamos que
fallaban.** Es el mismo defecto de ventana que ya encontramos cinco veces.

Aca va ECH restringido a la ventana del IPSA, que es la unica comparacion que
contesta la pregunta.

**Segunda: si el seguimiento malo es horario y no mercado.** ECH cotiza en Nueva
York y el IPSA cierra en Santiago; el retorno «del mismo dia» de los dos no
cubre el mismo tramo de tiempo. Se comprueba corriendo un dia en cada
direccion. Es la misma forma del hallazgo del valor cuota de las AFP, que iba
un dia atras del mercado.

Investigacion pura: no toca produccion.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from estudio import MINIMO_CLP_POR_USD, caida, cagr, episodios, pct

AQUI = Path(__file__).parent
ROOT = AQUI.parents[1]
CONFIG = ROOT / "config" / "runtime.v2.json"

# Dos versiones del IPSA, y las dos se usan: la archivada cubre 2015-2026 pero
# **quedo congelada el 17-07-2026** con el incidente del feed chileno, y la viva
# arranca en 2021 pero llega hasta hoy. Ninguna sola alcanza, y coincidir en las
# dos es mejor prueba que coincidir en una.
ARCHIVADA = ROOT / "data" / "archivo" / "ipsa_tr_proxy_cfmitnipsa.csv"
FIN_ARCHIVADA = "2026-07-17"
VIVA = ROOT / "data" / "market_prices_daily.csv"


def serie(t, ajustado=True):
    h = yf.Ticker(t).history(start="2007-01-01", auto_adjust=ajustado)["Close"].dropna()
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return h[h >= MINIMO_CLP_POR_USD] if "CLP" in t else h


def ipsa_archivada():
    s = (pd.read_csv(ARCHIVADA, parse_dates=["date"]).set_index("date")
         .sort_index().adjusted_close)
    return s.loc[:FIN_ARCHIVADA]


def ipsa_viva():
    d = pd.read_csv(VIVA, parse_dates=["date"])
    return (d[d.alphadata_ticker == "IPSA_TR"].set_index("date")
            .sort_index().adjusted_close)


# --------------------------------------------------------------------------
# PRIMERA: la misma ventana para las dos series
# --------------------------------------------------------------------------

def primera():
    fx, ech = serie("USDCLP=X", ajustado=False), serie("ECH")
    ipsa = ipsa_archivada()
    mundo, oro = serie("^990100-USD-STRD"), serie("GC=F")
    # **Dos indices, y confundirlos fue el defecto.** `idx_ech` no incluye al
    # IPSA, asi que llega a 2007; `idx_comun` si, y por eso empieza en 2015 y
    # termina en el congelamiento. En la primera version arme un solo indice
    # con el IPSA adentro y despues rotule una de las filas como «2007-2026»:
    # las dos filas eran la misma ventana y la etiqueta mentia.
    idx_ech = fx.index
    for s in (ech, mundo, oro):
        idx_ech = idx_ech.intersection(s.index)
    idx_comun = idx_ech.intersection(ipsa.index)

    reparto = json.loads(CONFIG.read_text(encoding="utf-8"))["capital"]["reparto"]
    w = (float(reparto["Delta-12"]), float(reparto["Gamma-6"]), float(reparto["Oro"]))

    print("#" * 78)
    print("# PRIMERA — ECH y el IPSA sobre la MISMA ventana")
    print("#" * 78)
    print("  La tabla anterior comparaba ECH en 2007-2026 contra IPSA en 2015-2026.")
    print("  Los dos fracasos mas profundos quedaban fuera por construccion.\n")

    for etiqueta, base, desde, hasta in (
            ("2007-11 a 2026-09, solo ECH", idx_ech, "2007-11-21", "2026-12-31"),
            ("2015-01 a 2026-07, ventana comun", idx_comun, "2015-01-02", FIN_ARCHIVADA)):
        k = base[(base >= desde) & (base <= hasta)]
        # Sin la columna del IPSA cuando no corresponde: dejarla con NaN
        # cambiaba el `dropna` y con el un dia de la ventana, y con ese dia el
        # conteo de episodios dejaba de calzar con la tabla publicada.
        cols = {
            "fx": fx.reindex(k).pct_change(),
            "mundo_usd": mundo.reindex(k).pct_change(),
            "oro_usd": oro.reindex(k).pct_change(),
            "ech": (ech * fx).reindex(k).pct_change(),
        }
        hay_ipsa = base is idx_comun
        if hay_ipsa:
            cols["ipsa"] = ipsa.reindex(k).pct_change()
        r = pd.DataFrame(cols).dropna()
        r["mundo_clp"] = (1 + r.mundo_usd) * (1 + r.fx) - 1
        r["oro_clp"] = (1 + r.oro_usd) * (1 + r.fx) - 1
        print(f"  --- {etiqueta}, {len(r)} dias")
        print(f"      {'serie':10} {'episodios':>10} {'peso sube':>11} "
              f"{'benef. mediano':>15} {'fracasos':>10} {'caida con':>11} {'caida sin':>11}")
        for nombre, col in (("ECH x FX", "ech"), ("IPSA", "ipsa")):
            if col == "ipsa" and not hay_ipsa:
                continue                        # la archivada no llega a esa ventana
            con = w[0] * r[col] + w[1] * r.mundo_clp + w[2] * r.oro_clp
            sin = w[0] * r[col] + w[1] * r.mundo_usd + w[2] * r.oro_usd
            ep = episodios((1 + r[col]).cumprod())
            ben = [float((1 + con.loc[a:b]).prod()) - float((1 + sin.loc[a:b]).prod())
                   for a, b in ep]
            sube = sum(int(float((1 + r.fx.loc[a:b]).prod() - 1) > 0) for a, b in ep)
            print(f"      {nombre:10} {len(ep):>10} {str(sube) + ' de ' + str(len(ep)):>11} "
                  f"{pct(np.median(ben)) if ben else '   —  ':>15} "
                  f"{str(sum(1 for x in ben if x < 0)) + ' de ' + str(len(ben)):>10} "
                  f"{pct(caida(con)):>11} {pct(caida(sin)):>11}")
        print()


# --------------------------------------------------------------------------
# SEGUNDA: el desfase horario
# --------------------------------------------------------------------------

def segunda():
    fx, ech = serie("USDCLP=X", ajustado=False), serie("ECH")
    print("#" * 78)
    print("# SEGUNDA — el seguimiento malo, ¿es horario o es mercado?")
    print("#" * 78)
    print("  ECH cierra en Nueva York y el IPSA en Santiago. Si el retorno «del")
    print("  mismo dia» no cubre el mismo tramo, un corrimiento de un dia lo arregla.\n")

    for etiqueta, ipsa in (("archivada 2015-2026", ipsa_archivada()),
                           ("viva 2021-2026", ipsa_viva())):
        k = fx.index.intersection(ech.index).intersection(ipsa.index)
        a = (ech * fx).reindex(k).pct_change()
        b = ipsa.reindex(k).pct_change()
        j = pd.concat({"ech": a, "ipsa": b}, axis=1).dropna()
        print(f"  --- IPSA {etiqueta}, {len(j)} dias "
              f"({j.index.min().date()} a {j.index.max().date()})")
        print(f"      {'alineacion':28} {'correlacion':>12} {'error segu.':>13}")
        for nombre, desp in (("ECH(t) contra IPSA(t-1)", 1),
                             ("ECH(t) contra IPSA(t)   ", 0),
                             ("ECH(t) contra IPSA(t+1) ", -1)):
            otro = j.ipsa.shift(desp)
            m = pd.concat([j.ech, otro], axis=1).dropna()
            te = (m.iloc[:, 0] - m.iloc[:, 1]).std() * 252 ** .5
            print(f"      {nombre:28} {m.iloc[:, 0].corr(m.iloc[:, 1]):>+12.3f} "
                  f"{te:>12.1%}")
        print()


if __name__ == "__main__":
    primera()
    segunda()
