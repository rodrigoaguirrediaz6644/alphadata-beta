"""El libro lo escribe producción, no un recorrido que se regenera.

`tools/construir_libro.py` llenó el pasado una sola vez. Si el libro siguiera
siendo un artefacto derivado, en tres meses estaríamos otra vez sin saber desde
cuándo viene cada posición. Lo que se prueba acá es que cada corrida agrega sus
aperturas, cierra sus salidas y **no toca lo que ya estaba escrito**.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

from src.libro import abiertas, anotar, cargar, guardar

PRECIOS = pd.DataFrame({
    "alphadata_ticker": ["BCI", "BCI", "CHILE", "CHILE"],
    "date": pd.to_datetime(["2026-09-11", "2026-09-18", "2026-09-11", "2026-09-18"]),
    "close": [64500., 65600., 180.5, 197.9],
})


def _cartera(tickers):
    return pd.DataFrame({"ticker": tickers, "target_weight": [1 / len(tickers)] * len(tickers)}) if tickers \
        else pd.DataFrame(columns=["ticker", "target_weight"])


def test_una_apertura_nueva_queda_con_la_fecha_de_la_senal():
    libro, movimientos = anotar(pd.DataFrame(columns=["estrategia", "instrumento", "fecha_entrada",
                                                      "precio_entrada", "fecha_salida", "origen"]),
                                "Sigma-6", _cartera(["BCI"]), pd.Timestamp("2026-09-18"), PRECIOS)
    assert movimientos == ["abre BCI"]
    fila = libro.iloc[0]
    assert fila.fecha_entrada == pd.Timestamp("2026-09-18")
    assert fila.precio_entrada == 65600.
    assert pd.isna(fila.fecha_salida)
    assert fila.origen == "produccion"


def test_mantener_una_posicion_no_reescribe_su_fecha_de_entrada():
    """Es el error que el libro vino a arreglar: cada corrida decía «hoy»."""
    libro = pd.DataFrame(columns=["estrategia", "instrumento", "fecha_entrada",
                                  "precio_entrada", "fecha_salida", "origen"])
    libro, _ = anotar(libro, "Sigma-6", _cartera(["BCI"]), pd.Timestamp("2026-09-11"), PRECIOS)
    libro, movimientos = anotar(libro, "Sigma-6", _cartera(["BCI"]), pd.Timestamp("2026-09-18"), PRECIOS)
    assert movimientos == []
    assert len(libro) == 1
    assert libro.iloc[0].fecha_entrada == pd.Timestamp("2026-09-11")
    assert libro.iloc[0].precio_entrada == 64500.


def test_una_salida_se_cierra_y_una_reentrada_abre_fila_nueva():
    libro = pd.DataFrame(columns=["estrategia", "instrumento", "fecha_entrada",
                                  "precio_entrada", "fecha_salida", "origen"])
    libro, _ = anotar(libro, "Sigma-6", _cartera(["BCI"]), pd.Timestamp("2026-09-11"), PRECIOS)
    libro, salida = anotar(libro, "Sigma-6", _cartera(["CHILE"]), pd.Timestamp("2026-09-18"), PRECIOS)
    assert salida == ["cierra BCI", "abre CHILE"]
    libro, vuelta = anotar(libro, "Sigma-6", _cartera(["CHILE", "BCI"]), pd.Timestamp("2026-09-18"), PRECIOS)
    assert vuelta == ["abre BCI"]
    assert len(libro) == 3
    assert abiertas(libro, "Sigma-6") == {"CHILE": pd.Timestamp("2026-09-18"),
                                          "BCI": pd.Timestamp("2026-09-18")}


def test_cada_estrategia_lleva_su_propia_cuenta():
    """BCI está en Sigma-6 y en Delta-12 al mismo tiempo, con fechas distintas."""
    libro = pd.DataFrame(columns=["estrategia", "instrumento", "fecha_entrada",
                                  "precio_entrada", "fecha_salida", "origen"])
    libro, _ = anotar(libro, "Sigma-6", _cartera(["BCI"]), pd.Timestamp("2026-09-11"), PRECIOS)
    libro, _ = anotar(libro, "Delta-12", _cartera(["BCI"]), pd.Timestamp("2026-09-18"), PRECIOS)
    libro, movimientos = anotar(libro, "Sigma-6", _cartera([]), pd.Timestamp("2026-09-18"), PRECIOS)
    assert movimientos == ["cierra BCI"]
    assert abiertas(libro, "Sigma-6") == {}
    assert abiertas(libro, "Delta-12") == {"BCI": pd.Timestamp("2026-09-18")}


def test_el_libro_sobrevive_el_viaje_por_disco(tmp_path):
    libro = pd.DataFrame(columns=["estrategia", "instrumento", "fecha_entrada",
                                  "precio_entrada", "fecha_salida", "origen"])
    libro, _ = anotar(libro, "Sigma-6", _cartera(["BCI"]), pd.Timestamp("2026-09-11"), PRECIOS)
    ruta = tmp_path / "libro_posiciones.csv"
    guardar(libro, ruta)
    guardar(cargar(ruta), ruta)  # dos vueltas: la fecha no puede ir derivando
    vuelta = cargar(ruta)
    assert abiertas(vuelta, "Sigma-6") == {"BCI": pd.Timestamp("2026-09-11")}
    assert ruta.read_text(encoding="utf-8").count("2026-09-11") == 1


def test_los_movimientos_salen_del_libro_y_no_de_comparar_carteras():
    """El bloque del informe mira la fecha de señal, no la corrida anterior.

    Una posición abierta hace ocho meses no es una compra de esta semana. Que
    lo fuera es lo que puso «Comprar INTC» en la misma página en que la tabla
    decía «comprada el 30-09-2025».
    """
    from src.libro import movimientos_de
    libro = pd.DataFrame([
        {"estrategia": "Delta-12", "instrumento": "ANDINA-B", "fecha_entrada": pd.Timestamp("2026-08-31"),
         "precio_entrada": 4530., "fecha_salida": pd.NaT, "origen": "produccion"},
        {"estrategia": "Delta-12", "instrumento": "ILC", "fecha_entrada": pd.Timestamp("2026-06-30"),
         "precio_entrada": 11000., "fecha_salida": pd.Timestamp("2026-08-31"), "origen": "produccion"},
        {"estrategia": "Gamma-6", "instrumento": "INTC", "fecha_entrada": pd.Timestamp("2025-09-30"),
         "precio_entrada": 32373., "fecha_salida": pd.NaT, "origen": "recorrido"},
    ])
    m = movimientos_de(libro, {"Delta-12": pd.Timestamp("2026-08-31"), "Gamma-6": pd.Timestamp("2026-08-31")})
    assert set(zip(m.instrumento, m.accion)) == {("ANDINA-B", "COMPRAR"), ("ILC", "VENDER")}
    assert "INTC" not in set(m.instrumento)


def test_sin_nada_en_la_fecha_de_senal_el_bloque_viene_vacio():
    from src.libro import movimientos_de
    libro = pd.DataFrame([{"estrategia": "Sigma-6", "instrumento": "BCI",
                           "fecha_entrada": pd.Timestamp("2026-01-16"), "precio_entrada": 64500.,
                           "fecha_salida": pd.NaT, "origen": "recorrido"}])
    assert movimientos_de(libro, {"Sigma-6": pd.Timestamp("2026-09-17")}).empty


def test_el_precio_de_entrada_lo_manda_el_libro_no_la_serie():
    """En una copia con febrero alterado, ITAUCL pasaba de $20.900 a $8.360."""
    from src.libro import precios_de_entrada
    libro = pd.DataFrame([
        {"estrategia": "Delta-12", "instrumento": "ITAUCL", "fecha_entrada": pd.Timestamp("2026-02-27"),
         "precio_entrada": 20900., "fecha_salida": pd.NaT, "origen": "recorrido"},
        {"estrategia": "Delta-12", "instrumento": "SQM-B", "fecha_entrada": pd.Timestamp("2026-01-30"),
         "precio_entrada": 30000., "fecha_salida": pd.Timestamp("2026-02-27"), "origen": "recorrido"},
        {"estrategia": "Sigma-6", "instrumento": "BORDE", "fecha_entrada": pd.Timestamp("2025-01-02"),
         "precio_entrada": None, "fecha_salida": pd.NaT, "origen": "recorrido (borde)"},
    ])
    assert precios_de_entrada(libro, "Delta-12") == {"ITAUCL": 20900.}  # la cerrada no entra
    assert precios_de_entrada(libro, "Sigma-6") == {}  # sin precio, no se inventa


def test_alterar_un_precio_pasado_no_mueve_ninguna_fila_del_libro():
    """Correr dos veces prueba determinismo; esto prueba que no deriva.

    Sobre una copia de trabajo con veinte ruedas de febrero de ITAUCL
    multiplicadas por 0,4, el recorrido movía su entrada del 27-02 al 31-03 —o
    sea, un recálculo sí cambia— y el libro no se movió ni un byte. Acá se
    reproduce la parte que corre en producción: anotar con precios distintos de
    los guardados no puede tocar lo ya escrito.
    """
    libro = pd.DataFrame([
        {"estrategia": "Delta-12", "instrumento": "BCI", "fecha_entrada": pd.Timestamp("2026-09-11"),
         "precio_entrada": 64500., "fecha_salida": pd.NaT, "origen": "produccion"},
        {"estrategia": "Delta-12", "instrumento": "SQM-B", "fecha_entrada": pd.Timestamp("2026-08-31"),
         "precio_entrada": 30000., "fecha_salida": pd.Timestamp("2026-09-11"), "origen": "produccion"},
    ])
    alterados = PRECIOS.copy()
    alterados.loc[alterados.date == pd.Timestamp("2026-09-11"), "close"] *= .4
    despues, movimientos = anotar(libro.copy(), "Delta-12", _cartera(["BCI"]),
                                  pd.Timestamp("2026-09-18"), alterados)
    assert movimientos == []
    pd.testing.assert_frame_equal(despues.reset_index(drop=True), libro.reset_index(drop=True))


def test_los_dos_bloques_del_informe_no_pueden_contradecirse():
    """El invariante entre movimientos y cartera, que el reinicio rompió.

    Toda COMPRAR del bloque de movimientos tiene que estar en la cartera con
    esa misma fecha, y ninguna posición más vieja puede aparecer como
    movimiento. Sin esto el informe publicó veinte «Comprar» para posiciones
    que llevaban meses abiertas, entre ellas INTC desde el 30-09-2025.
    """
    from src.libro import abiertas, movimientos_de
    libro = pd.read_csv(ROOT / "data" / "libro_posiciones.csv",
                        parse_dates=["fecha_entrada", "fecha_salida"])
    senales = {"Sigma-6": pd.Timestamp("2026-09-17"), "Delta-12": pd.Timestamp("2026-08-31"),
               "Gamma-6": pd.Timestamp("2026-08-31"), "Oro": pd.Timestamp("2026-09-17")}
    movimientos = movimientos_de(libro, senales)
    for estrategia, senal in senales.items():
        cartera = abiertas(libro, estrategia)
        compras = movimientos.loc[(movimientos.estrategia == estrategia)
                                  & (movimientos.accion == "COMPRAR")]
        for instrumento in compras.instrumento:
            assert instrumento in cartera, f"{instrumento} se manda comprar y no está en la cartera"
            assert cartera[instrumento] == senal, f"{instrumento} se manda comprar con otra fecha"
        anteriores = {t for t, f in cartera.items() if f < senal}
        assert not (anteriores & set(compras.instrumento)), "una posición vieja aparece como compra"
        ventas = movimientos.loc[(movimientos.estrategia == estrategia)
                                 & (movimientos.accion == "VENDER")]
        assert not (set(ventas.instrumento) & set(cartera)), "se manda vender algo que sigue abierto"
