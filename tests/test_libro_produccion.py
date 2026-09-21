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


def test_los_movimientos_comparan_contra_la_cartera_del_informe_anterior():
    """No contra la fecha de señal, que dejaba cambios invisibles.

    El primer informe dijo «Comprar CENCOMALLS». Al encender la SMA200, el
    recorrido situó su salida en la revisión del 11-09 y no en la del 17-09,
    así que el informe siguiente no la tenía y **nunca dijo que la vendiera**.
    Quien la hubiera comprado se quedaba con una posición que el modelo ya no
    tiene y sin ninguna instrucción.
    """
    from src.libro import movimientos_de
    publicada = {"Sigma-6": {"BCI": "2025-10-24", "CENCOMALLS": "2026-04-02", "LTM": "2026-08-28"}}
    vigente = {"Sigma-6": {"BCI": "2025-10-24", "LTM": "2026-09-17", "VAPORES": "2026-06-12"}}
    m = movimientos_de(publicada, vigente)
    assert set(zip(m.instrumento, m.accion)) == {("CENCOMALLS", "VENDER"), ("VAPORES", "COMPRAR")}
    # LTM cambió de fecha al reconstruirse el libro, y eso no es una operación.
    assert "LTM" not in set(m.instrumento)


def test_sin_diferencias_el_bloque_viene_vacio():
    from src.libro import movimientos_de
    cartera = {"Sigma-6": {"BCI": "2026-01-16"}, "Delta-12": {}}
    assert movimientos_de(cartera, cartera).empty


def test_una_estrategia_nueva_entra_entera_y_una_que_desaparece_sale_entera():
    from src.libro import movimientos_de
    m = movimientos_de({"Delta-12": {"ILC": "2026-06-30"}}, {"Gamma-6": {"INTC": "2025-09-30"}})
    assert set(zip(m.estrategia, m.instrumento, m.accion)) == {
        ("Delta-12", "ILC", "VENDER"), ("Gamma-6", "INTC", "COMPRAR")}


def test_la_cartera_publicada_sobrevive_el_viaje_por_disco(tmp_path):
    from src.libro import cartera_publicada, guardar_publicada
    carteras = {"Sigma-6": {"BCI": "2025-10-24"}, "Oro": {"IAU": "2026-01-01"}}
    ruta = tmp_path / "cartera_publicada.json"
    assert cartera_publicada(ruta) == {}   # sin archivo, no inventa nada
    guardar_publicada(carteras, pd.Timestamp("2026-09-17"), ruta)
    assert cartera_publicada(ruta) == carteras


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
    """El invariante, en sus dos direcciones.

    Hacia adelante: toda COMPRAR tiene que estar en la cartera vigente.
    Hacia atrás —la que faltaba—: **toda posición que estaba en el informe
    anterior y ya no está tiene que aparecer como VENDER**. Es el agujero de
    CENCOMALLS, y sin la simétrica no falla.
    """
    from src.libro import abiertas, cartera_publicada, movimientos_de
    libro = pd.read_csv(ROOT / "data" / "libro_posiciones.csv",
                        parse_dates=["fecha_entrada", "fecha_salida"])
    estrategias = ["Sigma-6", "Delta-12", "Gamma-6", "Oro"]
    vigente = {n: {t: f.date().isoformat() for t, f in abiertas(libro, n).items()} for n in estrategias}
    publicada = cartera_publicada(ROOT / "data" / "cartera_publicada.json")
    movimientos = movimientos_de(publicada, vigente)
    for estrategia in estrategias:
        antes = set(publicada.get(estrategia, {}))
        ahora = set(vigente.get(estrategia, {}))
        de_la_pieza = movimientos.loc[movimientos.estrategia == estrategia]
        compras = set(de_la_pieza.loc[de_la_pieza.accion == "COMPRAR", "instrumento"])
        ventas = set(de_la_pieza.loc[de_la_pieza.accion == "VENDER", "instrumento"])
        assert compras <= ahora, "se manda comprar algo que no está en la cartera"
        assert not (ventas & ahora), "se manda vender algo que sigue abierto"
        assert compras == ahora - antes, "hay una posición nueva sin orden de compra"
        assert ventas == antes - ahora, "hay una posición que salió sin orden de venta"

