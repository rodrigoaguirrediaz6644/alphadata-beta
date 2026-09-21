"""La tabla de posiciones y el periodo que mide cada columna.

El informe muestra dos rendimientos en la misma página: cuánto se movió una
acción desde que se compró, y cuánto rinde la estrategia desde que arrancó el
seguimiento. No tienen por qué calzar, y la trampa es dejar las dos columnas
etiquetadas igual, porque entonces el lector concluye que una está mala.
"""

import pandas as pd

from src.reporting_public import _positions


CARTERA = pd.DataFrame({
    "ticker": ["ITAUCL"], "target_weight": [.125], "opened_at": ["2026-02-27"],
    "entry_price": [20900.], "current_price": [24200.], "open_return": [.2293],
})


def test_la_tabla_muestra_el_precio_de_entrada_junto_al_de_hoy():
    html = _positions(CARTERA)
    assert "<th>Precio de entrada</th><th>Precio hoy</th>" in html
    # Con los dos precios a la vista el +22,9% se puede verificar de memoria.
    assert "20.900,00" in html and "24.200,00" in html
    assert "27-02-2026" in html


def test_una_posicion_sin_precio_de_entrada_no_rompe_la_tabla():
    """Las del borde del recorrido no tienen precio y la fila igual se dibuja."""
    sin_precio = CARTERA.assign(entry_price=[pd.NA], opened_at=[pd.NaT], open_return=[pd.NA])
    html = _positions(sin_precio)
    assert html.count("<td>—</td>") >= 2
    assert "ITAUCL" in html


def test_la_columna_de_la_estrategia_dice_desde_cuando_mide(tmp_path, monkeypatch):
    """Sin la fecha, «desde el inicio» y «va ganando» se leen como lo mismo."""
    import src.reporting_public as rp
    monkeypatch.setattr(rp, "DIRECTORIO_GRAFICOS", tmp_path)
    historia = pd.DataFrame([
        {"date": "2026-09-16", "Sigma-6": 100, "Delta-12": 100, "Conjunto AlphaData": 100},
        {"date": "2026-09-18", "Sigma-6": 101, "Delta-12": 100, "Conjunto AlphaData": 100},
    ])
    vacio = pd.DataFrame(columns=["ticker", "action", "target_weight"])
    _, html = rp.build_public_report(pd.Timestamp("2026-09-18"), CARTERA, CARTERA, vacio, vacio,
                                     pd.DataFrame([{"status": "OK"}]), pd.DataFrame(), historia)
    assert "<th>Desde el 16-09-2026</th>" in html
    assert "Desde el inicio" not in html
    # Y la advertencia de que los dos números no calzan va donde se leen.
    assert "no tienen por qué calzar" in html


def test_una_variacion_con_dividendo_va_marcada():
    """Nueve de veinte posiciones abiertas cobraron dividendo: es lo normal.

    VAPORES entró a $48,89, hoy vale $48,30 y va ganando +12,9%. Con los dos
    precios en la misma fila, ese número se lee como un error de cálculo si no
    se dice que la variación incluye lo que se cobró.
    """
    con = CARTERA.assign(entry_price=[48.89], current_price=[48.30],
                         open_return=[.129], con_dividendo=[True])
    html = _positions(con)
    assert "+12,9% *" in html
    sin = con.assign(con_dividendo=[False])
    assert "*" not in _positions(sin)


def test_sin_ninguna_fila_marcada_no_se_imprime_la_nota(tmp_path, monkeypatch):
    import src.reporting_public as rp
    monkeypatch.setattr(rp, "DIRECTORIO_GRAFICOS", tmp_path)
    historia = pd.DataFrame([{"date": "2026-09-16", "Conjunto AlphaData": 100},
                             {"date": "2026-09-18", "Conjunto AlphaData": 101}])
    vacio = pd.DataFrame(columns=["ticker", "action", "target_weight"])
    limpia = CARTERA.assign(con_dividendo=[False])
    _, html = rp.build_public_report(pd.Timestamp("2026-09-18"), limpia, limpia, vacio, vacio,
                                     pd.DataFrame([{"status": "OK"}]), pd.DataFrame(), historia)
    assert "repartió dividendos" not in html


def test_la_tabla_dice_cuantos_pesos_va_en_cada_accion():
    """En porcentajes, la caja de Sigma-6 pasaba inadvertida; en pesos, no."""
    from src.reporting_public import _caja
    con_monto = CARTERA.assign(monto_clp=[625000.])
    html = _positions(con_monto)
    assert "<th>Cuánto invertir</th>" in html and "$ 625.000" in html
    # Cinco posiciones al 10% dejan la mitad de la pieza sin invertir.
    sigma = pd.DataFrame({"ticker": list("ABCDE"), "target_weight": [.1] * 5})
    assert "$ 2.500.000" in _caja(sigma, 5_000_000)
    assert _caja(pd.DataFrame({"ticker": ["A"], "target_weight": [1.]}), 5_000_000) == ""


def test_los_dividendos_van_en_pesos_y_no_como_nota_al_pie():
    """Nueve de veinte filas marcadas es demasiado para un asterisco.

    Con el monto a la vista, la aritmética se sigue de la fila: VAPORES entró a
    $48,89, hoy vale $48,30 y cobró $6,71.
    """
    con = CARTERA.assign(entry_price=[48.89], current_price=[48.30], open_return=[.129],
                         dividendos_clp=[6.705327], con_dividendo=[False])
    html = _positions(con)
    assert "<th>Dividendos cobrados</th>" in html and "$ 6,71" in html
    assert "+12,9% *" not in html
    # Sin monto itemizado —las estadounidenses— la fila conserva la marca.
    sin = CARTERA.assign(dividendos_clp=[pd.NA], con_dividendo=[True])
    html = _positions(sin)
    assert "<th>Dividendos cobrados</th>" not in html
    assert "*" in html


def test_la_columna_de_tenencia_avisa_antes_de_que_el_calendario_venda():
    """Una venta por calendario es información de ejecución, no de señal.

    BCI entró el 24-10-2025 y toca el tope de 365 días a fines de octubre de
    2026. Sin la columna, esa venta aparecería sin aviso en un informe que
    muestra la posición ganando +44,7%.
    """
    from src.reporting_public import _tenencia
    assert _tenencia(328, 365) == ("<strong>328 de 365 días</strong> · toca el tope en 37")
    assert _tenencia(20, 365) == "20 de 365 días"
    assert _tenencia(pd.NA, 365) == "—"
    cerca = CARTERA.assign(dias_tenencia=[328], tope_tenencia=[365])
    html = _positions(cerca)
    assert "<th>Tiempo en cartera</th>" in html and "toca el tope en 37" in html
    # Las piezas sin tope no llevan la columna.
    assert "<th>Tiempo en cartera</th>" not in _positions(CARTERA)


def test_el_informe_dice_que_las_fechas_salen_de_aplicar_las_reglas_hacia_atras(tmp_path, monkeypatch):
    """Nunca hubo sistema en vivo antes del 15-07-2026.

    «Comprada el 27-02-2026» se lee como que alguien la tuvo desde febrero. Lo
    que pasó es que el modelo la seleccionó ese día y no la ha soltado.
    """
    import src.reporting_public as rp
    monkeypatch.setattr(rp, "DIRECTORIO_GRAFICOS", tmp_path)
    historia = pd.DataFrame([{"date": "2026-09-16", "Conjunto AlphaData": 100},
                             {"date": "2026-09-18", "Conjunto AlphaData": 101}])
    vacio = pd.DataFrame(columns=["ticker", "action", "target_weight"])
    _, html = rp.build_public_report(pd.Timestamp("2026-09-18"), CARTERA, CARTERA, vacio, vacio,
                                     pd.DataFrame([{"status": "OK"}]), pd.DataFrame(), historia)
    assert "no de operaciones registradas en vivo" in html
    assert "el modelo la seleccionó ese día y no la ha soltado" in html


def test_la_columna_de_peso_hoy_marca_la_deriva_grande():
    """El NAV supone que la cartera vuelve al objetivo todos los días.

    Nadie da esa orden ni paga ese costo, así que en una cuenta real los
    ganadores se concentran: INTC salió del 16,7% y hoy pesa 19,9%. Sin la
    columna eso es invisible hasta que es grande.
    """
    from src.reporting_public import _deriva
    assert _deriva(.199, 1 / 6) == "<strong>19,9%</strong>"   # 3,2 puntos: se marca
    assert _deriva(.163, 1 / 6) == "16,3%"                    # 0,4 puntos: ruido
    assert _deriva(pd.NA, 1 / 6) == "—"
    con = CARTERA.assign(peso_real=[.199])
    html = _positions(con)
    assert "<th>Peso hoy</th>" in html and "<strong>19,9%</strong>" in html
    assert "<th>Peso hoy</th>" not in _positions(CARTERA)
