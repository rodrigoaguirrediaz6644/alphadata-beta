"""El aviso de cambio de fondo.

Lo que se prueba, en orden de cuánto duele que falle:

**Que mande al fondo correcto.** Un aviso que llega a tiempo y manda al fondo
equivocado es peor que no tener aviso. Es lo único que este correo tiene que
acertar y tiene prueba dedicada.

**Que las dos fechas sean distintas.** El día del envío manda; la del valor
cuota dice qué tan viejo es el dato. Las tuve confundidas y la fecha de
materialización salía del último día con dato.

**Que no falle callado**, y que el ensayo no se pueda confundir con uno real.
"""

import datetime as dt
import re

import pytest

from src import aviso_generacional as av
from src import registro_generacional as r


def _fila(fecha, posicion, fuera=(), **extra):
    f = {c: "" for c in r.columnas()}
    f.update(fecha=fecha, posicion=posicion, vc_a="99224.01", vc_e="65846.31",
             vc_d="57330.19")
    for m in r.MEDIAS:
        f[f"pos_{m}"] = r.FUERA if m in fuera else r.DENTRO
        f[f"razon_{m}"] = "-0.024" if m in fuera else "0.018"
    f["votos"] = str(len(fuera))
    f.update(extra)
    return f


def _historia(*pares):
    """(posición, medias que indican salir) por día hábil consecutivo."""
    d = dt.date(2026, 11, 2)
    filas = []
    for pos, fuera in pares:
        filas.append(_fila(d.isoformat(), pos, fuera))
        d += dt.timedelta(days=1 if d.weekday() < 4 else 3)
    return filas


def _salida():
    """La historia que importa: venía en el agresivo y hoy toca refugio."""
    return _historia(("A", ()), ("A", ()), ("E", (45, 64)))


# --------------------------------------------------------------------------
# LO ÚNICO QUE TIENE QUE ACERTAR: el fondo destino
# --------------------------------------------------------------------------

def test_una_transicion_real_manda_al_refugio_y_lo_dice_en_todas_partes():
    """La prueba que decide.

    No basta con que la línea de valores se vea bien: hay que ver el nombre
    del fondo destino en un aviso de salida de verdad.
    """
    a = av.pendiente(_salida())
    assert a["hacia"] == r.REFUGIO and a["desde"] == r.DENTRO
    assert av.asunto(a).startswith("Cambiar a Fondo E")
    assert "CAMBIAR A FONDO E" in av.texto(a)
    assert ">Cambiar a Fondo E</h1>" in av.html(a)


def test_los_dos_fondos_de_la_linea_de_valores_son_distintos():
    """Salían dos veces el mismo. Era el ensayo, pero la prueba va igual."""
    a = av.pendiente(_salida())
    assert a["cuota_a"] != a["cuota_destino"]
    for cuerpo in (av.texto(a), av.html(a)):
        assert "99.224,01" in cuerpo and "65.846,31" in cuerpo


def test_la_vuelta_al_agresivo_tambien_nombra_bien_el_destino():
    a = av.pendiente(_historia(("E", (45, 64)), ("E", (45, 64)), ("A", ())))
    assert a["hacia"] == r.DENTRO and "Cambiar a Fondo A" in av.html(a)


def test_el_nombre_del_fondo_sale_del_registro_y_no_del_codigo():
    """En abril de 2027 los multifondos desaparecen."""
    a = av.pendiente(_historia(("A", ()), ("Consolidacion", (45, 64))))
    assert "Fondo Consolidacion" in av.asunto(a)
    assert "Fondo Consolidacion" in av.html(a)


# --------------------------------------------------------------------------
# LAS DOS FECHAS
# --------------------------------------------------------------------------

def test_la_materializacion_sale_del_envio_y_no_del_ultimo_dia_con_dato():
    """Después de Fiestas Patrias el dato tiene seis días.

    Con la fecha vieja el aviso habría dicho «materializado el 23» cuando
    pidiéndolo ese día se materializa cerca del 29.
    """
    a = av.pendiente(_salida())
    assert a["fecha_envio"] == dt.date.today()
    assert a["fecha_dato"] != a["fecha_envio"]
    assert a["materializa"] == av.habiles_adelante(a["fecha_envio"])
    assert a["materializa"] > a["fecha_envio"]


def test_el_asunto_empieza_por_la_instruccion_y_no_por_el_nombre():
    """El nombre de la estrategia va en el cuerpo, donde hay espacio.

    El asunto existe para leerse en la pantalla bloqueada de un telefono, y
    «Ahorro Generacional:» se come veinte caracteres antes de decir nada util.
    Si hace falta distinguirlo de otros correos, que lo haga el remitente.
    """
    a = av.pendiente(_salida())
    assert av.asunto(a).startswith("Cambiar a ")
    for rotulo in ("AFP:", "Ahorro Generacional", "Horizonte"):
        assert rotulo not in av.asunto(a)
    # y el ensayo antepone solo su marca, que es lo unico que va antes
    assert av.asunto(av.ensayo(_historia(("A", ())))).startswith("[ENSAYO] Cambiar a ")


def test_el_nombre_de_la_estrategia_va_en_el_cuerpo():
    h = av.html(av.pendiente(_salida()))
    assert "Ahorro Generacional" in h


def test_el_asunto_lleva_la_fecha_del_envio():
    a = av.pendiente(_salida())
    assert dt.date.today().strftime("%d-%m-%Y") in av.asunto(a)


def test_se_ve_que_tan_viejo_es_el_dato():
    """Si tiene seis días, que se vea que tiene seis días."""
    a = av.pendiente(_salida())
    for cuerpo in (av.texto(a), av.html(a)):
        assert f"{a['dias_de_dato']} d" in cuerpo
        assert a["fecha_dato"].strftime("%d-%m-%Y") in cuerpo


def test_los_dias_habiles_saltan_el_fin_de_semana():
    assert av.habiles_adelante(dt.date(2026, 11, 5), 4) == dt.date(2026, 11, 11)


# --------------------------------------------------------------------------
# CUÁNDO DISPARA
# --------------------------------------------------------------------------

def test_dispara_en_la_transicion():
    assert av.pendiente(_salida()) is not None


def test_no_dispara_si_la_posicion_no_cambio():
    assert av.pendiente(_historia(("A", ()), ("A", ()), ("A", ()))) is None


def test_no_dispara_todos_los_dias_que_esta_en_refugio():
    filas = _historia(("A", ()), *[("E", (45, 64))] * 5)
    assert av.pendiente(filas) is None


def test_se_repite_tres_dias_y_despues_para():
    """Un correo se pierde; tres no."""
    base = [("A", ()), ("E", (45, 64))]
    for extra, esperado in [([], 1), ([("E", (45, 64))], 2), ([("E", (45, 64))] * 2, 3)]:
        assert av.pendiente(_historia(*base, *extra))["cual"] == esperado
    assert av.pendiente(_historia(*base, *[("E", (45, 64))] * 3)) is None


def test_no_avisa_dos_veces_por_el_mismo_dia():
    filas = _salida()
    filas[-1]["aviso_estado"] = "enviado"
    assert av.pendiente(filas) is None


def test_un_intento_fallido_no_bloquea_el_reintento():
    filas = _salida()
    filas[-1]["aviso_estado"] = "fallo"
    assert av.pendiente(filas) is not None


def test_dice_desde_cuando_venia_en_el_fondo_anterior():
    a = av.pendiente(_salida())
    assert a["desde_cuando"] == "2026-11-02"
    assert "02-11-2026" in av.texto(a)


# --------------------------------------------------------------------------
# LA FORMA
# --------------------------------------------------------------------------

def test_el_texto_plano_lleva_la_misma_instruccion_y_las_mismas_dos_fechas():
    """Hay clientes que no muestran HTML y el aviso no se puede perder por eso."""
    a = av.pendiente(_salida())
    t, h = av.texto(a), av.html(a)
    for dato in (a["fecha_envio"].strftime("%d-%m-%Y"),
                 a["fecha_dato"].strftime("%d-%m-%Y"),
                 av._largo(a["materializa"])):
        assert dato in t and dato in h
    assert "Fondo E" in t and "Fondo E" in h


def test_el_correo_no_depende_de_imagenes():
    """Se bloquean por defecto en la mitad de los clientes."""
    h = av.html(av.pendiente(_salida()))
    for prohibido in ("<img", "background-image", "<svg"):
        assert prohibido not in h


def test_cabe_en_un_telefono_sin_desplazar():
    h = av.html(av.pendiente(_salida()))
    assert 'name="viewport"' in h
    assert int(re.search(r"max-width:(\d+)px", h).group(1)) <= 640
    assert "@media(max-width:640px)" in h


def test_usa_la_tipografia_y_la_paleta_del_informe():
    """No un estilo nuevo: el aviso tiene que reconocerse como parte de lo mismo."""
    h = av.html(av.pendiente(_salida()))
    assert "-apple-system,Segoe UI,Arial,sans-serif" in h
    for color in ("#101828", "#475467", "#f2f4f7", "#eaecf0"):
        assert color in h


def test_las_medias_que_disparan_quedan_marcadas():
    h = av.html(av.pendiente(_salida()))
    assert h.count('class="sale"') == 2


def test_el_pie_explica_la_regla_dentro_de_un_ano():
    pie = av._pie(av.pendiente(_salida()))
    assert "45, 64, 90, 105, 126" in pie and "2%" in pie
    assert r.CONGELADO[:4] in pie          # el anio del congelamiento


def test_el_aviso_no_recomienda_nada():
    t = av.texto(av.pendiente(_salida())).lower()
    for palabra in ("conviene", "recomend", "urgente", "deberia"):
        assert palabra not in t


# --------------------------------------------------------------------------
# EL ENSAYO
# --------------------------------------------------------------------------

def test_el_ensayo_mueve_de_fondo_de_verdad():
    """El primero usaba la posición de hoy como destino y decía «Fondo A» dos
    veces: un ensayo que no se parece al aviso real no prueba lo que uno cree."""
    a = av.ensayo(_historia(("A", ())))
    assert a["hacia"] == r.REFUGIO
    assert a["cuota_a"] != a["cuota_destino"]


def test_el_ensayo_sale_al_otro_lado_tambien_desde_el_refugio():
    assert av.ensayo(_historia(("E", (45, 64))))["hacia"] == r.DENTRO


def test_el_ensayo_es_imposible_de_confundir_con_uno_real():
    a = av.ensayo(_historia(("A", ())))
    assert av.asunto(a).startswith("[ENSAYO]")
    assert av.texto(a).startswith("ESTO ES UN ENSAYO")


def test_la_franja_del_ensayo_va_antes_de_la_instruccion():
    """Si el aviso de que es ensayo aparece después, ya se leyó la instrucción."""
    h = av.html(av.ensayo(_historia(("A", ()))))
    assert h.index("Esto es un ensayo") < h.index("Cambiar a Fondo")


def test_un_aviso_real_no_lleva_franja_de_ensayo():
    """La clase existe siempre en el estilo; lo que no puede estar es la franja."""
    h = av.html(av.pendiente(_salida()))
    assert 'class="ensayo"' not in h
    assert "Esto es un ensayo" not in h


def test_el_ensayo_se_manda_cuando_no_hay_nada_que_avisar(monkeypatch):
    monkeypatch.setenv("SIMULAR_AVISO", "true")
    mandados = []
    ok, dicho = av.avisar(_historia(("A", ()), ("A", ())),
                          enviador=lambda a: (mandados.append(a), (True, "ok"))[1])
    assert ok and dicho == "ensayo enviado"
    assert mandados[0]["ensayo"] is True


def test_el_ensayo_no_marca_la_fila(monkeypatch):
    monkeypatch.setenv("SIMULAR_AVISO", "1")
    filas = _historia(("A", ()), ("A", ()))
    av.avisar(filas, enviador=lambda a: (True, "ok"))
    assert filas[-1]["aviso"] == "" and filas[-1]["aviso_estado"] == ""


# --------------------------------------------------------------------------
# CUANDO FALLA
# --------------------------------------------------------------------------

def test_si_el_correo_falla_queda_en_rojo_y_la_fila_lo_dice():
    filas = _salida()
    ok, dicho = av.avisar(filas, enviador=lambda a: (False, "SMTPAuthenticationError"))
    assert ok is False and "AVISO NO ENVIADO" in dicho
    assert filas[-1]["aviso_estado"] == "fallo" and filas[-1]["aviso"].startswith("a E")


def test_si_el_correo_sale_queda_anotado():
    filas = _salida()
    ok, _ = av.avisar(filas, enviador=lambda a: (True, "alguien@ejemplo.cl"))
    assert ok and filas[-1]["aviso_estado"] == "enviado"


def test_sin_secretos_no_finge_que_salio(monkeypatch):
    for s in av.SECRETOS:
        monkeypatch.delenv(s, raising=False)
    ok, detalle = av.enviar(av.pendiente(_salida()))
    assert ok is False and "faltan secretos" in detalle


def test_sin_transicion_no_toca_la_fila(monkeypatch):
    monkeypatch.delenv("SIMULAR_AVISO", raising=False)
    filas = _historia(("A", ()), ("A", ()))
    ok, dicho = av.avisar(filas, enviador=lambda a: pytest.fail("no debio enviar"))
    assert ok and dicho == "sin transicion pendiente"
    assert filas[-1]["aviso"] == ""


# --------------------------------------------------------------------------
# LO QUE GMAIL PUEDE ROMPER
# --------------------------------------------------------------------------

def test_los_estilos_van_inline_y_no_solo_en_un_bloque_style():
    """Varios clientes descartan el <style> entero.

    Si pasara, la tabla de las cinco medias se desarmaria en una columna de
    texto corrido, que es justo el bloque que hay que leer de un vistazo.
    """
    h = av.html(av.pendiente(_salida()))
    assert h.count('style="') >= 25
    for etiqueta in ("<table", "<td", "<th", "<body", "<h1"):
        i = h.index(etiqueta)
        assert 'style="' in h[i:i + 260], f"{etiqueta} sin estilo inline"


def test_cada_celda_lleva_fondo_y_color_propios():
    """Contra la inversion de modo oscuro: si el fondo se invierte y el texto
    no, queda gris claro sobre gris oscuro. Declarar los dos evita el caso."""
    h = av.html(av.pendiente(_salida()))
    celdas = re.findall(r'<td style="([^"]+)"', h)
    assert len(celdas) == 3 * len(r.MEDIAS)
    for c in celdas:
        assert "background:" in c and "color:" in c


def test_le_dice_al_cliente_que_no_invierta_los_colores():
    h = av.html(av.pendiente(_salida()))
    assert 'name="color-scheme" content="light only"' in h
    assert 'name="supported-color-schemes"' in h


def test_pesa_muy_por_debajo_de_donde_gmail_recorta():
    """Gmail corta con «[Mensaje recortado]» sobre 102 KB."""
    h = av.html(av.pendiente(_salida()))
    assert len(h.encode("utf-8")) < 102_400 / 4


def test_el_ensayo_no_anuncia_que_se_va_a_repetir():
    """La repeticion es para los avisos de verdad.

    Tres correos de prueba entrenan a ignorarlos, que es lo contrario de lo
    que se busca.
    """
    a = av.ensayo(_historia(("A", ())))
    assert "de 3" not in av.texto(a) and "de 3" not in av.html(a)


def test_un_aviso_real_si_dice_cual_de_los_tres_es():
    assert "Aviso 1 de 3" in av.html(av.pendiente(_salida()))
