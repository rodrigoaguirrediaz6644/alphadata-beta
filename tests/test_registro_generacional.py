"""El registro AFP: que la grilla siga congelada y que la regla haga lo que dice.

**Una aclaracion, porque esta prueba se parece a lo que UN_VALOR_UNA_CASA.md
prohibe.** Ahi la norma dice que comparar una constante del codigo contra otra
constante escrita en la prueba no verifica nada. Es cierto, y `test_la_grilla_
sigue_congelada` hace exactamente eso — a proposito, y por otra razon.

No esta verificando que los numeros sean correctos: **esta impidiendo que
cambien en silencio.** Los parametros de este registro no se eligieron midiendo,
se eligieron despues de ver los datos, y el registro existe justamente para que
el tiempo decida entre ellos. Si alguien los ajusta a mitad de camino, el
registro deja de servir y nadie se entera. La prueba es el pestillo.

El resto de las pruebas si verifica comportamiento.
"""

import csv
import inspect

import pytest

from src import registro_generacional as r


# --------------------------------------------------------------------------
# el pestillo
# --------------------------------------------------------------------------

def test_la_grilla_sigue_congelada():
    """Si esto falla, alguien recalibro. Que sea un commit que lo diga fuerte."""
    assert r.BANDA == .02
    assert r.MEDIAS == (45, 64, 90, 105, 126)
    assert r.REZAGO == 4
    assert r.REFUGIOS == ("E", "D")
    assert r.AFP == "CUPRUM"
    assert r.CONGELADO == "2026-09-23"


def test_las_medias_estan_declaradas_en_dias_de_cotizacion():
    """La distincion que nos costo una discrepancia entera entre sesiones.

    `de_cotizacion` es lo que hace que MEDIAS signifique dias de rueda y no
    dias corridos. Si alguien la saca del camino, las mismas cifras pasan a
    significar una ventana 40% mas corta sin que cambie una sola constante.
    """
    assert "de_cotizacion" in inspect.getsource(r.construir)


# --------------------------------------------------------------------------
# la regla
# --------------------------------------------------------------------------

def test_solo_deja_los_dias_en_que_la_cuota_se_movio():
    filas = [("2026-01-01", {"A": 100., "D": 1., "E": 1.}),
             ("2026-01-02", {"A": 100., "D": 2., "E": 2.}),   # fin de semana
             ("2026-01-03", {"A": 101., "D": 3., "E": 3.})]
    assert [f for f, _ in r.de_cotizacion(filas)] == ["2026-01-01", "2026-01-03"]


def test_la_razon_es_none_hasta_que_la_media_existe():
    razones = r.razones([1., 2., 3., 4.], media=3)
    assert razones[0] is None and razones[1] is None
    assert razones[2] == pytest.approx(3 / 2 - 1)
    assert razones[3] == pytest.approx(4 / 3 - 1)


def test_la_histeresis_se_queda_quieta_entre_los_dos_umbrales():
    """Lo unico de toda esta linea que resulto ser mecanico y no afortunado.

    Cruzar la media no basta: hay que cruzarla por la banda. Los cruces de ida
    y vuelta alrededor de la linea dejan de contar, y eso es lo que baja la
    rotacion de ~7,5 a ~1,5 cambios al anio en las siete AFP.
    """
    # +1% no alcanza para nada; -1% tampoco. -3% saca; +1% no devuelve; +3% si.
    razones = [.01, -.01, -.03, -.01, .01, .03, .01]
    assert r.histeresis(razones, banda=.02) == [
        r.DENTRO, r.DENTRO, r.FUERA, r.FUERA, r.FUERA, r.DENTRO, r.DENTRO]


def test_la_histeresis_arranca_dentro_del_fondo_a():
    """La posicion por defecto es la de quien no hace nada."""
    assert r.histeresis([.0])[0] == r.DENTRO


def test_la_posicion_en_vigor_va_atrasada_el_rezago():
    senales = [r.DENTRO, r.FUERA, r.FUERA, r.DENTRO, r.DENTRO, r.FUERA]
    assert r.ejecutada(senales, rezago=2) == [
        None, None, r.DENTRO, r.FUERA, r.FUERA, r.DENTRO]


def test_la_senal_del_dia_no_se_puede_materializar_el_dia():
    """Con rezago 0 el registro mentiria, y el rezago congelado no es 0."""
    assert r.REZAGO > 0


# --------------------------------------------------------------------------
# el archivo
# --------------------------------------------------------------------------

def _serie(n=200, salto=None):
    """Serie sintetica: sube, y si `salto` opcionalmente se desploma ahi."""
    filas = []
    p = 100.
    for i in range(n):
        p *= .90 if salto is not None and salto <= i < salto + 10 else 1.001
        filas.append((f"2020-{1 + i // 28:02d}-{1 + i % 28:02d}",
                      {"A": p, "D": p * .5, "E": p * .25}))
    return filas


def test_construir_produce_una_fila_por_dia_de_cotizacion_con_todas_las_columnas():
    filas = r.construir(_serie(200))
    assert len(filas) == 200
    assert list(filas[0]) == r.columnas()
    for m in r.MEDIAS:
        assert filas[-1][f"senal_{m}"] in (r.DENTRO, r.FUERA)


def test_una_caida_saca_a_las_medias_cortas_antes_que_a_las_largas():
    """Es la unica diferencia real entre las cinco configuraciones registradas.

    Si no se cumpliera, registrar cinco medias no aportaria nada sobre una.
    """
    filas = r.construir(_serie(220, salto=180))
    ultima = filas[-1]
    fuera = [m for m in r.MEDIAS if ultima[f"senal_{m}"] == r.FUERA]
    assert min(r.MEDIAS) in fuera, "la media mas corta deberia haber salido"


def test_recalcular_dos_veces_da_lo_mismo():
    """El registro se reconstruye entero en cada corrida; tiene que ser estable."""
    serie = _serie(200)
    assert r.construir(serie) == r.construir(serie)


def test_se_niega_a_sobrescribir_si_la_fuente_reescribio_el_pasado():
    """Un registro hacia adelante cuyo pasado se reescribe solo no sirve de nada.

    Y peor: no se nota. Por eso `alteraciones` compara fila por fila contra lo
    ya commiteado en vez de confiar en que la fuente es inmutable.
    """
    viejo = r.construir(_serie(200))
    nuevo = [dict(f) for f in viejo]
    nuevo[50][f"senal_{r.MEDIAS[0]}"] = r.FUERA
    malas = r.alteraciones(viejo, nuevo)
    assert malas and nuevo[50]["fecha"] in malas[0]


def test_una_fila_que_desaparece_de_la_fuente_tambien_es_alteracion():
    viejo = r.construir(_serie(200))
    assert r.alteraciones(viejo, viejo[:-1])


def test_agregar_dias_al_final_no_es_alteracion():
    viejo = r.construir(_serie(200))
    nuevo = r.construir(_serie(210))
    assert r.alteraciones(viejo, nuevo) == []


def test_el_archivo_se_lee_igual_que_se_escribio(tmp_path):
    ruta = tmp_path / "afp_senales.csv"
    filas = r.construir(_serie(200))
    r.guardar(filas, ruta)
    assert r.leer(ruta) == filas
    with ruta.open(encoding="utf-8", newline="") as fh:
        assert next(csv.reader(fh)) == r.columnas()


# --------------------------------------------------------------------------
# el registro commiteado
# --------------------------------------------------------------------------

def test_el_registro_commiteado_tiene_la_forma_de_la_grilla_actual():
    """Si la grilla cambiara, el archivo viejo quedaria con otras columnas.

    Esta prueba lo agarra: obliga a que cambiar la grilla sea tambien reiniciar
    el registro, que es lo honesto, en vez de mezclar dos experimentos en un
    archivo.
    """
    filas = r.leer()
    if not filas:
        pytest.skip("todavia no hay registro commiteado")
    assert list(filas[0]) == r.columnas()
    fechas = [f["fecha"] for f in filas]
    assert fechas == sorted(fechas), "el registro tiene que estar ordenado"
    assert len(set(fechas)) == len(fechas), "hay fechas repetidas"


# --------------------------------------------------------------------------
# El peaje: la mitad del trato que no necesita una crisis
# --------------------------------------------------------------------------

def test_el_acumulado_arranca_en_el_congelamiento_y_no_antes():
    """Antes del congelamiento no hay nada que acumular: esa historia ya la vimos."""
    serie = _serie(300)
    congelado = serie[200][0]
    coti = r.de_cotizacion(serie)
    grilla = {m: (lambda x: (x, r.histeresis(x), r.ejecutada(r.histeresis(x))))(
        r.razones([v["A"] for _, v in coti], m)) for m in r.MEDIAS}
    acum = r.acumulados(coti, grilla, congelado=congelado)
    fechas = [f for f, _ in coti]
    corte = fechas.index(congelado)
    assert acum["acum_a"][corte] == ""
    assert acum["acum_a"][corte + 1] != ""


def test_el_acumulado_del_fondo_a_es_el_del_valor_cuota():
    """Sin trucos: si la columna no reproduce la cuota, no sirve de referencia."""
    serie = _serie(300)
    congelado = serie[200][0]
    coti = r.de_cotizacion(serie)
    acum = r.acumulados(coti, {m: (None, None, [None] * len(coti)) for m in r.MEDIAS},
                        congelado=congelado)
    esperado = coti[-1][1]["A"] / coti[200][1]["A"] - 1
    assert float(acum["acum_a"][-1]) == pytest.approx(esperado, abs=1e-6)


def test_una_configuracion_que_nunca_sale_iguala_al_fondo_a(monkeypatch):
    """Es el control: si difiere sin haberse movido, el calculo esta mal."""
    serie = _serie(400)                  # sube siempre, ninguna senal sale
    monkeypatch.setattr(r, "CONGELADO", serie[300][0])
    ultima = r.construir(serie)[-1]
    assert ultima["acum_a"]
    for m in r.MEDIAS:
        assert ultima[f"acum_{m}_e"] == ultima["acum_a"]


def test_el_congelamiento_tiene_una_sola_casa(monkeypatch):
    """Un valor por defecto captura la constante al definir la funcion.

    Eso le daria a CONGELADO dos casas que pueden discrepar, que es el defecto
    que UN_VALOR_UNA_CASA.md nombra. Lo encontre probando: el peaje salia vacio
    al mover la fecha.
    """
    coti = r.de_cotizacion(_serie(300))
    fechas = [f for f, _ in coti]
    monkeypatch.setattr(r, "CONGELADO", fechas[100])
    assert r._base(fechas) == 100
    assert r.acumulados(coti, {m: (None, None, [None] * len(coti))
                              for m in r.MEDIAS})["acum_a"][101] != ""


# --------------------------------------------------------------------------
# La votación: una instrucción, no cinco
# --------------------------------------------------------------------------

def test_la_votacion_tambien_esta_congelada():
    assert r.VOTOS_PARA_SALIR == 2
    assert r.REFUGIO == "E"
    assert r.SALTO_IMPOSIBLE == .08


def test_sale_al_refugio_con_dos_de_cinco_y_no_antes():
    assert r.posicion_por_voto(1) == r.DENTRO
    assert r.posicion_por_voto(2) == r.REFUGIO
    assert r.posicion_por_voto(5) == r.REFUGIO
    assert r.posicion_por_voto(None) is None


def test_el_refugio_de_la_votacion_no_esta_escrito_a_mano():
    """En abril de 2027 el nombre cambia y tiene que cambiar en un solo lugar."""
    assert r.posicion_por_voto(3, refugio="Consolidacion") == "Consolidacion"


def test_los_votos_salen_de_la_posicion_en_vigor_no_de_la_senal():
    """Lo que se vota es lo que se puede materializar."""
    n = 6
    grilla = {m: (None, None, [r.FUERA] * 2 + [r.DENTRO] * (n - 2)) for m in r.MEDIAS}
    assert r.votos(grilla, 0) == len(r.MEDIAS)
    assert r.votos(grilla, 5) == 0


def test_sin_todas_las_medias_no_hay_voto():
    grilla = {m: (None, None, [None]) for m in r.MEDIAS}
    assert r.votos(grilla, 0) is None


# --------------------------------------------------------------------------
# Las columnas de evento y el esquema
# --------------------------------------------------------------------------

def test_el_aviso_no_se_recalcula_se_arrastra():
    """Que salió un aviso es un hecho, no una función de la serie.

    Si se recalculara como todo lo demás, el historial de notificaciones se
    borraría solo cada día.
    """
    viejo = r.construir(_serie(200))
    viejo[-1]["aviso"] = "a E (1/3)"
    viejo[-1]["aviso_estado"] = "enviado"
    nuevo = r.arrastrar(viejo, r.construir(_serie(210)))
    igual = next(f for f in nuevo if f["fecha"] == viejo[-1]["fecha"])
    assert igual["aviso_estado"] == "enviado"


def test_un_aviso_distinto_no_cuenta_como_que_la_fuente_reescribio_el_pasado():
    """Son dos fallas distintas y confundirlas gastaría la alarma que importa."""
    viejo = r.construir(_serie(200))
    nuevo = [dict(f) for f in viejo]
    nuevo[50]["aviso_estado"] = "fallo"
    assert r.alteraciones(viejo, nuevo) == []


def test_agregar_una_columna_no_se_reporta_como_reescritura_de_la_fuente():
    viejo = [{c: "" for c in r.columnas() if c != "votos"} | {"fecha": f["fecha"]}
             for f in r.construir(_serie(200))]
    entran, salen = r.cambio_de_esquema(viejo)
    assert "votos" in entran and salen == []


# --------------------------------------------------------------------------
# La guardia del dato imposible
# --------------------------------------------------------------------------

def test_un_salto_imposible_del_fondo_agresivo_se_detecta():
    """Nunca pasó en 24 años. Si pasa, es dato malo antes que mercado."""
    filas = [{"fecha": "2026-01-01", "vc_a": "100.00"},
             {"fecha": "2026-01-02", "vc_a": "80.00"}]
    assert "se movio" in r.salto_imposible(filas)


def test_un_dia_malo_de_verdad_no_dispara_la_guardia():
    """El peor día del Fondo A en la historia está por debajo del límite."""
    filas = [{"fecha": "2026-01-01", "vc_a": "100.00"},
             {"fecha": "2026-01-02", "vc_a": "95.00"}]
    assert r.salto_imposible(filas) is None


def test_la_transicion_es_la_ultima_y_dice_desde_donde():
    filas = r.construir(_serie(200))
    for f in filas[:100]:
        f["posicion"] = "A"
    for f in filas[100:]:
        f["posicion"] = "E"
    assert r.transicion(filas) == (100, "A", "E")


def test_sin_cambios_no_hay_transicion():
    filas = r.construir(_serie(200))
    for f in filas:
        f["posicion"] = "A"
    assert r.transicion(filas) is None


# --------------------------------------------------------------------------
# lo que el informe publica: los últimos cambios y la evolución
# --------------------------------------------------------------------------

def _dia(fecha, a, e, posicion, fuera=None):
    """`fuera`: cuántas de las cinco señales indican refugio ese día; por defecto, las de `posicion`."""
    n = (2 if posicion == "E" else 0) if fuera is None else fuera
    fila = {"fecha": fecha, "vc_a": f"{a:.2f}", "vc_e": f"{e:.2f}", "vc_d": "100.00", "posicion": posicion}
    if posicion or n:
        from src.registro_generacional import FUERA, MEDIAS
        for i, m in enumerate(MEDIAS):
            fila[f"senal_{m}"] = FUERA if i < n else "A"
    return fila


# Las señales cambian una rueda antes que la posición en vigor (en el registro
# real, cuatro): 2021-06-30 y 2025-12-30 son los días de la recomendación, y
# 2021-07-01 y 2026-01-02 los de la posición en vigor.
HISTORIA = [
    _dia("2015-01-02", 100., 100., ""),                    # sin medias todavía: está en el A
    _dia("2021-06-29", 110., 101., "A"),
    _dia("2021-06-30", 120., 102., "A", fuera=2),          # las señales salen; el último día de hace cinco años o antes
    _dia("2021-07-01", 60., 103., "E"),                    # la posición en vigor llega: no se come la caída del A
    _dia("2025-12-30", 90., 110., "E", fuera=0),           # las señales vuelven; el último día de 2025
    _dia("2026-01-02", 180., 121., "A"),                   # la posición en vigor vuelve y toma la subida
    _dia("2026-06-30", 198., 110., "A"),
]


def test_los_cambios_son_los_de_la_recomendacion_y_salen_del_mas_nuevo_al_mas_viejo():
    from src.registro_generacional import CAMBIOS_EN_INFORME, cambios
    assert CAMBIOS_EN_INFORME == 4
    assert cambios(HISTORIA) == [("2025-12-30", "E", "A"), ("2021-06-30", "A", "E")]
    assert cambios(HISTORIA, cuantos=1) == [("2025-12-30", "E", "A")]
    assert cambios(HISTORIA[:2]) == []


def test_con_muchos_cambios_se_queda_con_los_ultimos_cuatro():
    from src.registro_generacional import cambios
    dias = [_dia(f"2020-{m:02d}-01", 100., 100., "E" if m % 2 else "A") for m in range(1, 11)]
    assert [f for f, _, _ in cambios(dias)] == ["2020-10-01", "2020-09-01", "2020-08-01", "2020-07-01"]


def test_la_senal_es_la_posicion_en_vigor_adelantada_por_el_rezago():
    """En el registro real: cada cambio de la posición llegó `REZAGO` ruedas después de la votación."""
    from src.registro_generacional import REZAGO, leer, posicion_de_la_senal
    filas = [f for f in leer() if f["posicion"]]
    senal = [posicion_de_la_senal(f) for f in filas]
    assert all(s is not None for s in senal)
    assert [f["posicion"] for f in filas[REZAGO:]] == senal[:-REZAGO]


def test_posicion_de_la_senal_vota_igual_que_la_regla():
    from src.registro_generacional import FUERA, MEDIAS, posicion_de_la_senal, VOTOS_PARA_SALIR
    def fila(n):
        return {f"senal_{m}": FUERA if i < n else "A" for i, m in enumerate(MEDIAS)}
    assert posicion_de_la_senal(fila(VOTOS_PARA_SALIR - 1)) == "A"
    assert posicion_de_la_senal(fila(VOTOS_PARA_SALIR)) == "E"
    assert posicion_de_la_senal({}) is None                     # sin medias todavía


def test_el_ultimo_cambio_de_la_senal_es_el_primero_de_la_lista():
    """Dos lugares decidiendo qué es un cambio terminarían discrepando sobre la fecha."""
    from src.registro_generacional import cambios, transicion, transicion_senal
    i, desde, hacia = transicion_senal(HISTORIA)
    assert cambios(HISTORIA)[0] == (HISTORIA[i]["fecha"], desde, hacia)
    # La posición en vigor cambia después, y esa es la que se valoriza.
    assert transicion(HISTORIA)[0] > i


def test_la_evolucion_mide_los_tres_periodos_desde_donde_corresponde():
    from src.registro_generacional import evolucion
    e = evolucion(HISTORIA)
    assert (e["hasta"], e["inicio_año"]) == ("2026-06-30", "2026-01-01")
    assert "inicio_historia" not in e
    filas = dict(e["filas"])
    assert list(filas) == ["Fondo A", "Fondo E", "Ahorro Generacional"]
    # El año, desde el 90 del 30-12-2025; los cinco años, desde el 120 del 30-06-2021;
    # los diez, desde el 100 del 02-01-2015, el último día de hace diez años o antes.
    assert filas["Fondo A"] == pytest.approx({"año": 198 / 90 - 1, "cinco_años": 198 / 120 - 1, "diez_años": .98})
    assert filas["Fondo E"] == pytest.approx({"año": 0., "cinco_años": 110 / 102 - 1, "diez_años": .10})


def test_la_regla_rinde_lo_del_fondo_en_que_esta_cada_dia():
    """Sobre la posición en vigor: la que habría quedado pidiendo el cambio el día de la recomendación."""
    from src.registro_generacional import evolucion
    regla = dict(evolucion(HISTORIA)["filas"])["Ahorro Generacional"]
    en_a_hasta_2021 = 120 / 100
    en_e = (103 / 102) * (110 / 103)
    en_a_desde_2026 = (180 / 90) * (198 / 180)
    assert regla["diez_años"] == pytest.approx(en_a_hasta_2021 * en_e * en_a_desde_2026 - 1)
    assert regla["cinco_años"] == pytest.approx(en_e * en_a_desde_2026 - 1)
    assert regla["año"] == pytest.approx(en_a_desde_2026 - 1)


def test_la_serie_del_grafico_parte_en_100_y_termina_en_lo_que_dice_la_tabla():
    """El número al final de cada línea y el de la columna salen del mismo dato."""
    from src.registro_generacional import evolucion
    e = evolucion(HISTORIA)
    serie = e["serie"]
    assert serie["fechas"][0] == "2015-01-02" and serie["fechas"][-1] == "2026-06-30"
    for nombre, r in e["filas"]:
        assert serie[nombre][0] == 100.
        assert serie[nombre][-1] == pytest.approx(100 * (1 + r["diez_años"]))


def test_sin_historia_suficiente_el_periodo_queda_vacio_y_no_inventado():
    from src.registro_generacional import evolucion
    corta = evolucion(HISTORIA[4:])
    filas = dict(corta["filas"])["Fondo A"]
    assert filas["cinco_años"] is None and filas["diez_años"] is None
    assert filas["año"] == pytest.approx(198 / 90 - 1)
    assert corta["serie"] is None
    assert evolucion(HISTORIA[:1]) is None


def test_el_informe_recibe_los_cambios_y_la_evolucion():
    from src.registro_generacional import MEDIAS, columnas, para_informe
    filas = [{c: "" for c in columnas()} | f for f in HISTORIA]
    g = para_informe(filas)
    assert g["cambios"][0] == ("2025-12-30", "E", "A")
    assert [n for n, _ in g["evolucion"]["filas"]] == ["Fondo A", "Fondo E", "Ahorro Generacional"]
    assert len(MEDIAS) == 5


def _informe(hasta):
    from src.registro_generacional import columnas, para_informe
    return para_informe([{c: "" for c in columnas()} | f for f in HISTORIA[:hasta]])


def test_sin_cambio_en_curso_la_recomendacion_es_la_posicion_en_vigor():
    g = _informe(4)                                   # hasta 2021-07-01: señales y posición ya en el refugio
    assert g["recomendado"] == "E" and g["recomendado_desde"] == "2021-06-30"
    assert g["cambio_en_curso"] is None
    g = _informe(7)                                   # hasta el final: de vuelta en el A
    assert g["recomendado"] == "A" and g["recomendado_desde"] == "2025-12-30" and g["cambio_en_curso"] is None


def test_hay_cambio_en_curso_cuando_las_senales_ya_cambiaron_y_la_posicion_en_vigor_todavia_no():
    g = _informe(3)                                   # hasta 2021-06-30: las señales salen, la posición sigue en el A
    assert g["recomendado"] == "E" and g["posicion"] == "A"
    assert g["cambio_en_curso"] == {"desde": "A", "hacia": "E", "fecha": "2021-06-30"}


def test_sin_medias_todavia_no_hay_recomendacion():
    g = _informe(1)
    assert g["recomendado"] is None and g["cambio_en_curso"] is None


def test_con_el_registro_real_el_cambio_en_curso_dura_el_rezago_y_lo_incluye_el_aviso():
    """En cada cambio real: en curso las `REZAGO` ruedas hasta que llega la posición en vigor, y el aviso cae dentro."""
    from src.aviso_generacional import pendiente
    from src.registro_generacional import REZAGO, _cambios_de, leer, para_informe, posicion_de_la_senal
    filas = leer()
    for k, _, hacia in _cambios_de(filas, posicion_de_la_senal)[-6:]:
        for j in range(REZAGO + 2):
            g = para_informe(filas[:k + 1 + j])
            assert (g["cambio_en_curso"] is not None) == (j < REZAGO), (filas[k]["fecha"], j)
            if pendiente(filas[:k + 1 + j]) is not None:
                assert g["cambio_en_curso"] is not None
        assert para_informe(filas[:k + 1])["cambio_en_curso"]["hacia"] == hacia
