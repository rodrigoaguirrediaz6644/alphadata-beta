"""El premio del CDV sobre su valor teorico, y lo que lo hace medible.

Lo que se prueba aca es sobre todo **el filtro**: sin el, la medicion no mide un
premio, mide que el precio del CDV esta rancio. El 96% de las ruedas repite el
cierre anterior y ABTCL estuvo 453 ruedas seguidas en el mismo precio.
"""

import pandas as pd
import pytest

from src.cdv import (BANDA, OPERABLE, RECHAZADO, SIN_SIMBOLO, SIN_VERIFICAR,
                     cdvs, estado, frescas, premio)
from src.salud import revisar


def _precios(fechas, usd, fx=1000.):
    filas = []
    for f, u in zip(fechas, usd):
        filas.append({"date": f, "alphadata_ticker": "ABT", "close": u})
        filas.append({"date": f, "alphadata_ticker": "USDCLP", "close": fx})
    return pd.DataFrame(filas).assign(date=lambda d: pd.to_datetime(d.date))


def _cdv(fechas, clp, volumen):
    return pd.DataFrame({"date": pd.to_datetime(list(fechas)), "cdv": "ABTCL.SN",
                         "subyacente": "ABT", "cdv_clp": list(clp), "volumen": list(volumen)})


FECHAS = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]


def test_un_precio_rancio_no_cuenta_aunque_tenga_volumen():
    """El volumen solo no alcanza: hay ruedas con volumen que repiten el cierre.

    Sin este filtro se estaria dividiendo un precio de hace semanas por un
    subyacente que si se movio, y el resultado mide el rancio y no el premio.
    """
    p = _precios(FECHAS, [100., 110., 120., 130.])
    c = _cdv(FECHAS, [100_000., 100_000., 100_000., 131_000.], [5, 5, 5, 5])
    f = frescas(c, p)
    assert list(f.date.dt.strftime("%Y-%m-%d")) == ["2026-01-08"]


def test_sin_volumen_tampoco_cuenta():
    p = _precios(FECHAS, [100., 110., 120., 130.])
    c = _cdv(FECHAS, [100_000., 111_000., 121_000., 131_000.], [0, 0, 0, 7])
    assert list(frescas(c, p).date.dt.strftime("%Y-%m-%d")) == ["2026-01-08"]


def test_el_premio_es_el_desvio_contra_el_subyacente_por_el_tipo_de_cambio():
    fechas = [f"2026-02-{d:02d}" for d in range(1, 41 + 1) if d <= 28] + \
             [f"2026-03-{d:02d}" for d in range(1, 13)]
    usd = [100. + i for i in range(len(fechas))]
    p = _precios(fechas, usd)
    # El CDV cotiza siempre 1% sobre su teorico, y siempre fresco.
    c = _cdv(fechas, [u * 1000. * 1.01 for u in usd], [3] * len(fechas))
    x = premio(c, p)
    assert x is not None
    assert x.medio == pytest.approx(.01, abs=1e-9)
    assert x.ruedas == len(fechas) - 1      # la primera no tiene rueda anterior


def test_con_pocas_ruedas_frescas_no_se_afirma_nada():
    """Es la diferencia entre no saber y decir cero."""
    p = _precios(FECHAS, [100., 110., 120., 130.])
    c = _cdv(FECHAS, [100_000., 111_000., 121_000., 131_000.], [1, 1, 1, 1])
    assert premio(c, p) is None


def test_una_razon_muy_lejos_de_uno_no_promedia_pero_si_se_conserva():
    """Asi se descubrio que el simbolo anotado para Bank of America era Boeing.

    BACL.SN cotizaba a 3,6 veces el teorico de BAC, de forma consistente. Eso no
    es un premio: es otra empresa.

    El recorte no puede vivir en `frescas`, porque las dos cosas que leen de ahi
    quieren lo contrario: para medir el premio un 3,6 es un dato roto que
    ensucia la media, y para la puerta de simbolos es **la evidencia**.
    Descartarlo ahi dejaba a la puerta sin con que rechazar.
    """
    largo = [f"2026-0{m}-{d:02d}" for m in (1, 2) for d in range(1, 16)]
    p = _precios(largo, [100. + i for i in range(len(largo))])
    c = _cdv(largo, [(100. + i) * 1000. * 3.6 for i in range(len(largo))], [3] * len(largo))
    assert len(frescas(c, p)) == len(largo) - 1      # se conservan
    assert premio(c, p) is None                      # y no promedian


def test_exxon_queda_fuera_en_vez_de_adivinarle_un_simbolo():
    u = pd.DataFrame([
        {"alphadata_ticker": "BAC", "tipo": "accion_us", "cdv_ticker": "BACCL"},
        {"alphadata_ticker": "XOM", "tipo": "accion_us", "cdv_ticker": None},
        {"alphadata_ticker": "IAU", "tipo": "etf_us", "cdv_ticker": "IAUCL"},
        {"alphadata_ticker": "BCI", "tipo": "accion_local", "cdv_ticker": None},
    ])
    assert cdvs(u) == {"BAC": "BACCL.SN", "IAU": "IAUCL.SN"}


def _revisar(premio_cdv):
    return revisar(as_of=pd.Timestamp("2026-09-18"), precios_al_dia=True, series_detenidas=set(),
                   cobertura_incompleta=set(), series_recalculadas={"A"}, series_publicadas={"A"},
                   carteras_reproducidas=True, dias_sin_recomendaciones=10, umbral_vigencia=90,
                   dividendos_sin_respaldo=set(), suite_verde=True, premio_cdv=premio_cdv)[0]


def test_el_panel_avisa_solo_si_el_premio_sale_de_la_banda():
    """Una alarma que suena por ruido deja de ser alarma.

    El premio medido tiene un error estandar de 0,05% sobre dos anios, asi que
    una banda estrecha sonaria sola todas las semanas.
    """
    class P:
        medio, error, ruedas, nombres = BANDA / 2, .0005, 700, 14
        distinguible, dentro_de_la_banda = True, True

    class Fuera(P):
        medio, dentro_de_la_banda = BANDA * 2, False

    fila = [c for c in _revisar(P()) if c.nombre == "Premio del CDV"][0]
    assert fila.sano
    fila = [c for c in _revisar(Fuera()) if c.nombre == "Premio del CDV"][0]
    assert not fila.sano and "fuera de la banda" in fila.detalle


def test_sin_medicion_el_panel_lo_dice_y_no_inventa_un_cero():
    fila = [c for c in _revisar(None) if c.nombre == "Premio del CDV"][0]
    assert fila.sano and "sin ruedas frescas suficientes" in fila.detalle


# --- La puerta de simbolos -------------------------------------------------

UNIVERSO = pd.DataFrame([
    {"alphadata_ticker": "BAC", "tipo": "accion_us", "cdv_ticker": "BACCL",
     "nombre": "Bank of America Corp. (CDV BACCL)"},
    {"alphadata_ticker": "ABT", "tipo": "accion_us", "cdv_ticker": "ABTCL",
     "nombre": "Abbott Laboratories (CDV ABTCL)"},
    {"alphadata_ticker": "XOM", "tipo": "accion_us", "cdv_ticker": "",
     "nombre": "Exxon Mobil Corp. (CDV sin confirmar)"},
])


def _serie(sub, simbolo, fechas, clp, volumen):
    return pd.DataFrame({"date": pd.to_datetime(list(fechas)), "cdv": simbolo,
                         "subyacente": sub, "cdv_clp": list(clp), "volumen": list(volumen)})


def _mercado(fechas, usd_por_sub, fx=1000.):
    filas = []
    for f in fechas:
        filas.append({"date": f, "alphadata_ticker": "USDCLP", "close": fx})
        for sub, u in usd_por_sub.items():
            filas.append({"date": f, "alphadata_ticker": sub, "close": u})
    return pd.DataFrame(filas).assign(date=lambda d: pd.to_datetime(d.date))


DIAS = [f"2026-0{m}-{d:02d}" for m in (1, 2) for d in range(1, 16)]


def _puerta(cdv, simbolos):
    return estado(UNIVERSO, cdv, _mercado(DIAS, {"BAC": 50., "ABT": 100.}),
                  pd.DataFrame(simbolos)).set_index("ticker")


def test_el_simbolo_de_otra_empresa_queda_fuera_aunque_su_serie_sea_impecable():
    """BA + CL = BACL, que es Boeing. BAC + CL = BACCL, que es Bank of America.

    El simbolo se arma pegando un sufijo a un ticker, y cuando un ticker es
    prefijo de otro la regla devuelve un instrumento **real** y equivocado: no
    falla con ruido, falla con una serie de precios perfectamente valida de
    otra empresa. Por eso duro dos anios.
    """
    # Una serie sana en todo salvo en el nivel: 3,6 veces su teorico.
    precios = [50. * 1000. * 3.6 + i for i in range(len(DIAS))]
    cdv = _serie("BAC", "BACL.SN", DIAS, precios, [9] * len(DIAS))
    p = _puerta(cdv, [{"cdv": "BACL.SN", "subyacente": "BAC",
                       "nombre_proveedor": "The Boeing Company"}])
    assert p.loc["BAC", "estado"] == RECHAZADO
    assert "Boeing" in p.loc["BAC", "motivo"]


def test_una_razon_imposible_rechaza_con_una_sola_rueda_fresca():
    """La red para cuando el proveedor no da el nombre: no depende de una fuente.

    Basta **una** rueda fresca, sin esperar a las diez, porque una razon de 3,5
    no es un premio ni un desfase de horario.
    """
    precios = [50. * 1000. * 3.5 + i for i in range(len(DIAS))]
    cdv = _serie("BAC", "BACL.SN", DIAS, precios, [6] * len(DIAS))
    p = _puerta(cdv, [{"cdv": "BACL.SN", "subyacente": "BAC", "nombre_proveedor": ""}])
    assert p.loc["BAC", "estado"] == RECHAZADO
    assert "otro instrumento" in p.loc["BAC", "motivo"]


def test_un_precio_congelado_no_puede_rechazar_a_nadie():
    """Esto estuvo mal y HONCL lo pago: se rechazo una posicion sana.

    La red se habia tendido sobre la razon mediana de **todas** las ruedas, con
    el argumento de que ninguna cantidad de rancio explica un numero grande. Es
    falso. HONCL tiene once precios distintos en 480 ruedas, y estar congelado
    mientras el subyacente se movia lo dejo con mediana 1,77 y maximo 2,08. Sus
    ruedas frescas dan 1,005.

    El tamanio del artefacto **no tiene techo**: lo fija cuanto se movio el
    subyacente durante el congelamiento. Por eso la razon solo se mide sobre
    ruedas frescas, nunca sobre el cierre exhibido.
    """
    # El CDV congelado en su precio inicial mientras el subyacente se duplica.
    mercado = _mercado(DIAS, {"BAC": 50., "ABT": 100.})
    congelado = _serie("ABT", "ABTCL.SN", DIAS, [100. * 1000. * 2.0] * len(DIAS), [7] * len(DIAS))
    p = estado(UNIVERSO, congelado, mercado,
               pd.DataFrame([{"cdv": "ABTCL.SN", "subyacente": "ABT",
                              "nombre_proveedor": "Abbott Laboratories"}])).set_index("ticker")
    assert p.loc["ABT", "estado"] == OPERABLE, "un precio congelado no es un instrumento equivocado"
    assert p.loc["ABT", "ruedas"] == 0


def test_sin_simbolo_no_se_opera_y_la_puerta_lo_dice_sola():
    """XOM es el caso vivo: si entra a Gamma-6 el mes que viene, esto lo detiene.

    La puerta no depende de que alguien se acuerde del nombre que entro este
    mes.
    """
    p = _puerta(pd.DataFrame(columns=["date", "cdv", "subyacente", "cdv_clp", "volumen"]), [])
    assert p.loc["XOM", "estado"] == SIN_SIMBOLO
    assert p.loc["XOM", "simbolo"] == ""


def test_un_nombre_sin_ruedas_frescas_pasa_por_el_proveedor_y_no_se_bloquea():
    """ABT no tiene **una sola** rueda fresca en dos anios, y su simbolo es correcto.

    Bloquearlo por no poder medirle la razon seria tratar «no se puede
    verificar» igual que «esta mal», que son cosas distintas. El nombre del
    proveedor es la verificacion de identidad; la razon verifica otra cosa
    —que sea uno a uno— y eso queda dicho en el motivo.
    """
    precios = [100. * 1000.] * len(DIAS)        # congelado: ninguna rueda fresca
    cdv = _serie("ABT", "ABTCL.SN", DIAS, precios, [4] * len(DIAS))
    p = _puerta(cdv, [{"cdv": "ABTCL.SN", "subyacente": "ABT",
                       "nombre_proveedor": "Abbott Laboratories"}])
    assert p.loc["ABT", "estado"] == OPERABLE
    assert p.loc["ABT", "ruedas"] == 0
    assert "uno a uno" in p.loc["ABT", "motivo"]


def test_sin_ruedas_frescas_y_sin_nombre_no_se_afirma_que_esta_bien():
    p = _puerta(pd.DataFrame(columns=["date", "cdv", "subyacente", "cdv_clp", "volumen"]),
                [{"cdv": "ABTCL.SN", "subyacente": "ABT", "nombre_proveedor": ""}])
    assert p.loc["ABT", "estado"] == SIN_VERIFICAR


def test_la_guia_no_imprime_simbolo_de_lo_que_no_paso_la_puerta():
    """Es el punto de toda la orden: que no haya nada que teclear."""
    from src.ingreso import cartera_de_ingreso, markdown as md
    puerta = pd.DataFrame([
        {"ticker": "BAC", "simbolo": "", "estado": RECHAZADO,
         "motivo": "el proveedor dice que BACL.SN es «The Boeing Company», no Bank of America Corp."},
        {"ticker": "ABT", "simbolo": "ABTCL.SN", "estado": OPERABLE, "motivo": "razón 1,0012"},
    ])
    cartera = pd.DataFrame([
        {"ticker": "BAC", "monto_clp": 1_250_000., "current_price": 55_000., "opened_at": "2026-08-01"},
        {"ticker": "ABT", "monto_clp": 1_250_000., "current_price": 98_000., "opened_at": "2026-08-01"},
    ])
    t = cartera_de_ingreso({"Gamma-6": cartera}, pd.Timestamp("2026-09-18"),
                           {"Gamma-6": (.001785, 999.99)}, simbolos=puerta)
    texto = md(t, pd.Timestamp("2026-09-18"))
    assert "ABTCL.SN" in texto
    assert "BACL.SN" not in texto.split("Lo que no se opera")[0]   # no en la tabla de compra
    assert "Lo que no se opera, y por qué" in texto
    assert "Boeing" in texto
