"""La tabla de cada cartera.

Con el precio de ingreso al lado del actual, la rentabilidad de la fila se puede
verificar de memoria en vez de tener que creerla.
"""

import pandas as pd

from src.reporting_public import _positions


CARTERA = pd.DataFrame({
    "ticker": ["ITAUCL"], "target_weight": [.125], "opened_at": ["2026-02-27"],
    "entry_price": [20900.], "current_price": [24200.], "open_return": [.2293],
})


def test_la_tabla_muestra_el_precio_de_ingreso_junto_al_actual():
    html = _positions(CARTERA)
    assert "<th>Precio de ingreso</th><th>Precio actual</th>" in html
    # Con los dos precios a la vista el +22,9% se puede verificar de memoria.
    assert "20.900,00" in html and "24.200,00" in html
    assert "<th>Fecha de ingreso</th>" in html and "27-02-2026" in html
    assert "<th>Rentabilidad</th>" in html and "+22,9%" in html


def test_una_posicion_sin_precio_de_ingreso_no_rompe_la_tabla():
    """Las del borde del recorrido no tienen precio y la fila igual se dibuja."""
    sin_precio = CARTERA.assign(entry_price=[pd.NA], opened_at=[pd.NaT], open_return=[pd.NA])
    html = _positions(sin_precio)
    assert html.count("<td>—</td>") >= 2
    assert "ITAUCL" in html


def test_la_columna_de_la_estrategia_dice_desde_cuando_mide(tmp_path, monkeypatch):
    import src.reporting_public as rp
    monkeypatch.setattr(rp, "DIRECTORIO_GRAFICOS", tmp_path)
    historia = pd.DataFrame([
        {"date": "2026-09-16", "Delta-12": 100, "Gamma-6": 100, "Conjunto AlphaData": 100},
        {"date": "2026-09-18", "Delta-12": 101, "Gamma-6": 100, "Conjunto AlphaData": 100},
    ])
    vacio = pd.DataFrame(columns=["ticker", "action", "target_weight"])
    _, html = rp.build_public_report(pd.Timestamp("2026-09-18"), CARTERA, vacio,
                                     pd.DataFrame([{"status": "OK"}]), pd.DataFrame(), historia)
    assert "<th>Desde el 01-01-2026</th>" in html
    assert "Desde el inicio" not in html


def test_la_inversion_es_el_porcentaje_con_que_entra_y_no_los_pesos():
    con_monto = CARTERA.assign(monto_clp=[625000.], peso_real=[.199])
    html = _positions(con_monto)
    assert "<th>Inversión</th>" in html and "<td>12,5%</td>" in html
    for fuera in ("Cuánto invertir", "$ 625.000", "Peso hoy", "19,9%", "Peso de entrada", "objetivo"):
        assert fuera not in html


def test_la_caja_se_sigue_diciendo_en_pesos():
    """En porcentajes, la caja de Sigma-6 pasaba inadvertida; en pesos, no."""
    from src.reporting_public import _caja
    # Cinco posiciones al 10% dejan la mitad de la pieza sin invertir.
    sigma = pd.DataFrame({"ticker": list("ABCDE"), "target_weight": [.1] * 5})
    assert "$ 2.500.000" in _caja(sigma, 5_000_000)
    assert _caja(pd.DataFrame({"ticker": ["A"], "target_weight": [1.]}), 5_000_000) == ""


def test_los_dividendos_recibidos_van_en_pesos_y_solo_donde_los_hay():
    """VAPORES entró a $48,89, hoy vale $48,30 y recibió $6,71: la aritmética se sigue de la fila."""
    con = CARTERA.assign(entry_price=[48.89], current_price=[48.30], open_return=[.129],
                         dividendos_clp=[6.705327], con_dividendo=[False])
    html = _positions(con)
    assert "<th>Dividendos recibidos</th>" in html and "$ 6,71" in html
    # Sin monto itemizado —las estadounidenses— la columna no aparece.
    sin = CARTERA.assign(dividendos_clp=[pd.NA], con_dividendo=[True])
    assert "Dividendos" not in _positions(sin)


def test_la_rentabilidad_no_lleva_marcas_sin_explicacion():
    """El asterisco remitía a una nota que salió del informe: solo, no dice nada."""
    con = CARTERA.assign(open_return=[.129], con_dividendo=[True])
    assert "*" not in _positions(con)


def test_la_columna_avisa_cuando_caduca_la_recomendacion():
    """El único reloj que le queda a Sigma-6, y el que la va a ir vaciando.

    El tope de tenencia de 365 días salió el 21-09-2026. Lo que sigue vigente
    es la caducidad de la recomendación: con el flujo de Credicorp detenido
    desde el 22-07-2026, VAPORES se cae el 24-11-2026 y el resto hasta julio de
    2027. Una salida por calendario es información de ejecución.
    """
    from src.reporting_public import _caducidad
    assert _caducidad("2026-11-24", 68) == "<strong>24-11-2026</strong> · en 68 días"
    assert _caducidad("2027-07-01", 287) == "01-07-2027"
    assert _caducidad(pd.NaT, pd.NA) == "—"
    cerca = CARTERA.assign(caduca=["2026-11-24"], dias_para_caducar=[68])
    html = _positions(cerca)
    assert "<th>Recomendación vigente hasta</th>" in html and "en 68 días" in html
    # Las piezas que no dependen de recomendaciones no llevan la columna.
    assert "<th>Recomendación vigente hasta</th>" not in _positions(CARTERA)
