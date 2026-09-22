"""La cartera de ingreso, con sus relojes.

Lo que se prueba acá es que quien va a poner la primera orden vea lo que está
comprando: cuántas unidades caben, cuánto queda suelto, hace cuánto el modelo
tiene la posición, cuándo sale si tiene fecha, y qué cuesta el par
entrada-salida en ese plazo.
"""

import pandas as pd

from src.ingreso import PERMANENTE, SIN_FECHA, cartera_de_ingreso, costo_del_par, markdown

AS_OF = pd.Timestamp("2026-09-17")
COSTOS = {"Sigma-6": (.001785, 999.99), "Delta-12": (.001785, 999.99),
          "Gamma-6": (.001, 0.), "Oro": (.001, 0.)}


def _cartera(**kwargs):
    base = {"ticker": "BCI", "target_weight": .1, "monto_clp": 500_000.,
            "current_price": 65_600., "opened_at": "2024-10-11"}
    return pd.DataFrame([{**base, **kwargs}])


def test_se_redondea_hacia_abajo_y_el_residuo_queda_en_caja():
    """Las acciones se transan por unidades enteras y el suelto es real.

    $500.000 en BCI a $65.600 son 7,62 acciones: se compran 7 por $459.200 y
    quedan $40.800. Multiplicado por veinte posiciones, los pesos efectivos del
    primer día no calzan con los de referencia, y eso es esperado.
    """
    t = cartera_de_ingreso({"Sigma-6": _cartera()}, AS_OF, COSTOS)
    fila = t.iloc[0]
    assert fila.unidades == 7
    assert fila.monto_efectivo == 7 * 65_600.
    assert abs(fila.residuo - 40_800.) < 1e-9
    assert fila.dias_en_cartera == 706


def test_el_costo_del_par_lo_domina_el_minimo_en_lo_chileno():
    # 0,1785% de $459.200 son $820, así que manda el mínimo de $999,99, dos veces.
    assert costo_del_par(459_200., .001785, 999.99) == 2 * 999.99
    # En lo estadounidense no hay mínimo: el porcentaje manda siempre.
    assert abs(costo_del_par(830_431., .001, 0.) - 1660.862) < 1e-6


def test_una_salida_con_fecha_muestra_su_costo_anualizado():
    """Es el punto: el mismo 0,4% no cuesta lo mismo a diez semanas que a diez meses."""
    cerca = _cartera(ticker="VAPORES", current_price=48.30, opened_at="2026-06-12",
                     caduca="2026-11-24", dias_para_caducar=68)
    lejos = _cartera(ticker="PARAUCO", current_price=3900., opened_at="2026-06-26",
                     caduca="2027-07-01", dias_para_caducar=287)
    t = cartera_de_ingreso({"Sigma-6": pd.concat([cerca, lejos], ignore_index=True)}, AS_OF, COSTOS)
    v, p = t.iloc[0], t.iloc[1]
    assert abs(v.costo_pct - p.costo_pct) < .001          # el mismo porcentaje
    assert v.costo_anualizado > 4 * p.costo_anualizado    # y un costo por año muy distinto
    assert "2,1% anual" in markdown(t, AS_OF)


def test_sin_fecha_se_dice_y_no_se_deja_la_celda_vacia():
    """Las salidas por ranking no tienen fecha, que es distinto de no saberse."""
    t = cartera_de_ingreso({"Delta-12": _cartera(monto_clp=625_000.),
                            "Oro": _cartera(ticker="IAU", monto_clp=5_000_000., current_price=77_938.80)},
                           AS_OF, COSTOS)
    assert list(t.proxima_salida) == [SIN_FECHA, PERMANENTE]
    assert t.costo_anualizado.isna().all()
    texto = markdown(t, AS_OF)
    assert "nan" not in texto.lower()
    assert SIN_FECHA in texto and PERMANENTE in texto


def test_la_comision_del_primer_dia_sale_del_modelo_de_cada_pieza():
    """Es lo primero que se puede contrastar contra la boleta de la corredora.

    Y no es el 0,1785% de los $20 millones: sólo lo chileno paga esa tarifa,
    los CDV pagan 0,1% sin mínimo, y el redondeo deja parte sin invertir.
    """
    from src.ingreso import UMBRAL_MINIMO, costo_de_una
    # Sobre el umbral manda el porcentual; bajo el umbral manda el mínimo.
    assert costo_de_una(UMBRAL_MINIMO + 1000, .001785, 999.99) > 999.99
    assert costo_de_una(300_000., .001785, 999.99) == 999.99
    assert costo_de_una(300_000., .001, 0.) == 300.
    carteras = {"Delta-12": _cartera(monto_clp=937_500.),
                "Gamma-6": _cartera(ticker="TGT", monto_clp=1_250_000., current_price=152_490.)}
    t = cartera_de_ingreso(carteras, AS_OF, COSTOS)
    texto = markdown(t, AS_OF)
    assert "Lo que va a cobrar la corredora el primer día" in texto
    assert "0,1785%, con mínimo" in texto and "0,1% de CDV, sin mínimo" in texto
    assert "no es el 0,1785% de los $20 millones" in texto
    # La chilena paga el porcentual sobre lo efectivamente invertido.
    chilena = t.loc[t.estrategia == "Delta-12"].iloc[0]
    assert abs(chilena.costo_de_entrar - .001785 * chilena.monto_efectivo) < 1e-6
