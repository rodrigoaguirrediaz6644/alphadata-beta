"""El libro lo escribe producción, no un recorrido que se regenera.

`tools/construir_libro.py` llenó el pasado una sola vez. Si el libro siguiera
siendo un artefacto derivado, en tres meses estaríamos otra vez sin saber desde
cuándo viene cada posición. Lo que se prueba acá es que cada corrida agrega sus
aperturas, cierra sus salidas y **no toca lo que ya estaba escrito**.
"""

import pandas as pd

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
