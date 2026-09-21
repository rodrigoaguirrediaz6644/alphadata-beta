import json
from pathlib import Path

import pandas as pd
import pytest

from src.ingest_recommendations import ingest
from src.run_pipeline import enrich_open_positions, movements_for_report
from src.strategy_engine import movements, normalize_broker, normalize_signal
from src.strategy_registry import load_registry


def test_only_credicorp_is_accepted_for_sigma6():
    assert normalize_broker("Credicorp Capital") == "Credicorp Capital"
    assert normalize_broker("BICE") is None
    assert normalize_signal("Sobreponderar") == 1


def test_registry_has_the_four_official_components():
    assert set(load_registry()) == {"SIGMA6", "DELTA12", "GAMMA6", "ORO"}


def test_methodology_document_matches_the_runtime_configuration():
    # La documentación oficial y la configuración que corre el pipeline se
    # escriben en archivos distintos: sin esta prueba se separan en silencio.
    root = Path(__file__).resolve().parents[1]
    runtime = json.loads((root / "config" / "runtime.v2.json").read_text())
    oficial = json.loads((root / "strategies.v2.json").read_text())
    esperadas = set(runtime["enabled_strategies"])
    assert set(oficial["official_strategies"]) == esperadas
    assert set(oficial["combined_portfolio"]["components"]) == esperadas
    assert set(runtime["combined_portfolio"]["components"]) == esperadas
    assert {s["strategy_code"] for s in oficial["strategies"]} == esperadas
    assert oficial["methodology_version"] == runtime["methodology_version"]


def test_runtime_uses_trii_effective_rate():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config" / "runtime.v2.json").read_text())
    assert config["transaction_cost"]["rate"] == 0.001785
    assert config["benchmark"]["alphadata_ticker"] == "IPSA_TR"


def test_position_metadata_does_not_change_movement_logic():
    previous = [{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-06"}]
    current = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-06"}])
    result = movements(previous, current)
    assert result.iloc[0].action == "MANTIENE"


def test_el_precio_que_se_muestra_es_el_crudo_y_la_variacion_va_sobre_el_ajustado():
    """Las tres decisiones de la columna, en un caso con dividendo de por medio.

    BCI cerró en 100 el 01-07 y en 105 el 24-07, y repartió un dividendo que
    deja el ajustado de la entrada en 95. El informe muestra los cierres
    crudos, porque son los que el lector reconoce en la pantalla de su
    corredora, pero la variación se calcula sobre el ajustado: si se calculara
    sobre el crudo, el dividendo cobrado aparecería como una pérdida.

    Y no se descuenta la comisión de entrada: el costo vive en el NAV. La
    consecuencia buscada es que esta columna y el rendimiento de la estrategia
    no cuadren exactamente.
    """
    prices = pd.DataFrame({
        "date": pd.to_datetime(["2026-07-01", "2026-07-24"]),
        "alphadata_ticker": ["BCI", "BCI"],
        "close": [100.0, 105.0],
        "adjusted_close": [95.0, 105.0],
    })
    portfolio = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-01"}])
    result = enrich_open_positions(portfolio, prices, pd.Timestamp("2026-07-24"))
    assert result.iloc[0].entry_price == 100.0
    assert result.iloc[0].current_price == 105.0
    assert abs(result.iloc[0].open_return - (105 / 95 - 1)) < 1e-10


def test_latest_meaningful_movements_are_kept(tmp_path):
    prior = pd.DataFrame([{"ticker": "LTM", "action": "SALE", "previous_weight": .125, "target_weight": 0.0, "change": -.125}])
    path = tmp_path / "movements.csv"
    prior.to_csv(path, index=False)
    routine = pd.DataFrame([{"ticker": "BCI", "action": "MANTIENE", "previous_weight": .125, "target_weight": .125, "change": 0.0}])
    result = movements_for_report(routine, path)
    assert result.iloc[0].action == "SALE"


def test_las_recomendaciones_del_nombre_viejo_siguen_valiendo():
    """Cencosud Shopping se renombró Cenco Malls: es la misma empresa.

    Sin el alias, veintidós recomendaciones reales de Credicorp quedaban
    rechazadas como "fuera del catálogo" y Sigma-6 perdía un instrumento que sí
    puede operar.
    """
    from src.strategy_engine import validate_recommendations
    fila = {"published_at": "2026-09-01", "available_at": "2026-09-01", "broker": "Credicorp Capital",
            "ticker": "CENCOSHOPP", "recommendation": "Comprar", "target_price_min": "", "target_price_max": "",
            "currency": "", "source_url": "", "notes": ""}
    validas, errores = validate_recommendations(pd.DataFrame([fila]), {"CENCOMALLS"})
    assert len(errores) == 0
    assert validas.iloc[0].ticker == "CENCOMALLS"


def test_el_correo_reescribe_los_graficos_a_cid():
    """En el archivo el gráfico apunta al PNG; en el correo, a cid:.

    Son dos destinos con formas distintas: `cid:` sólo funciona dentro del
    mensaje, y dejarlo en el archivo hacía que el informe se viera sin gráficos
    al abrirlo desde el repositorio.
    """
    from src.send_report import GRAFICOS
    html = '<img src="seguimiento_vivo.png"><img src="reconstruccion.png">'
    for nombre in GRAFICOS:
        html = html.replace(f'src="{nombre}"', f'src="cid:{Path(nombre).stem}"')
    assert html == '<img src="cid:seguimiento_vivo"><img src="cid:reconstruccion">'


def test_los_pesos_corren_entre_revisiones_y_el_nav_no_lo_modela():
    """`pesos_corridos` dice dónde quedó cada peso sin tocar la cartera.

    Dos posiciones al 50%: una duplica y la otra se queda quieta. La que subió
    pasa a pesar dos tercios. El NAV publicado seguiría calculando con 50% y
    50%, que es la aritmética de una cartera rebalanceada a diario, gratis.
    """
    from src.run_pipeline import pesos_corridos
    precios = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-31", "2026-08-31", "2026-09-17", "2026-09-17"]),
        "alphadata_ticker": ["SUBE", "QUIETA", "SUBE", "QUIETA"],
        "adjusted_close": [100., 100., 200., 100.],
    })
    cartera = pd.DataFrame({"ticker": ["SUBE", "QUIETA"], "target_weight": [.5, .5]})
    r = pesos_corridos(cartera, precios, pd.Timestamp("2026-08-31"), pd.Timestamp("2026-09-17"))
    assert abs(float(r.iloc[0]) - 2 / 3) < 1e-9
    assert abs(float(r.iloc[1]) - 1 / 3) < 1e-9


def test_la_caja_no_se_mueve_al_correr_los_pesos():
    """Con la mitad en caja, una posición que duplica no llega al 100%."""
    from src.run_pipeline import pesos_corridos
    precios = pd.DataFrame({
        "date": pd.to_datetime(["2026-08-31", "2026-09-17"]),
        "alphadata_ticker": ["SUBE", "SUBE"],
        "adjusted_close": [100., 200.],
    })
    cartera = pd.DataFrame({"ticker": ["SUBE"], "target_weight": [.5]})
    r = pesos_corridos(cartera, precios, pd.Timestamp("2026-08-31"), pd.Timestamp("2026-09-17"))
    assert abs(float(r.iloc[0]) - 2 / 3) < 1e-9   # 1,0 sobre 1,0 + 0,5 de caja


def test_una_entrada_se_financia_con_el_producto_de_la_salida():
    """La pregunta que la política dejaba abierta.

    ILC subió y pesa 15% cuando sale; ANDINA-B entra en su lugar. Recibe el
    producto de la venta, no un octavo de la pieza: lo segundo obligaría a
    mover plata desde las sobrevivientes, que es el rebalanceo que la política
    descarta. Con tope en el peso de referencia, y lo que sobra a caja.
    """
    from src.nav_historico import _reasignar
    pesos = {"ILC": .15, "BCI": .13, "CHILE": .11}
    nuevos, caja = _reasignar(pesos, .61, {"ANDINA-B": .125, "BCI": .125, "CHILE": .125})
    assert nuevos["BCI"] == .13 and nuevos["CHILE"] == .11   # no se tocan
    assert nuevos["ANDINA-B"] == .125                        # topada en la referencia
    assert abs(caja - (1 - .13 - .11 - .125)) < 1e-12        # el resto queda en caja


def test_sin_salidas_ni_entradas_una_revision_no_mueve_nada():
    """Si nadie entra ni sale, la política no ordena ninguna operación."""
    from src.nav_historico import _reasignar
    pesos = {"BCI": .2, "CHILE": .1}
    nuevos, caja = _reasignar(pesos, .7, {"BCI": .125, "CHILE": .125})
    assert nuevos == pesos and abs(caja - .7) < 1e-12


def test_sigma6_exige_estar_sobre_la_sma200():
    """Era la única estrategia accionaria sin salida que mirara el precio de hoy.

    Su `Momentum12-1` salta las últimas 21 ruedas, así que una caída del último
    mes le era invisible. La condición viene encendida desde el 21-09-2026 y es
    también de permanencia: una acción con recomendación viva y momentum
    positivo se suelta igual si cae bajo su SMA200.
    """
    from src.strategy_engine import sigma6
    fechas = pd.bdate_range("2024-01-01", "2026-09-17")
    # Sube tres años y se desploma el último mes: el momentum 12-1 no lo ve.
    serie = pd.Series(range(100, 100 + len(fechas)), index=fechas, dtype=float)
    serie.iloc[-21:] = serie.iloc[-22] * .5
    precios = pd.DataFrame({"date": fechas, "alphadata_ticker": "CAE",
                            "adjusted_close": serie.to_numpy(), "close": serie.to_numpy(),
                            "volume": 1e6})
    recomendacion = pd.DataFrame([{"ticker": "CAE", "broker_normalized": "Credicorp Capital",
                                   "signal": 1, "row_number": 1,
                                   "available_at_parsed": pd.Timestamp("2026-09-01")}])
    as_of = pd.Timestamp("2026-09-17")
    con, _, _ = sigma6(recomendacion, precios, as_of, {"sigma_entries": {}})
    sin, _, _ = sigma6(recomendacion, precios, as_of, {"sigma_entries": {}}, exigir_sma200=False)
    assert "CAE" not in set(con.ticker), "la SMA200 tiene que soltarla"
    assert "CAE" in set(sin.ticker), "sin la condición, el momentum 12-1 no ve la caída"


def test_toda_serie_publicada_en_la_reconstruccion_se_recalcula():
    """El censo, como guardia: una serie guardada es la forma que ya falló.

    La de Sigma-6 sobrevivió intacta a la reparación de los precios chilenos,
    a la reconstrucción de los dividendos y a los cambios de metodología, y
    publicó +28,75% anual cuando el número era diez puntos menos. Agregar una
    columna al archivo sin recalcularla deja de ser posible en silencio.
    """
    from pathlib import Path
    from src.run_pipeline import SERIES_RECONSTRUIDAS
    archivo = Path(__file__).resolve().parents[1] / "data" / "reconstruccion_historica.csv"
    if not archivo.exists():
        pytest.skip("todavía no hay reconstrucción")
    columnas = set(pd.read_csv(archivo, nrows=1).columns) - {"date"}
    assert columnas <= SERIES_RECONSTRUIDAS, (
        f"series publicadas que nadie recalcula: {sorted(columnas - SERIES_RECONSTRUIDAS)}")


def test_sigma6_no_suelta_una_posicion_por_calendario():
    """El tope de 365 días salió: Sigma-6 rota por señal, no por calendario.

    Medido antes de quitarlo: nueve salidas por tope en el recorrido 2024-2026
    y las nueve reingresaban la semana siguiente, porque al soltarse el nombre
    desaparecía del contador y el reloj partía de cero. Dieciocho operaciones
    que no cambiaban la cartera.
    """
    import src.strategy_engine as motor
    from src.strategy_engine import sigma6
    assert not hasattr(motor, "TOPE_TENENCIA_SIGMA")
    fechas = pd.bdate_range("2023-01-02", "2026-09-17")
    serie = pd.Series(range(100, 100 + len(fechas)), index=fechas, dtype=float)
    precios = pd.DataFrame({"date": fechas, "alphadata_ticker": "VIEJA",
                            "adjusted_close": serie.to_numpy(), "close": serie.to_numpy(),
                            "volume": 1e6})
    recomendacion = pd.DataFrame([{"ticker": "VIEJA", "broker_normalized": "Credicorp Capital",
                                   "signal": 1, "row_number": 1,
                                   "available_at_parsed": pd.Timestamp("2026-09-01")}])
    # Tres años y medio en cartera: con el tope habría salido tres veces.
    estado = {"sigma_entries": {"VIEJA": "2023-01-02"}}
    cartera, _, _ = sigma6(recomendacion, precios, pd.Timestamp("2026-09-17"), estado)
    assert "VIEJA" in set(cartera.ticker)
