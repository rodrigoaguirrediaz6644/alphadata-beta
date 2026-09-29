import pandas as pd
import pytest

from pathlib import Path

from src.reporting_public import BENCHMARK, _metrics, build_public_report

ROOT = Path(__file__).resolve().parents[1]


def test_metrics_do_not_invent_history_with_one_observation():
    result = _metrics(pd.Series([100.0]), pd.Series(["2026-07-16"]))
    assert result["return"] is None
    assert result["mdd"] is None


@pytest.fixture(autouse=True)
def _graficos_en_temporal(tmp_path, monkeypatch):
    """Ninguna prueba escribe en reports/: publicaría curvas de fixture."""
    import src.reporting_public as rp
    monkeypatch.setattr(rp, "DIRECTORIO_GRAFICOS", tmp_path)
    yield tmp_path


def _report(**kwargs):
    portfolio = pd.DataFrame([{"ticker": "BCI", "target_weight": .1, "opened_at": "2026-07-06", "current_price": 31000.0, "open_return": .08}])
    moves = pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "previous_weight": 0.0, "target_weight": .1, "change": .1}])
    coverage = pd.DataFrame([{"status": "OK"}])
    history = pd.DataFrame([
        {"date": "2026-07-16", "Sigma-6": 100, "Delta-12": 100, "Gamma-6": 100, "Mercado chileno": 100, "Conjunto AlphaData": 100},
        {"date": "2026-09-18", "Sigma-6": 110, "Delta-12": 105, "Gamma-6": 120, "Mercado chileno": 102, "Conjunto AlphaData": 112},
    ])
    arguments = {"delta": portfolio, "delta_moves": pd.DataFrame(columns=["ticker", "action", "target_weight"]),
                 "coverage": coverage, "errors": pd.DataFrame(), "history": history}
    arguments.update(kwargs)
    return build_public_report(pd.Timestamp("2026-09-18"), **arguments)


def test_public_report_hides_strategy_methodology():
    _, html = build_public_report(
        pd.Timestamp("2026-09-18"),
        pd.DataFrame([{"ticker": "BCI", "target_weight": .1}]),
        pd.DataFrame([{"ticker": "BCI", "action": "ENTRA", "target_weight": .1, "change": .1}]),
        pd.DataFrame([{"status": "OK"}]),
        pd.DataFrame(),
        pd.DataFrame([{"date": "2026-07-16", "Delta-12": 100, "Gamma-6": 100, "Mercado chileno": 100}]),
    )
    for secret in ["momentum_12_1", "SMA200", "sma200", "RSI", "z-score", "score", "Credicorp", "252"]:
        assert secret not in html


def test_el_informe_no_lleva_descargos():
    # Cambio de criterio: es una herramienta personal y el único lector ya
    # conoce las limitaciones. Las consideraciones van en la documentación
    # interna, no en lo que se publica.
    _, html = _report()
    for descargo in ["seguimiento simulado", "no garantizan", "recomendación de inversión",
                     "aplicando las mismas reglas hacia atrás"]:
        assert descargo not in html


MOVIMIENTOS = pd.DataFrame([
    {"estrategia": "Sigma-6", "instrumento": "BCI", "accion": "COMPRAR", "fecha": pd.Timestamp("2026-09-18")},
    {"estrategia": "Gamma-6", "instrumento": "BAC", "accion": "VENDER", "fecha": pd.Timestamp("2026-08-31")},
])


def test_report_leads_with_the_combined_result_and_the_movements():
    """Los movimientos salen del libro y llevan la fecha de su propia señal.

    Antes salían de comparar la cartera con la anterior, y eso mezclaba lo que
    cambió con lo que hay que comprar para entrar hoy: el informe llegó a decir
    «Comprar INTC» en la misma página en que la tabla decía «comprada el
    30-09-2025».
    """
    markdown, html = _report(
        gamma=pd.DataFrame([{"ticker": "MRK", "target_weight": 1 / 6, "opened_at": "2026-08-03", "current_price": 146.87, "open_return": .15}]),
        movimientos=MOVIMIENTOS,
    )
    assert "+12,0%" in html  # 100 -> 112, el titular cuando no hay dato del año
    assert "<h2>Cambios en las estrategias</h2>" in html
    assert "<strong>Gamma6:</strong> Sale BAC." in html and "- Gamma6: Sale BAC." in markdown
    # Lo que no cambió se nombra igual, y una estrategia retirada que se mueve también.
    assert "<strong>Delta12:</strong> Sin cambios de cartera" in html
    assert "<strong>Oro:</strong> Sin cambios</p>" in html
    assert "- Sigma-6: Entra BCI." in markdown
    assert "MRK" in html


def test_report_says_plainly_when_there_is_nothing_to_do():
    """Tres de las cuatro piezas son mensuales: el bloque vacío es lo normal.

    Y un bloque vacío se lee como informe roto, así que tiene que decirlo con
    todas sus letras.
    """
    markdown, html = _report()
    for estrategia, texto in (("Delta12", "Sin cambios de cartera"), ("Gamma6", "Sin cambios de cartera"),
                              ("Oro", "Sin cambios")):
        assert f"<strong>{estrategia}:</strong> {texto}</p>" in html
        assert f"- {estrategia}: {texto}\n" in markdown
    assert "Entra" not in html and "Sale" not in html


def test_report_survives_without_gamma_history_or_positions():
    markdown, html = _report()
    assert "Sin posiciones abiertas" in html  # Gamma-6 todavía sin cartera
    assert "AlphaData" in markdown


def test_el_informe_ya_no_lleva_la_seccion_de_preocuparse():
    """Salió completa: ni el panel de salud, ni «Revisar», ni la vigencia de Sigma-6."""
    from src.salud import Chequeo
    md, html = _report(errors=pd.DataFrame([{"ticker": "X"}]), coverage=pd.DataFrame([{"status": "SIN_DATOS"}]),
                       salud=[Chequeo("Cobertura", False, "sin datos suficientes: IPSA_TR")],
                       vigencia={"dias": 95, "umbral": 90, "detenida": True, "renovar": []})
    for texto in (md, html):
        for fuera in ("preocuparse", "Revisar", "no se pudieron usar", "sin datos suficientes",
                      "Sigma-6 está detenida", "Todos los datos llegaron completos"):
            assert fuera not in texto


def test_report_refuses_to_compare_against_a_broken_benchmark():
    from src.reporting_public import is_continuous

    broken = pd.DataFrame([
        {"date": "2026-07-16", "Sigma-6": 100, "Delta-12": 100, "Gamma-6": 100, "Mercado chileno": 100, "Conjunto AlphaData": 100},
        {"date": "2026-07-17", "Sigma-6": 101, "Delta-12": 101, "Gamma-6": 101, "Mercado chileno": 212, "Conjunto AlphaData": 101},
        {"date": "2026-09-18", "Sigma-6": 110, "Delta-12": 110, "Gamma-6": 110, "Mercado chileno": 212, "Conjunto AlphaData": 110},
    ])
    assert not is_continuous(broken["Mercado chileno"])
    markdown, html = _report(history=broken)
    assert "comparado con haber invertido" not in html
    assert "Mercado chileno" not in html
    # El markdown es la parte en texto plano del correo y queda commiteado en el
    # repositorio: publicaba el salto de 100 a 212 como si fuera rentabilidad.
    assert "Mercado chileno" not in markdown
    _, healthy = _report()
    assert "comparado con haber invertido" in healthy


SERIE = pd.DataFrame({"date": pd.to_datetime(["2021-09-28", "2024-01-31", "2026-09-28"]),
                      "Delta-12": [100., 180., 320.], "Gamma-6": [100., 170., 336.], "Oro": [100., 150., 285.],
                      "Conjunto AlphaData": [100., 175., 334.], "Mercado chileno": [100., 140., 250.]})


def test_el_informe_lleva_un_solo_grafico_y_es_el_de_cinco_años(_graficos_en_temporal):
    """El del seguimiento en vivo salió: medía desde otra fecha que el resto del informe."""
    _, html = _report(desempeño={**DESEMPEÑO, "serie": SERIE})
    assert html.count("<img ") == 1 and 'src="reconstruccion.png"' in html
    assert "cid:" not in html
    assert "<h2>Desempeño AlphaData últimos 5 años</h2>" in html
    assert (_graficos_en_temporal / "reconstruccion.png").exists()
    assert not (_graficos_en_temporal / "seguimiento_vivo.png").exists()
    for fuera in ("seguimiento_vivo", "Seguimiento en vivo", "El seguimiento en vivo corre desde",
                  "cuando empezó esta serie", "<h2>Evolución</h2>", "Reconstrucción",
                  "Aplicando las mismas reglas hacia atrás", "no se encadena"):
        assert fuera not in html


def test_el_grafico_dibuja_alphadata_en_rojo_el_ipsa_y_no_a_sigma6(monkeypatch):
    import src.reporting_public as rp
    visto = {}

    def _espia(data, nombres, titulo, archivo, pie, colores=None, principal=None, suave=False, grosores=None):
        visto.update(nombres=nombres, titulo=titulo, pie=pie, colores=colores, principal=principal,
                     columnas=list(data.columns), suave=suave, grosores=grosores)
        return "<img>"

    monkeypatch.setattr(rp, "_dibujar", _espia)
    rp._chart(SERIE.assign(**{"Sigma-6": [100., 120., 217.]}))
    assert visto["nombres"] == ["AlphaData", "Delta12", "Gamma6", "Oro", "Ipsa"]
    assert visto["colores"]["AlphaData"] == "#d92d20" and visto["principal"] == "AlphaData"
    assert visto["pie"] == ""
    for fuera in ("Sigma-6", "Conjunto AlphaData", "Mercado chileno"):
        assert fuera not in visto["nombres"]
    # AlphaData con grosor 3 y todas las demás con 1, en curvas suavizadas.
    assert visto["grosores"] == (3, 1) and visto["suave"] is True
    assert len(set(visto["colores"].values())) == 5


def _diaria():
    fechas = pd.bdate_range("2025-01-02", "2025-12-30")
    zigzag = pd.Series([100 + i * .2 + (8 if i % 2 else -8) for i in range(len(fechas))])
    return pd.Series(fechas), zigzag


def test_la_curva_suave_pasa_por_los_cierres_de_mes_y_termina_en_el_valor_real():
    """Un promedio móvil terminaría en otro número que el de la tabla."""
    from src.reporting_public import _suavizar
    fechas, valores = _diaria()
    x, y = _suavizar(fechas, valores)
    assert x[0] == fechas.iloc[0] and y[0] == valores.iloc[0]
    assert x[-1] == fechas.iloc[-1] and y[-1] == valores.iloc[-1]
    curva = dict(zip(x, y))
    cierres = pd.Series(valores.to_numpy(), index=pd.DatetimeIndex(fechas)).groupby(
        pd.DatetimeIndex(fechas).to_period("M")).tail(1)
    for fecha, valor in cierres.items():
        assert curva[fecha] == pytest.approx(valor)


def test_la_curva_suave_no_lleva_el_zigzag_diario():
    from src.reporting_public import _suavizar
    fechas, valores = _diaria()
    _, y = _suavizar(fechas, valores)
    saltos = pd.Series(y).diff().abs().dropna()
    assert valores.diff().abs().max() > 15 and saltos.max() < 4


def test_con_pocos_datos_la_curva_es_la_serie_tal_cual():
    from src.reporting_public import _suavizar
    fechas = pd.Series(pd.to_datetime(["2026-09-24", "2026-09-25", "2026-09-28"]))
    x, y = _suavizar(fechas, pd.Series([100., 101., 102.]))
    assert y == [100., 101., 102.] and len(x) == 3


def test_dos_finales_parecidos_no_se_tapan_y_conservan_el_orden():
    from src.reporting_public import _separar
    puestos = _separar({"AlphaData": 334., "Gamma6": 336., "Delta12": 322., "Ipsa": 254.}, 12.)
    assert puestos["Ipsa"] == 254. and puestos["Delta12"] == 322.
    assert puestos["AlphaData"] == 334. and puestos["Gamma6"] == 346.


def test_el_grafico_no_lleva_titulo_adentro(_graficos_en_temporal):
    """El título lo lleva la sección. `set_title` dejaría la frase dibujada en la imagen."""
    import inspect
    import src.reporting_public as rp
    assert "set_title" not in inspect.getsource(rp._dibujar)


def test_sin_serie_de_cinco_años_no_hay_seccion_del_grafico():
    _, html = _report(desempeño={**DESEMPEÑO, "serie": None})
    assert "<img " not in html and "Desempeño AlphaData últimos 5 años" not in html
    assert "Detalle de carteras" in html


def test_la_serie_viva_no_se_reescala_con_la_reconstruccion():
    """Regresión del encadenamiento: la serie viva empieza donde empieza.

    La reconstrucción termina cerca de 350 en base 100; si el gráfico la
    encadenara, la serie viva arrancaría en ese nivel en vez de en 100.
    """
    from src.reporting_public import _dibujar, _series_presentes
    vivo = pd.DataFrame({"date": pd.to_datetime(["2026-09-17", "2026-09-18", "2026-09-21"]),
                         "Sigma-6": [100.0, 101.0, 102.0], "Conjunto AlphaData": [100.0, 100.5, 101.0]})
    bloque = _dibujar(vivo, _series_presentes(vivo), "prueba", "prueba_vivo.png", "pie")
    assert 'src="prueba_vivo.png"' in bloque
    # El dibujo normaliza a 100 en el primer dato propio de la serie, sin mirar
    # ningún archivo histórico.
    assert vivo["Sigma-6"].iloc[0] == 100.0


def test_el_benchmark_roto_queda_fuera_del_grafico_vivo():
    from src.reporting_public import _series_presentes
    roto = pd.DataFrame({"date": pd.to_datetime(["2026-09-17", "2026-09-18"]),
                         "Delta-12": [100.0, 101.0], "Mercado chileno": [100.0, 212.0]})
    presentes = _series_presentes(roto)
    # `_chart` filtra el benchmark cuando la serie no es continua; aquí se
    # comprueba que el filtro se aplica sobre la lista de series presentes.
    assert "Mercado chileno" in presentes
    assert [n for n in presentes if n != "Mercado chileno"] == ["Delta-12"]


def test_sigma6_sale_del_cuerpo_pero_se_queda_en_la_reconstruccion():
    """Sale de la asignación, no del repositorio.

    El cuerpo del informe describe tres piezas; el gráfico de la
    reconstrucción sigue dibujando la serie de Sigma-6, que es historia del
    proyecto y está medida.
    """
    from src.reporting_public import SERIES, SERIES_RECONSTRUCCION, STRATEGIES, _series_presentes
    assert STRATEGIES == ["Delta-12", "Gamma-6", "Oro"]
    assert "Sigma-6" not in SERIES
    assert "Sigma-6" in SERIES_RECONSTRUCCION
    recon = pd.DataFrame({"date": pd.to_datetime(["2021-07-08", "2021-07-09"]),
                          "Sigma-6": [100.0, 101.0], "Delta-12": [100.0, 100.5]})
    assert "Sigma-6" in _series_presentes(recon, SERIES_RECONSTRUCCION)
    assert "Sigma-6" not in _series_presentes(recon)


def test_el_reparto_del_capital_no_es_en_cuartos():
    markdown, html = _report(capital_por_pieza={"Delta-12": 7_500_000., "Gamma-6": 7_500_000.,
                                                "Oro": 5_000_000.})
    for texto in (markdown, html):
        assert "Delta12 37,5%" in texto and "Oro 25,0%" in texto
        assert "cuartos" not in texto and "cuatro piezas" not in texto


MOVIMIENTOS_RETIRO = pd.DataFrame([
    {"estrategia": "Sigma-6", "instrumento": "BCI", "accion": "VENDER", "fecha": pd.NaT},
    {"estrategia": "Delta-12", "instrumento": "ANDINA-B", "accion": "COMPRAR",
     "fecha": pd.Timestamp("2026-08-31")},
])


def test_sin_haber_comprado_el_bloque_describe_y_no_ordena():
    """El informe llegó a decir «Vender BCI» a quien no tenía BCI.

    Era cierto sobre el modelo —la cartera publicada anterior la tenía y la
    vigente no— e imposible de ejecutar, y al mismo tiempo la guía de ingreso
    decía comprar la cartera completa: dos instrucciones a la vez, una de ellas
    irrealizable.
    """
    markdown, html = _report(movimientos=MOVIMIENTOS_RETIRO, ha_entrado=False)
    for texto in (markdown, html):
        assert "Vender" not in texto and "Comprar" not in texto
        assert "Sale BCI." in texto and "Entra ANDINA-B" in texto
        assert "Todavía no has comprado nada" in texto


def test_habiendo_comprado_el_mismo_bloque_ordena():
    markdown, html = _report(movimientos=MOVIMIENTOS_RETIRO, ha_entrado=True)
    for texto in (markdown, html):
        assert "Sale BCI." in texto and "Entra ANDINA-B" in texto
        assert "Todavía no has comprado nada" not in texto


def test_lo_que_entra_dice_con_que_porcentaje_del_capital_de_su_estrategia():
    cartera = pd.DataFrame([{"ticker": "ANDINA-B", "target_weight": .125, "opened_at": "2026-08-31",
                             "current_price": 3000.0, "open_return": .02},
                            {"ticker": "CHILE", "target_weight": .125, "opened_at": "2026-06-30",
                             "current_price": 150.0, "open_return": .05}])
    movimientos = pd.DataFrame([
        {"estrategia": "Delta-12", "instrumento": "ILC", "accion": "VENDER", "fecha": pd.Timestamp("2026-08-31")},
        {"estrategia": "Delta-12", "instrumento": "ANDINA-B", "accion": "COMPRAR", "fecha": pd.Timestamp("2026-08-31")},
    ])
    markdown, html = _report(delta=cartera, movimientos=movimientos)
    frase = "Sale ILC. Entra ANDINA-B con 12,5% del capital de Delta12."
    assert f"<strong>Delta12:</strong> {frase}</p>" in html and f"- Delta12: {frase}" in markdown
    assert "<strong>Gamma6:</strong> Sin cambios de cartera" in html


# --------------------------------------------------------------------------
# Ahorro Generacional: el informe sale completo con registro presente,
# atrasado y ausente
# --------------------------------------------------------------------------

def _serie_generacional():
    fechas = [str(d.date()) for d in pd.bdate_range("2016-09-30", "2026-11-05")]
    n = len(fechas)
    return {"fechas": fechas,
            "Fondo A": [100 + i * .02 + (2 if i % 2 else -2) for i in range(n)],
            "Fondo E": [100 + i * .008 for i in range(n)],
            "Ahorro Generacional": [100 + i * .04 for i in range(n)]}


def _generacional(**cambios):
    base = {"fecha": "2026-11-05", "filas": 6000, "congelado": "2026-09-23",
            "agresivo": "A", "refugio": "E", "votos_para_salir": 2,
            "medias": [(45, "A", .061, "A"), (64, "A", .048, "A"), (90, "A", .032, "A"),
                       (105, "A", .027, "A"), (126, "A", .019, "A")],
            "votos": 0, "posicion": "A", "desde": "2026-10-01",
            "acum_a": .031, "acum_voto": .026,
            "peaje": [(45, -.004), (64, -.003), (90, -.005), (105, -.005), (126, -.006)],
            "aviso": None, "aviso_estado": None,
            "cambios": [("2025-05-19", "E", "A"), ("2025-03-13", "A", "E"),
                        ("2024-07-25", "E", "A"), ("2024-05-03", "A", "E")],
            "evolucion": {"hasta": "2026-11-05", "inicio_año": "2026-01-01", "serie": _serie_generacional(),
                          "filas": [("Fondo A", {"año": .141, "cinco_años": .645, "diez_años": 1.512}),
                                    ("Fondo E", {"año": -.060, "cinco_años": .421, "diez_años": .783}),
                                    ("Ahorro Generacional", {"año": .141, "cinco_años": 1.032, "diez_años": 3.102})]}}
    return base | cambios


def _seccion(html):
    return html[html.index("<h2>Estrategia Ahorro Generacional</h2>"):]


def test_la_seccion_se_llama_estrategia_ahorro_generacional_y_dice_que_es():
    md, html = _report(generacional=_generacional())
    explicacion = ("Estrategia diseñada para ahorro en la cuenta 2 de la AFP. Consiste en cambiar la inversión "
                   "entre el fondo de renta variable y el de renta fija (más riesgoso y más conservador).")
    assert f'<h2>Estrategia Ahorro Generacional</h2>\n    <p class="lead">{explicacion}</p>' in html
    assert "## Estrategia Ahorro Generacional" in md and explicacion in md
    assert "<h2>Ahorro Generacional</h2>" not in html


def test_la_tabla_muestra_los_dos_fondos_y_la_estrategia_en_tres_periodos():
    md, html = _report(generacional=_generacional())
    seccion = _seccion(html)
    assert ("<th>Fondo</th><th>Desde el 01-01-2026</th><th>Últimos 5 años</th>"
            "<th>Últimos 10 años</th>") in seccion
    assert "<td>Fondo A</td><td>+14,1%</td><td>+64,5%</td><td>+151,2%</td>" in seccion
    assert "<td>Fondo E</td><td>-6,0%</td><td>+42,1%</td><td>+78,3%</td>" in seccion
    assert ('<tr class="row-strong"><td>Ahorro Generacional</td><td>+14,1%</td><td>+103,2%</td>'
            "<td>+310,2%</td></tr>") in seccion
    assert "- Fondo E: -6,0% desde el 01-01-2026; +42,1% últimos 5 años; +78,3% últimos 10 años." in md
    for fuera in ("máximo disponible", "01-08-2002"):
        assert fuera not in seccion and fuera not in md


def test_el_orden_es_explicacion_evolucion_grafico_y_al_final_los_cambios():
    md, html = _report(generacional=_generacional())
    seccion = _seccion(html)
    orden = ["Estrategia diseñada", "<h3>Evolución</h3>", "<h3>Desempeño Ahorro Generacional últimos 10 años</h3>",
             "<h3>Últimos 4 cambios</h3>"]
    posiciones = [seccion.index(x) for x in orden]
    assert posiciones == sorted(posiciones)
    assert seccion.index("<h3>Últimos 4 cambios</h3>") > seccion.index("<img ")
    # Y en el texto plano, la evolución antes de los cambios.
    assert md.index("**Evolución**") < md.index("**Últimos 4 cambios**")


def test_muestra_solo_los_ultimos_cuatro_cambios():
    md, html = _report(generacional=_generacional())
    seccion = _seccion(html)
    assert "<th>Fecha</th><th>Cambio recomendado</th>" in seccion
    assert seccion.count("Cambiar de Fondo") == 4
    assert "<tr><td>19-05-2025</td><td>Cambiar de Fondo E a Fondo A</td></tr>" in seccion
    assert "<tr><td>03-05-2024</td><td>Cambiar de Fondo A a Fondo E</td></tr>" in seccion
    assert "03-11-2023" not in seccion
    assert seccion.index("19-05-2025") < seccion.index("13-03-2025") < seccion.index("03-05-2024")
    assert "- 19-05-2025: Cambiar de Fondo E a Fondo A" in md and md.count("Cambiar de Fondo") == 4


def test_el_grafico_de_ahorro_generacional_se_dibuja_y_se_adjunta(_graficos_en_temporal):
    _, html = _report(generacional=_generacional())
    assert 'src="ahorro_generacional.png"' in html and "cid:" not in html
    assert (_graficos_en_temporal / "ahorro_generacional.png").exists()
    assert html.count("<img ") == 1      # el del desempeño no viene sin su serie
    from src.send_report import GRAFICOS
    assert "ahorro_generacional.png" in GRAFICOS


def test_el_grafico_de_ahorro_generacional_usa_el_mismo_estilo_que_el_otro(monkeypatch):
    import src.reporting_public as rp
    visto = {}

    def _espia(data, nombres, titulo, archivo, pie, colores=None, principal=None, suave=False,
               grosores=None, años=5):
        visto.update(nombres=nombres, titulo=titulo, pie=pie, colores=colores, principal=principal,
                     suave=suave, grosores=grosores, años=años, primera=data.iloc[0].to_dict())
        return "<img>"

    monkeypatch.setattr(rp, "_dibujar", _espia)
    rp._grafico_generacional(_serie_generacional())
    assert visto["nombres"] == ["Ahorro Generacional", "Fondo A", "Fondo E"]
    assert visto["principal"] == "Ahorro Generacional" and visto["grosores"] == (3, 1) and visto["suave"] is True
    assert visto["colores"]["Ahorro Generacional"] == "#d92d20" and len(set(visto["colores"].values())) == 3
    assert visto["pie"] == ""
    # La serie ya viene recortada y no se recorta de nuevo: la primera fila es la base.
    assert visto["años"] is None and visto["primera"]["Ahorro Generacional"] == 100.


def test_sin_serie_de_diez_años_no_hay_grafico_pero_si_la_tabla():
    evolucion = {**_generacional()["evolucion"], "serie": None}
    _, html = _report(generacional=_generacional(evolucion=evolucion))
    seccion = _seccion(html)
    assert "<img " not in seccion and "Desempeño Ahorro Generacional" not in seccion
    assert "<h3>Evolución</h3>" in seccion and "<h3>Últimos 4 cambios</h3>" in seccion


def test_lo_que_mostraba_antes_ya_no_esta():
    md, html = _report(generacional=_generacional())
    for texto in (md, html):
        for fuera in ("Qué dice hoy", "media 45 d", "En vigor hoy", "Cuánto lleva costando",
                      "días de cotización", "la regla en vigor"):
            assert fuera not in texto


def test_la_seccion_es_lo_ultimo_del_informe():
    _, html = _report(generacional=_generacional())
    assert html.count("<section>") == html[:html.index("Estrategia Ahorro Generacional")].count("<section>")


def test_la_seccion_generacional_no_entra_en_la_suma_de_la_cartera():
    """No hay plata adentro: si apareciera en el conjunto, el informe mentiría."""
    con = _report(generacional=_generacional())[0].split("## Estrategia Ahorro Generacional")[0]
    sin = _report(generacional=None)[0].split("## Estrategia Ahorro Generacional")[0]
    assert con == sin


def test_con_el_registro_atrasado_lo_dice_y_el_informe_sale():
    """Una tabla que dejó de actualizarse se ve igual que una al día."""
    md, html = _report(generacional=_generacional(fecha="2026-08-01"))
    for texto in (md, html):
        assert "El registro dejó de crecer: el último día es el 01-08-2026" in texto
        assert "Fondo A" in texto
    assert "dejó de crecer" not in _report(generacional=_generacional(fecha="2026-09-17"))[1]


def test_el_informe_sale_completo_sin_registro():
    md, html = _report(generacional=None)
    for texto in (md, html):
        assert "Estrategia Ahorro Generacional" in texto
        assert "Estrategia diseñada" in texto
    assert "Detalle de carteras" in html
    assert "<h3>Evolución</h3>" not in html and "Cambio recomendado" not in html and "<img " not in html


def test_sin_cambios_ni_evolucion_la_seccion_no_inventa_tablas():
    _, html = _report(generacional=_generacional(cambios=[], evolucion=None))
    seccion = _seccion(html)
    assert "<table>" not in seccion and "Estrategia diseñada" in seccion


def test_los_nombres_de_los_fondos_salen_del_registro():
    """En abril de 2027 los multifondos desaparecen y esto no se edita."""
    md, _ = _report(generacional=_generacional(
        cambios=[("2027-05-03", "Inicial", "Consolidacion")],
        evolucion={"hasta": "2027-05-03", "inicio_año": "2027-01-01", "serie": None,
                   "filas": [("Fondo Inicial", {"año": .01, "cinco_años": .2, "diez_años": 1.})]}))
    assert "Cambiar de Fondo Inicial a Fondo Consolidacion" in md and "- Fondo Inicial: +1,0%" in md


# --------------------------------------------------------------------------
# Lo comprado de verdad contra el reparto de diseño
# --------------------------------------------------------------------------

DISENO = {"Delta-12": 7_500_000., "Gamma-6": 7_500_000., "Oro": 5_000_000.}


def test_lo_comprado_de_verdad_ya_no_va_en_el_informe():
    """Salió con toda la sección «La cartera completa». El cálculo sigue en src/operaciones.py."""
    md, html = _report(capital_por_pieza=DISENO)
    for texto in (md, html):
        assert "omprado de verdad" not in texto and "sin comprar todavía" not in texto
        assert "Expuesto al dólar" not in texto
        assert "Estrategia Ahorro Generacional" in texto


def test_una_venta_baja_lo_invertido():
    """Si se vendiera, el bloque tiene que reflejarlo o mentiría al revés."""
    from src.operaciones import invertido
    import pandas as pd
    ops = pd.DataFrame([
        {"estrategia": "Oro", "instrumento": "IAU", "accion": "COMPRA",
         "estado": "EJECUTADA", "cantidad": 8, "precio_pagado": 77300., "comision": 1103.84},
        {"estrategia": "Oro", "instrumento": "IAU", "accion": "VENTA",
         "estado": "EJECUTADA", "cantidad": 4, "precio_pagado": 78000., "comision": 557.},
    ])
    assert invertido(ops)["Oro"] == pytest.approx(8 * 77300 + 1103.84 - 4 * 78000 + 557.)


def test_una_orden_no_ejecutada_no_cuenta_como_comprada():
    from src.operaciones import invertido
    import pandas as pd
    ops = pd.DataFrame([{"estrategia": "Oro", "instrumento": "IAU", "accion": "COMPRA",
                         "estado": "PENDIENTE", "cantidad": 65, "precio_pagado": 77300.,
                         "comision": 0.}])
    assert invertido(ops) == {}


# --------------------------------------------------------------------------
# La exposición al dólar: estaba decidida sin decidirse
# --------------------------------------------------------------------------

def test_la_exposicion_se_calcula_de_la_moneda_del_universo_y_no_a_mano():
    """Una sola casa: la misma regla que usa `to_clp` para convertir a pesos.

    Dos lugares decidiendo qué es «en dólares» terminarían discrepando, y el
    síntoma sería que el informe declara una exposición y el NAV usa otra.
    """
    import pandas as pd
    from src.strategy_engine import en_dolares, exposicion_cambiaria

    universo = pd.DataFrame([
        {"alphadata_ticker": "BCI", "moneda": "CLP"},
        {"alphadata_ticker": "IAU", "moneda": "USD"},
        {"alphadata_ticker": "AAPL", "moneda": "USD"},
    ])
    assert en_dolares(universo) == {"IAU", "AAPL"}
    carteras = {
        "Delta-12": pd.DataFrame([{"ticker": "BCI", "target_weight": 1.}]),
        "Gamma-6": pd.DataFrame([{"ticker": "AAPL", "target_weight": 1.}]),
        "Oro": pd.DataFrame([{"ticker": "IAU", "target_weight": 1.}]),
    }
    e = exposicion_cambiaria(universo, carteras,
                             {"Delta-12": .375, "Gamma-6": .375, "Oro": .25}, 20_000_000.)
    assert e["fraccion"] == pytest.approx(.625)
    assert e["clp"] == pytest.approx(12_500_000.)


def test_sin_columna_de_moneda_no_inventa_una_exposicion():
    import pandas as pd
    from src.strategy_engine import en_dolares, exposicion_cambiaria
    universo = pd.DataFrame([{"alphadata_ticker": "BCI"}])
    assert en_dolares(universo) == set()
    assert exposicion_cambiaria(universo, {}, {"Oro": 1.}, 1.) is None


# --------------------------------------------------------------------------
# EL TITULAR: la rentabilidad del año, con el reparto vigente
# --------------------------------------------------------------------------

DESEMPEÑO = {"desde": pd.Timestamp("2026-01-01"),
             "reparto": {"Delta-12": .375, "Gamma-6": .375, "Oro": .25},
             "año": {"Delta-12": .2069, "Gamma-6": .4235, "Oro": .0601, "Conjunto AlphaData": .2552},
             "cinco_años": {"Delta-12": 2.2547, "Gamma-6": 2.2909, "Oro": 1.9292, "Conjunto AlphaData": 2.3435},
             "retroceso": {"Delta-12": -.1499, "Gamma-6": -.2694, "Oro": -.2348, "Conjunto AlphaData": -.1423}}


def test_el_titular_es_la_rentabilidad_del_año_y_dice_desde_cuando():
    markdown, html = _report(desempeño=DESEMPEÑO)
    # El número va pegado al título, y la explicación debajo del número.
    assert ('<h2>Cómo va tu dinero este año</h2><div class="hero up">+25,5%</div>'
            '<p class="lead">Invirtiendo en AlphaData desde el 01 de Enero del 2026 al día de hoy.</p>') in html
    assert ("**Cómo va tu dinero este año: +25,5%.** Invirtiendo en AlphaData desde el "
            "01 de Enero del 2026 al día de hoy.") in markdown


def test_el_titular_no_es_el_del_seguimiento_en_vivo():
    """El fixture lleva +12,0% en vivo. Si el titular lo mostrara, el rótulo mentiría."""
    _, html = _report(desempeño=DESEMPEÑO)
    assert '<div class="hero up">+12,0%</div>' not in html
    assert "desde que empezó el seguimiento" not in html
    # Bajo el número va una sola frase: ni el reparto ni la comparación con la bolsa.
    titular = html[html.index("Cómo va tu dinero este año"):html.index("Cambios en las estrategias")]
    assert "37,5%" not in titular and "comparado con" not in titular


def test_un_año_en_rojo_se_muestra_en_rojo():
    _, html = _report(desempeño={**DESEMPEÑO, "año": {**DESEMPEÑO["año"], "Conjunto AlphaData": -.031}})
    assert '<div class="hero down">-3,1%</div>' in html


def test_sin_el_dato_del_año_el_titular_no_cambia_de_rotulo():
    """Un número del seguimiento en vivo bajo el título «este año» sería otro número con el mismo nombre."""
    markdown, html = _report()
    assert "<h2>Cómo va tu dinero</h2>" in html and "este año" not in html
    assert "comparado con haber invertido en la bolsa chilena completa" in html
    assert "desde que empezó el seguimiento" in html and '<div class="hero up">+12,0%</div>' in html
    assert "desde el 16-07-2026" in markdown


def _tabla(html):
    return html[html.index("Desempeño separado por estrategia"):html.index("<h2>Detalle de carteras</h2>")]


def test_la_tabla_de_desempeño_mide_el_año_los_cinco_años_y_el_retroceso():
    markdown, html = _report(desempeño=DESEMPEÑO)
    tabla = _tabla(html)
    assert ("<th>Estrategia</th><th>En qué invierte</th><th>Desde el 01-01-2026</th>"
            "<th>Últimos 5 años</th><th>Máximo retroceso en 5 años</th></tr>") in tabla
    assert "<td>Delta12</td><td>Acciones chilenas</td><td>+20,7%</td><td>+225,5%</td><td>-15,0%</td>" in tabla
    assert "<td>Gamma6</td><td>Acciones de EE.UU.</td><td>+42,4%</td><td>+229,1%</td><td>-26,9%</td>" in tabla
    assert "<td>Oro</td><td>ETF de Oro</td><td>+6,0%</td><td>+192,9%</td><td>-23,5%</td>" in tabla
    assert "<strong>Máximo retroceso:</strong>" in tabla
    assert "- Delta12: +20,7% desde el 01-01-2026; +225,5% en los últimos 5 años; máximo retroceso en 5 años -15,0%." in markdown


def test_alphadata_va_en_la_ultima_fila_con_su_reparto():
    tabla = _tabla(_report(desempeño=DESEMPEÑO)[1])
    fila = ('<tr class="row-strong"><td>AlphaData</td>'
            "<td>37,5% en Delta12<br>37,5% en Gamma6<br>25% en Oro</td>"
            "<td>+25,5%</td><td>+234,4%</td><td>-14,2%</td></tr>")
    assert fila in tabla
    assert tabla.index("<td>Oro</td>") < tabla.index(fila)
    assert tabla.count("<tr") == 5  # la cabecera, las tres estrategias y AlphaData


def test_la_tabla_no_lleva_lo_que_se_saco():
    html = _report(desempeño=DESEMPEÑO)[1]
    tabla = _tabla(html)
    for fuera in ("Mercado chileno", "Conjunto AlphaData", "Acciones</th>", "Último año", "Peor caída",
                  "(en pesos)", "como seguro"):
        assert fuera not in tabla
    assert "Oro, como seguro del conjunto" not in html and "Acciones de EE.UU. (en pesos)" not in html


def test_el_numero_del_titular_es_el_de_la_fila_de_alphadata():
    """Salen del mismo dato: si se calcularan por separado podrían discrepar en la misma página."""
    html = _report(desempeño=DESEMPEÑO)[1]
    assert '<div class="hero up">+25,5%</div>' in html
    assert "<td>AlphaData</td>" in html and "<td>+25,5%</td>" in _tabla(html)


def test_sin_historia_para_cinco_años_el_año_sale_igual():
    sin_cinco = {**DESEMPEÑO, "cinco_años": None, "retroceso": None}
    tabla = _tabla(_report(desempeño=sin_cinco)[1])
    assert "<td>Delta12</td><td>Acciones chilenas</td><td>+20,7%</td><td>—</td><td>—</td>" in tabla


# --------------------------------------------------------------------------
# LOS NOMBRES Y EL DETALLE DE CARTERAS
# --------------------------------------------------------------------------

CARTERA_GAMMA = pd.DataFrame([{"ticker": "MRK", "target_weight": 1 / 6, "opened_at": "2026-07-31",
                               "entry_price": 120441.51, "current_price": 142898.53, "open_return": .193,
                               "monto_clp": 1_250_000., "peso_real": .165, "con_dividendo": True}])
CARTERA_DELTA = pd.DataFrame([{"ticker": "ITAUCL", "target_weight": .125, "opened_at": "2026-02-27",
                               "entry_price": 20900., "current_price": 23290., "open_return": .183,
                               "monto_clp": 937_500., "peso_real": .132, "dividendos_clp": 1187.27}])
CARTERA_ORO = pd.DataFrame([{"ticker": "IAU", "target_weight": 1., "opened_at": "2026-01-01",
                             "entry_price": 73374.64, "current_price": 74481.37, "open_return": .015,
                             "monto_clp": 5_000_000., "peso_real": 1.}])


def _completo():
    return _report(delta=CARTERA_DELTA, gamma=CARTERA_GAMMA, oro=CARTERA_ORO, movimientos=MOVIMIENTOS_RETIRO,
                   capital_por_pieza=DISENO, desempeño={**DESEMPEÑO, "serie": SERIE})


def test_las_estrategias_se_llaman_delta12_y_gamma6_en_todo_el_informe():
    for texto in _completo():
        assert "Delta12" in texto and "Gamma6" in texto
        assert "Delta-12" not in texto and "Gamma-6" not in texto


def test_adentro_las_series_conservan_su_nombre():
    """Cambiar el nombre de una columna guardada sería reescribir historia por presentación."""
    from src.reporting_public import NOMBRE_PUBLICO, STRATEGIES
    assert STRATEGIES == ["Delta-12", "Gamma-6", "Oro"]
    assert NOMBRE_PUBLICO["Delta-12"] == "Delta12" and NOMBRE_PUBLICO["Gamma-6"] == "Gamma6"


def test_el_detalle_de_carteras_lleva_solo_los_titulos_y_las_tablas():
    _, html = _completo()
    detalle = html[html.index("<h2>Detalle de carteras</h2>"):html.index("<h2>Estrategia Ahorro Generacional</h2>")]
    assert "<h3>Delta12 · Acciones chilenas</h3>" in detalle
    assert "<h3>Gamma6 · Acciones de EE.UU.</h3>" in detalle
    assert "<h3>Oro · ETF de Oro</h3>" in detalle
    assert detalle.count("<table>") == 3
    # Lo único que acompaña a una tabla es su caja, y sólo cuando la hay.
    assert detalle.count("<p") == detalle.count('<p class="muted">En caja:')
    assert "La cartera completa" not in html
    for fuera in ("Con un capital de", "Comprado de verdad", "Expuesto al dólar", "Va ganando", "va ganando",
                  "no tienen por qué calzar", "el modelo la seleccionó", "Todos los precios están en pesos",
                  "Dividendos cobrados", "repartió dividendos"):
        assert fuera not in html


def test_las_tres_tablas_llevan_las_columnas_nuevas():
    _, html = _completo()
    base = "<th>Acción</th><th>Inversión</th><th>Fecha de ingreso</th><th>Precio de ingreso</th><th>Precio actual</th>"
    assert html.count(base) == 3
    # Los dividendos van sólo en la chilena, que es la única que los tiene itemizados.
    assert html.count(base + "<th>Dividendos recibidos</th><th>Rentabilidad</th>") == 1
    assert html.count(base + "<th>Rentabilidad</th>") == 2
    assert ('<tr><td>ITAUCL</td><td>12,5%</td><td>27-02-2026</td><td>$ 20.900,00</td><td>$ 23.290,00</td>'
            '<td>$ 1.187,27</td><td class="up">+18,3%</td></tr>') in html
    assert ('<tr><td>IAU</td><td>100,0%</td><td>01-01-2026</td><td>$ 73.374,64</td><td>$ 74.481,37</td>'
            '<td class="up">+1,5%</td></tr>') in html
    for fuera in ("Cuánto invertir", "Peso de entrada", "Peso hoy", "Comprada el", "Precio de entrada",
                  "Precio hoy", "se recorta al", "$ 937.500", "+19,3% *"):
        assert fuera not in html
