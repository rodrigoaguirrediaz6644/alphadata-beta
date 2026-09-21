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
