"""La tabla de dividendos y el cierre ajustado derivado.

El riesgo aquí es fechar mal un dividendo: el ajustado es la columna sobre la
que corren el momentum 12-1, la SMA200 y el RSI, así que un factor en la fecha
equivocada no distorsiona un gráfico, cambia la cartera que la estrategia
elige.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dividendos import (CONFIRMADA, POR_CONVENCION, aplicar_ajuste, confirmada_por_precio, derivar_ajustado,
                            detectar_nuevos, factores, localizar_fecha_ex, tolerancia_de)

ROOT = Path(__file__).resolve().parents[1]
DIAS = pd.bdate_range("2026-01-05", periods=80)


def _serie_con_dividendo(monto=5.0, indice_ex=40, ruido=0.0):
    """Una serie que sube suave y cae el monto del dividendo en la fecha ex."""
    valores = np.linspace(100, 120, len(DIAS))
    serie = pd.Series(valores, index=DIAS)
    serie.iloc[indice_ex:] = serie.iloc[indice_ex:] - monto
    if ruido:
        serie.iloc[indice_ex] += ruido * serie.iloc[indice_ex - 1]
    return serie


def test_encuentra_la_fecha_ex_aunque_el_proveedor_declare_otra():
    # El proveedor declara una fecha cinco ruedas después de la caída real: es
    # lo que hace con los .SN, medido sobre 113 dividendos.
    serie = _serie_con_dividendo(monto=5.0, indice_ex=40)
    declarada = DIAS[45]
    calce = localizar_fecha_ex(serie, declarada, 5.0)
    assert calce is not None and not calce["rechazado"]
    assert calce["fecha_ex"] == DIAS[40]


def test_un_dividendo_que_ningun_dia_explica_queda_rechazado():
    serie = pd.Series(np.linspace(100, 120, len(DIAS)), index=DIAS)  # sin caída
    calce = localizar_fecha_ex(serie, DIAS[45], 15.0)
    assert calce is None or calce["rechazado"]


def test_la_tolerancia_escala_con_el_ruido_del_instrumento():
    # Un papel tranquilo exige un calce más estrecho que uno volátil, porque lo
    # que sobra tras quitar el dividendo es el movimiento del día.
    tranquilo = pd.Series(np.linspace(100, 101, 200), index=pd.bdate_range("2026-01-05", periods=200))
    volatil = pd.Series(100 * np.cumprod(1 + np.tile([.03, -.03], 100)),
                        index=pd.bdate_range("2026-01-05", periods=200))
    assert tolerancia_de(tranquilo) < tolerancia_de(volatil)
    assert tolerancia_de(tranquilo) >= .005  # nunca por debajo del piso


def test_el_factor_devuelve_el_dividendo_en_la_fecha_ex():
    serie = _serie_con_dividendo(monto=5.0, indice_ex=40)
    tabla = pd.DataFrame([{"alphadata_ticker": "BCI", "fecha_ex": DIAS[40], "monto": 5.0}])
    f = factores(tabla, serie)
    ajustada = serie * f
    # El día ex el crudo cae; el ajustado no debe mostrar esa caída.
    assert serie.pct_change().loc[DIAS[40]] < -.03
    assert abs(ajustada.pct_change().loc[DIAS[40]]) < .005
    # Y después de la fecha ex el factor es 1: el ajustado es el crudo.
    assert f.loc[DIAS[41]] == pytest.approx(1.0)


def test_sin_dividendos_el_ajustado_es_el_crudo():
    crudo = pd.DataFrame({"date": DIAS, "alphadata_ticker": "BCI",
                          "close": np.linspace(100, 120, len(DIAS))})
    derivado = derivar_ajustado(crudo, pd.DataFrame(columns=["alphadata_ticker", "fecha_ex", "monto"]))
    assert np.allclose(derivado.to_numpy(), crudo.close.to_numpy())


def test_solo_se_tocan_los_instrumentos_indicados():
    # EE.UU., oro y tipo de cambio conservan el ajustado del proveedor, que en
    # su mercado funciona.
    filas = []
    for t in ("BCI", "ABT"):
        for f, c in zip(DIAS[:5], [100.0, 101, 102, 103, 104]):
            filas.append({"date": f, "alphadata_ticker": t, "close": c, "adjusted_close": c * .9})
    precios = pd.DataFrame(filas)
    salida = aplicar_ajuste(precios, pd.DataFrame(columns=["alphadata_ticker", "fecha_ex", "monto"]), {"BCI"})
    bci = salida[salida.alphadata_ticker == "BCI"]
    abt = salida[salida.alphadata_ticker == "ABT"]
    assert np.allclose(bci.adjusted_close.to_numpy(), bci.close.to_numpy())      # derivado
    assert np.allclose(abt.adjusted_close.to_numpy(), abt.close.to_numpy() * .9)  # intacto


def test_un_dividendo_chico_no_se_confirma_con_el_precio_sino_por_convencion():
    # La prueba nula mostró que buscar la fecha de un dividendo pequeño en una
    # serie ruidosa "confirma" algo el 100% de las veces aunque no haya habido
    # reparto. Por debajo del umbral no se busca: se usa la convención y se
    # marca como tal, para no dar por verificado lo que no lo está.
    serie = pd.Series(np.linspace(100, 120, len(DIAS)), index=DIAS)
    calce = localizar_fecha_ex(serie, DIAS[45], 0.05)   # cinco centésimas: ruido puro
    assert calce is not None and not calce["rechazado"]
    assert calce["origen"] == POR_CONVENCION
    assert calce["fecha_ex"] == DIAS[40]                 # cinco ruedas antes


def test_un_dividendo_grande_si_se_confirma_con_el_precio():
    serie = _serie_con_dividendo(monto=8.0, indice_ex=40)
    calce = localizar_fecha_ex(serie, DIAS[45], 8.0)
    assert calce is not None and not calce["rechazado"]
    assert calce["origen"] == CONFIRMADA
    assert calce["fecha_ex"] == DIAS[40]


def test_un_dividendo_nuevo_del_proveedor_se_detecta():
    tabla = pd.DataFrame([{"alphadata_ticker": "BCI", "fecha_declarada": pd.Timestamp("2026-04-10")}])
    pendientes = pd.DataFrame(columns=["alphadata_ticker", "fecha_declarada"])
    eventos = [{"fecha_declarada": pd.Timestamp("2026-04-10"), "monto": 100.0},
               {"fecha_declarada": pd.Timestamp("2026-09-15"), "monto": 120.0}]
    nuevos = detectar_nuevos(tabla, pendientes, eventos, "BCI")
    assert len(nuevos) == 1 and nuevos[0]["fecha_declarada"] == pd.Timestamp("2026-09-15")
    # Y lo que ya está pendiente no se anota dos veces.
    pendientes = pd.DataFrame([{"alphadata_ticker": "BCI", "fecha_declarada": pd.Timestamp("2026-09-15")}])
    assert detectar_nuevos(tabla, pendientes, eventos, "BCI") == []


def test_la_tabla_publicada_pasa_su_prueba_de_aceptacion_donde_es_verificable():
    """Regresión con datos reales, separando lo verificado de lo asumido.

    Sólo los dividendos grandes se pueden verificar contra el precio, y son
    justamente los que producían los artefactos visibles: el +9,33% de Banco de
    Chile venía de uno de ellos. Los pequeños se fechan por convención y su
    error es del tamaño del propio dividendo, que es chico por definición.
    """
    tabla = ROOT / "data" / "dividendos.csv"
    if not tabla.exists():
        pytest.skip("todavía no se ha construido la tabla de dividendos")
    dividendos = pd.read_csv(tabla, parse_dates=["fecha_ex"])
    precios = pd.read_csv(ROOT / "data" / "market_prices_daily.csv", parse_dates=["date"])
    confirmadas = dividendos.loc[dividendos.origen.map(confirmada_por_precio)]
    assert len(confirmadas) >= 5

    crudos, ajustados = [], []
    for evento in confirmadas.itertuples():
        serie = precios.loc[precios.alphadata_ticker == evento.alphadata_ticker].set_index("date")
        crudo = serie["close"].pct_change().get(evento.fecha_ex)
        ajustado = serie["adjusted_close"].pct_change().get(evento.fecha_ex)
        if pd.notna(crudo) and pd.notna(ajustado):
            crudos.append(crudo)
            ajustados.append(ajustado)
    assert len(crudos) >= 5
    # El crudo cae con fuerza en la fecha ex y el ajustado devuelve el dividendo.
    assert float(np.mean(crudos)) < -.04
    assert abs(float(np.mean(ajustados))) < .02
