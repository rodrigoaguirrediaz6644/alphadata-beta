"""El relleno reescribe historia oficial. Estas pruebas cubren lo que no debe hacer.

Es un comando de una sola vez y fuera del flujo normal, así que el riesgo no es
que falle: es que escriba de más, que escriba sin validar, o que borre los
factores de dividendo al pasar por encima.
"""

import pandas as pd
import pytest

from src.referencia_investing import leer, ticker_de
from tools.rellenar_hueco import VALIDAR_DESDE, planificar

FECHAS = pd.bdate_range("2025-01-02", periods=300)


def _archivo(tmp_path, nombre, cierres, en_espanol=False):
    ruta = tmp_path / nombre
    if en_espanol:
        cabecera = '"Fecha","Último","Apertura","Máximo","Mínimo","Vol.","% var."'
        filas = [f'"{f:%d.%m.%Y}","{("%,.2f" % c).replace(",", "X").replace(".", ",").replace("X", ".")}","0,00","0,00","0,00","1,50K","0%"'
                 for f, c in zip(FECHAS, cierres)]
    else:
        cabecera = '"Date","Price","Open","High","Low","Vol.","Change %"'
        filas = [f'"{f:%m/%d/%Y}","{c:,.2f}","0.00","0.00","0.00","1.50K","0%"' for f, c in zip(FECHAS, cierres)]
    ruta.write_text("\n".join([cabecera, *reversed(filas)]) + "\n", encoding="utf-8-sig")
    return ruta


def _guardado(cierres, factor=1.0, ticker="BCI"):
    return pd.DataFrame({
        "date": FECHAS, "alphadata_ticker": ticker, "yahoo_ticker": f"{ticker}.SN",
        "open": cierres, "high": cierres, "low": cierres,
        "close": cierres, "adjusted_close": [c * factor for c in cierres], "volume": 1000.0,
    })


def test_lee_los_dos_formatos_de_investing():
    # El inglés y el español difieren en fecha, miles y decimal. Y el nombre del
    # archivo es la única fuente del ticker en el formato español.
    assert ticker_de("Datos históricos de Cap (CAP).csv") == "CAP"
    assert ticker_de("Salfacorp Stock Price History.csv") == "SALFACORP"
    assert ticker_de("Datos históricos de Multiexport Fo (MULTIX).csv") == "MULTIFOODS"


def test_el_volumen_con_sufijo_se_convierte(tmp_path):
    ruta = _archivo(tmp_path, "X.csv", [100.0] * len(FECHAS))
    assert leer(ruta).volume.iloc[0] == pytest.approx(1500.0)


def test_solo_se_escriben_las_ruedas_que_discrepan(tmp_path):
    cierres = [100.0 + i for i in range(len(FECHAS))]
    guardado = _guardado(cierres)
    rotos = list(cierres)
    rotos[200:210] = [rotos[199]] * 10  # diez ruedas congeladas
    guardado.loc[200:209, ["close", "adjusted_close"]] = rotos[199]
    ruta = _archivo(tmp_path, "Banco de Credito e Inversiones Stock Price History.csv", cierres)
    ticker, plan, informe = planificar(ruta, guardado, {"BCI"})
    assert ticker == "BCI" and informe["motivo"] == "validado"
    assert len(plan) == 10 and set(plan.accion) == {"sobrescribe"}


def test_un_archivo_con_otra_convencion_de_cierre_se_rechaza(tmp_path):
    # Una serie ajustada por dividendos tiene la misma forma pero otro nivel.
    # Es el caso SALFACORP fuera de la ventana validada.
    cierres = [100.0 + i for i in range(len(FECHAS))]
    ruta = _archivo(tmp_path, "Banco de Credito e Inversiones Stock Price History.csv",
                    [c * .92 for c in cierres])
    ticker, plan, informe = planificar(ruta, _guardado(cierres), {"BCI"})
    assert ticker is None and plan.empty
    assert "no pasa la validación" in informe["motivo"]


def test_no_se_escribe_nada_anterior_a_la_ventana_validada(tmp_path):
    cierres = [100.0 + i for i in range(len(FECHAS))]
    guardado = _guardado(cierres)
    guardado.loc[0:5, "close"] = 1.0  # rotas, pero anteriores a la ventana
    ruta = _archivo(tmp_path, "Banco de Credito e Inversiones Stock Price History.csv", cierres)
    _, plan, _ = planificar(ruta, guardado, {"BCI"})
    assert plan.empty or (plan.date >= VALIDAR_DESDE).all()


def test_el_factor_de_dividendo_se_conserva_al_sobrescribir(tmp_path):
    # Las estrategias corren sobre adjusted_close. Escribir el cierre crudo en
    # esa columna borraría los dividendos: en 2025-2026 el factor llega a 0,85.
    cierres = [100.0 + i for i in range(len(FECHAS))]
    guardado = _guardado(cierres, factor=.9)
    guardado.loc[200:209, ["close", "adjusted_close"]] = [999.0, 899.1]
    ruta = _archivo(tmp_path, "Banco de Credito e Inversiones Stock Price History.csv", cierres)
    _, plan, _ = planificar(ruta, guardado, {"BCI"})
    assert len(plan) == 10
    fila = plan.iloc[0]
    assert fila.adjusted_close == pytest.approx(fila.close * .9)


def test_un_instrumento_sin_serie_guardada_no_se_escribe(tmp_path):
    ruta = _archivo(tmp_path, "Banco de Credito e Inversiones Stock Price History.csv",
                    [100.0] * len(FECHAS))
    ticker, plan, informe = planificar(ruta, _guardado([100.0] * len(FECHAS), ticker="OTRO"), {"BCI"})
    assert ticker is None and "no hay serie guardada" in informe["motivo"]
