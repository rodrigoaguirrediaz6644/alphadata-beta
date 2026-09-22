"""La norma del proyecto, hecha prueba. Ver UN_VALOR_UNA_CASA.md.

Cuatro defectos caros resultaron ser el mismo: un valor con mas de una casa, y
una copia que se quedo atras mientras el original cambiaba. Ninguno fue un
calculo malo y los cuatro duraron meses o anios porque **nada los contrastaba
contra su fuente**.

Lo que se prueba aca no es que los numeros sean correctos. Es que **no haya
donde escribir un segundo numero**.
"""

import ast
import inspect
import json
import re
from pathlib import Path

import pytest

from src import strategy_engine
from src.run_pipeline import modelo_de_costo

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config" / "runtime.v2.json"


# Un parametro se considera constante del dominio si su nombre dice que lleva
# plata: una tarifa, un minimo, una comision. Son justo los valores que algo
# fuera del repositorio puede desmentir, que es el criterio de la norma.
PLATA = ("cost", "costo", "tasa", "rate", "minimo", "minimum", "fee", "comision", "tarifa")

# La excepcion, escrita y no silenciosa: `minimo_exactos` es cuanta
# coincidencia se le exige a una fuente candidata de precios. Es un umbral que
# elegimos, no un dato del mundo, asi que ninguna boleta puede desmentirlo.
EXCEPCIONES = {("feed_validation.py", "aprueba", "minimo_exactos")}


def test_ninguna_constante_del_dominio_tiene_valor_por_omision():
    """Un valor por omision es exactamente una segunda casa.

    Es una copia silenciosa que **solo se delata cuando falta la primera**.
    Cuatro funciones traian la tarifa por omision y una traia el 0,1% de los
    CDV que una boleta desmintio; produccion las llamaba explicitamente, asi
    que el error estaba dormido esperando al proximo que llamara sin el
    argumento. Quitarlas hizo que la corrida fallara al instante en dos sitios
    que venian usandolas sin que nadie lo supiera.

    La regla: **si el parametro no llega, la llamada falla.**
    """
    culpables = []
    for f in sorted((RAIZ / "src").glob("*.py")):
        arbol = ast.parse(f.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            a = nodo.args
            params = a.posonlyargs + a.args + a.kwonlyargs
            faltan = len(a.posonlyargs) + len(a.args) - len(a.defaults)
            omisiones = [None] * faltan + list(a.defaults) + list(a.kw_defaults)
            for par, omision in zip(params, omisiones):
                if omision is None or not any(k in par.arg.lower() for k in PLATA):
                    continue
                if (f.name, nodo.name, par.arg) in EXCEPCIONES:
                    continue
                culpables.append(f"{f.name}:{nodo.lineno} {nodo.name}({par.arg}=...)")
    assert not culpables, "constantes del dominio con valor por omision:\n" + "\n".join(culpables)


def test_las_reconstrucciones_exigen_la_tarifa():
    """El caso concreto que costo la corrida caida, por si la regla se ablanda."""
    for nombre in ["delta12_historical_nav", "gamma6_historical_nav",
                   "oro_historical_nav", "sigma6_historical_nav"]:
        p = inspect.signature(getattr(strategy_engine, nombre)).parameters["cost_rate"]
        assert p.default is inspect.Parameter.empty, f"{nombre} trae la tarifa por omision"


def test_la_tarifa_no_esta_escrita_en_el_codigo_de_produccion():
    """Si alguien inventa un numero en el medio, esto falla.

    El 0,1785% y el $999,99 tienen una sola casa: config/runtime.v2.json. El
    unico lugar de `src/` donde pueden aparecer escritos es un comentario que
    cuente la historia.
    """
    patron = re.compile(r"0\.001785|\b999\.99\b|\b1990\b|\b\.001785\b")
    culpables = []
    for f in sorted((RAIZ / "src").glob("*.py")):
        for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            codigo = linea.split("#")[0]
            if patron.search(codigo):
                culpables.append(f"{f.name}:{n}: {linea.strip()}")
    assert not culpables, "la tarifa tiene una segunda casa:\n" + "\n".join(culpables)


def test_la_configuracion_no_guarda_numeros_derivados():
    """El umbral es minimo/tasa: no tiene casa propia, se calcula.

    Estuvo escrito como constante **y** guardado en la configuracion. Cambiar
    el minimo y olvidar el umbral lo dejaba mintiendo, que es exactamente la
    forma del defecto.
    """
    from src.ingreso import umbral_minimo
    modelo = json.loads(CONFIG.read_text(encoding="utf-8"))["transaction_cost"]
    assert not [k for k in modelo if "umbral" in k], "la configuracion guarda un derivado"
    tasa, minimo = modelo_de_costo()
    assert umbral_minimo(tasa, minimo) == pytest.approx(560_218, abs=1)


def test_el_simbolo_del_cdv_vive_en_una_columna_y_no_dentro_del_nombre():
    """El mapa de simbolos duro dos anios equivocado porque no era un dato.

    Se deducia pegando un sufijo al ticker, y cuando un ticker es prefijo de
    otro la regla devuelve un instrumento real y equivocado: BA + CL da BACL,
    que es Boeing.
    """
    import pandas as pd
    u = pd.read_csv(RAIZ / "config" / "tickers.csv")
    assert "cdv_ticker" in u.columns
    us = u.loc[u.tipo.isin({"accion_us", "etf_us"})]
    assert len(us) > 20
    # BACL es Boeing; el CDV de Bank of America es BACCL.
    assert us.loc[us.alphadata_ticker == "BAC", "cdv_ticker"].iloc[0] == "BACCL"
    # Y lo que no se encontro queda vacio, no adivinado.
    assert us.cdv_ticker.fillna("").eq("").sum() >= 1
