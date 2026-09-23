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

from src import registro_afp as r


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
