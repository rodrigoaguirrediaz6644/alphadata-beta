import pandas as pd

from src.price_store import agregar, cambios_de_ajuste, instrumentos_con_simbolo_nuevo


def _filas(ticker, fechas, cierres, simbolo=None):
    return pd.DataFrame([
        {"date": pd.Timestamp(f), "alphadata_ticker": ticker, "yahoo_ticker": simbolo or f"{ticker}.SN",
         "open": c, "high": c, "low": c, "close": c, "adjusted_close": c, "volume": 1000}
        for f, c in zip(fechas, cierres)
    ])


def test_una_fecha_nueva_se_agrega():
    guardado = _filas("BCI", ["2026-07-15", "2026-07-16"], [100, 101])
    nuevo = _filas("BCI", ["2026-07-17"], [102])
    resultado, revisiones = agregar(guardado, nuevo)
    assert len(resultado) == 3 and revisiones.empty
    assert resultado.close.tolist() == [100, 101, 102]


def test_un_cierre_ya_grabado_no_se_sobrescribe_y_se_informa():
    # El caso que originó todo: el proveedor devuelve otro valor para una fecha
    # que ya tenía dato. Se conserva lo grabado y la diferencia se reporta.
    guardado = _filas("ILC", ["2026-08-28"], [25500])
    nuevo = _filas("ILC", ["2026-08-28"], [21450])
    resultado, revisiones = agregar(guardado, nuevo)
    assert resultado.close.iloc[0] == 25500
    # El fixture pone el mismo valor en apertura, máximo, mínimo y cierre, así
    # que las cuatro columnas crudas difieren y las cuatro se informan.
    assert set(revisiones.columna) == {"open", "high", "low", "close"}
    cierre = revisiones.loc[revisiones.columna == "close"].iloc[0]
    assert cierre.guardado == 25500 and cierre.recibido == 21450


def test_el_cierre_ajustado_si_se_actualiza_porque_es_derivado():
    guardado = _filas("BCI", ["2026-07-15"], [100])
    nuevo = guardado.copy(); nuevo["adjusted_close"] = 97.0
    resultado, revisiones = agregar(guardado, nuevo)
    assert resultado.close.iloc[0] == 100      # el crudo no se toca
    assert resultado.adjusted_close.iloc[0] == 97.0
    assert revisiones.empty


def test_un_dividendo_deja_rastro_con_su_factor():
    guardado = _filas("BCI", ["2026-07-13", "2026-07-14", "2026-07-15"], [100, 101, 102])
    nuevo = guardado.copy(); nuevo["adjusted_close"] = nuevo.adjusted_close * .97
    rastro = cambios_de_ajuste(guardado, nuevo)
    assert len(rastro) == 1
    assert rastro.iloc[0].dias == 3 and abs(rastro.iloc[0].factor - .97) < 1e-6


def test_un_cambio_de_simbolo_regraba_el_instrumento_entero():
    # IPSA_TR pasó de ^IPSA al ETF proxy: son niveles distintos y encadenarlos
    # inventaría un salto de rentabilidad.
    guardado = _filas("IPSA_TR", ["2026-07-14", "2026-07-15"], [5000, 5010], simbolo="^IPSA")
    nuevo = _filas("IPSA_TR", ["2026-07-16"], [212], simbolo="CFMITNIPSA.SN")
    assert instrumentos_con_simbolo_nuevo(guardado, nuevo) == {"IPSA_TR"}
    resultado, _ = agregar(guardado, nuevo)
    assert resultado.close.tolist() == [212]


def test_un_almacen_vacio_acepta_la_primera_descarga():
    nuevo = _filas("BCI", ["2026-07-15"], [100])
    resultado, revisiones = agregar(pd.DataFrame(), nuevo)
    assert len(resultado) == 1 and revisiones.empty
