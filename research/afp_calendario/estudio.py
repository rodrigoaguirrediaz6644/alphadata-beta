"""El privilegio del calendario: las mismas reglas, leidas en otro dia del mes.

Una regla mensual lee el cierre de mes. Pero el fin de mes no tiene nada de
especial para el mercado: es una fecha saliente para nosotros, no para los
precios. **Si la proteccion de la regla depende de leer justo ese dia, no es
una regla: es una coincidencia de calendario.**

La prueba: correr las doce reglas de `research/afp_desde_cero/` leyendo la
senal 0, 7, 14 y 21 dias corridos despues del cierre de mes. Mismo rezago de
ejecucion real -7 dias corridos- en las cuatro.

Investigacion pura: no toca produccion ni el informe.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

SP = Path("C:/Users/rodri/AppData/Local/Temp/claude/D--AlphaData/"
          "cda509b5-f3b1-4cc0-aadb-cdfdcf860f6d/scratchpad/afp")

# El cambio de fondo se materializa 4 dias habiles contados desde el dia habil
# siguiente a la solicitud. Son 7 dias corridos, no 3. Mis estudios mensuales
# anteriores usaron 3 y eso los favorecia.
REZAGO_REAL = 7

# Los cortes que se prueban: cierre de mes y tres semanas despues.
CORTES = (0, 7, 14, 21)

# La ventana de evaluacion comun a todos los estudios de esta serie.
DESDE = "2014-01-01"

# El proveedor entrega precios imposibles del dolar -5,46 el 10-04-2014-. Sin
# esta guardia la sigma del mercado sale 180% diaria.
MINIMO_CLP_POR_USD = 300


def cuotas(afp="cuprum"):
    v = (pd.read_csv(SP / f"vc_{afp}.csv", parse_dates=["date"])
         .set_index("date").sort_index()[["A", "E"]].dropna())
    return v[v.index >= "2002-08-01"]


def mercado(t):
    h = yf.Ticker(t).history(start="2003-01-01", auto_adjust=False)["Close"]
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return h[h >= MINIMO_CLP_POR_USD] if "CLP" in t else h


def cagr(s):
    anos = (s.index[-1] - s.index[0]).days / 365.25
    return (1 + s).prod() ** (1 / anos) - 1


def caida(s):
    nav = (1 + s).cumprod()
    return float((nav / nav.cummax() - 1).min())


def pct(x):
    return f"{x:+.2%}".replace(".", ",")


def senales(v, mclp, dia_corte):
    """Las doce reglas, leyendo el cierre `dia_corte` dias despues del fin de mes."""
    fechas = [f + pd.Timedelta(days=dia_corte) for f in v.resample("ME").last().index]
    fechas = [v.index[i] for i in (v.index.searchsorted(f) for f in fechas) if i < len(v)]
    a = v.A.reindex(fechas)
    m = mclp.reindex(pd.Index(fechas)).ffill()
    vol = (v.A.pct_change().rolling(60).std() * np.sqrt(252)).reindex(fechas)

    s = {}
    for n in (3, 6, 9, 12):
        s[f"propia-{n}m"] = a > a.rolling(n).mean()
        s[f"mercado-{n}m"] = m > m.rolling(n).mean()
    for p in (70, 80, 90, 95):
        s[f"vol-p{p}"] = vol < vol.expanding(24).quantile(p / 100)
    return s


def correr(v, senal, rezago=REZAGO_REAL):
    pos = pd.Series(index=v.index, dtype=object)
    for fecha, en_a in senal.dropna().items():
        i = v.index.searchsorted(fecha + pd.Timedelta(days=rezago))
        if i < len(v):
            pos.iloc[i] = "A" if en_a else "E"
    pos = pos.ffill().dropna()
    r = v.pct_change().fillna(0).loc[pos.index]
    return pd.Series(np.where(pos.eq("A"), r.A, r.E), index=pos.index)


def main():
    v = cuotas()
    mundo, fx = mercado("^990100-USD-STRD"), mercado("USDCLP=X")
    mclp = (mundo * fx.reindex(mundo.index).ffill()).dropna()

    print("#" * 78)
    print("# EL PRIVILEGIO DEL CALENDARIO")
    print("#" * 78)
    print("  Las mismas doce reglas, leidas en otro dia del mes.")
    print(f"  Rezago de ejecucion real: {REZAGO_REAL} dias corridos, igual en las cuatro.")
    print(f"  Ventana: {DESDE} en adelante, Cuprum.\n")

    print(f"  {'regla':14}" + "".join(f"{f'+{k}d':>20}" for k in CORTES))
    print(f"  {'':14}" + "".join(f"{'anual':>10}{'caida':>10}" for _ in CORTES))

    todos = {k: senales(v, mclp, k) for k in CORTES}
    peor, mejor = {}, {}
    for nombre in todos[0]:
        fila = []
        for k in CORTES:
            s = correr(v, todos[k][nombre]).loc[DESDE:]
            fila.append((cagr(s), caida(s)))
        # Cuidado con el signo: las caidas son negativas, asi que la lectura
        # MENOS protectora es el minimo y la mas protectora es el maximo. Lo
        # tuve al reves en la primera corrida y el resumen salio invertido.
        peor[nombre] = min(c for _, c in fila)
        mejor[nombre] = max(c for _, c in fila)
        print(f"  {nombre:14}" + "".join(f"{pct(a):>10}{pct(c):>10}" for a, c in fila))

    fa = v.A.pct_change().dropna().loc[DESDE:]
    ref = caida(fa)
    print(f"  {'Fondo A':14}" + "".join(f"{pct(cagr(fa)):>10}{pct(ref):>10}" for _ in CORTES))

    # Una regla "protege" si su caida es al menos 5 puntos mejor que el Fondo A.
    # Comparar caidas negativas directamente invita al error de signo -lo tuve
    # mal dos veces-, asi que se mide la VENTAJA en puntos, donde mas es mejor.
    VENTAJA_MINIMA = .05
    def protege(c):
        return c - ref >= VENTAJA_MINIMA

    algun = [n for n, c in mejor.items() if protege(c)]     # en su mejor dia de lectura
    cuatro = [n for n, c in peor.items() if protege(c)]     # en los cuatro
    print(f"\n  Caida del Fondo A en la ventana: {pct(ref)}")
    print(f"  Protege = caida al menos {VENTAJA_MINIMA:.0%} mejor que esa.\n")
    print(f"  No protegen en NINGUN dia de corte: {len(peor) - len(algun)} de {len(peor)}")
    print(f"  Protegen en algun dia de corte:     {len(algun)} de {len(peor)}")
    for n in algun:
        print(f"    - {n:12} mejor {pct(mejor[n])}   peor {pct(peor[n])}")
    print(f"  Protegen en LOS CUATRO dias:        {len(cuatro)} de {len(peor)}")
    print("\n  Esa ultima fila es la prueba. Una regla que protege solo si se")
    print("  lee el cierre de mes no es una regla: es el calendario.")


if __name__ == "__main__":
    main()
