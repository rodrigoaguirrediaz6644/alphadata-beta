"""Sobrescritura deliberada del tramo contaminado de la serie chilena.

    PYTHONPATH=. python -m tools.rellenar_hueco <carpeta>              # ensayo
    PYTHONPATH=. python -m tools.rellenar_hueco <carpeta> --confirmar  # escribe

**Esto no es parte del flujo normal y no debe serlo.** Vive fuera de `src/`
justamente por eso: la regla de sólo agregar vale porque no tiene excepciones
cómodas, y si el relleno fuera una bandera de la corrida habitual, en seis meses
alguien la usaría para tapar otra cosa. Es un comando de una sola vez.

## Qué repara

1. **El tramo congelado.** Desde el 17-07-2026 el proveedor repitió el mismo
   cierre durante dos meses.
2. **Las ventanas de caída ex-dividendo tardía.** En 2025 y 2026 la serie
   guardada se queda entre cinco y siete ruedas por encima del precio real
   alrededor de cada fecha ex, y después cae de golpe. Banco de Chile marcó
   +1,3% el 17-03-2025 cuando el movimiento real fue -6,2%.

Los dos defectos están dentro del rango que cubren los archivos de referencia,
así que se reparan en la misma pasada y con el mismo criterio: donde el archivo
validado discrepa, manda el archivo.

## Las condiciones que cumple

- **La fuente se valida antes de escribir nada.** Cada archivo se compara
  contra lo guardado en la ventana limpia anterior a la contaminación. Si no da
  razón mediana 1,0 con la coincidencia y el desvío exigidos, ese instrumento
  se salta entero.
- **La ventana se decide por instrumento, no por una fecha global.** Se
  sobrescribe cada rueda en que el archivo discrepa de lo guardado, sin
  suponer que todos se congelaron el mismo día.
- **Cada fila sobrescrita queda registrada** con su valor viejo y su valor
  nuevo en `data/relleno_sobrescrituras.csv`, que se commitea. Es historia
  oficial reescribiéndose y tiene que poder auditarse después.

## El cierre ajustado

Las estrategias corren sobre `adjusted_close`, que lleva los factores de
dividendo: en 2025-2026 va de 0,85 a 1,0 según el instrumento. Los archivos sólo
traen el crudo, así que escribir el crudo en esa columna rompería la serie. Se
conserva el factor de cada fila guardada —`adjusted_close / close`— y se aplica
al cierre nuevo. En la ventana del relleno ese factor es 1,0 en todos los
instrumentos, porque el último dividendo es anterior; en las reparaciones de
2025 no lo es, y ahí arrastrarlo es lo que evita borrar los dividendos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.feed_validation import aprueba, comparar
from src.fetch_prices import PRICE_COLUMNS, load_universe
from src.referencia_investing import leer, ticker_de

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
# La comparación se hace sobre el tramo limpio: desde que empiezan los archivos
# hasta la víspera del congelamiento.
VALIDAR_DESDE = pd.Timestamp("2025-01-01")
VALIDAR_HASTA = pd.Timestamp("2026-07-16")
TOLERANCIA = .001  # por debajo de esto es redondeo entre proveedores, no un defecto
# La validación aquí exige razón mediana 1 y coincidencia exacta en la gran
# mayoría de los días, pero **no** acota el desvío de los días que no calzan,
# como sí hace la selección de proveedor. La razón es que esos desvíos son
# precisamente los defectos que este comando viene a reparar: IAM y VAPORES
# quedaban fuera con el umbral de 1,2% por tener ventanas ex-dividendo más
# grandes —VAPORES llega a 15%— es decir, por estar más rotos, no por ser
# peores archivos. Lo que descalifica a un archivo es otra convención de
# cierre, y eso lo detecta la mediana.
MINIMO_EXACTOS = .90
SIN_LIMITE_DE_DESVIO = 1.0
REGISTRO = DATA / "relleno_sobrescrituras.csv"


def _factores(guardado: pd.DataFrame) -> pd.Series:
    """El factor de ajuste por dividendo de cada fila, arrastrado hacia adelante."""
    factor = pd.to_numeric(guardado.adjusted_close, errors="coerce") / pd.to_numeric(guardado.close, errors="coerce")
    return factor.where(factor.notna() & (factor > 0)).ffill().fillna(1.0)


def planificar(archivo: Path, guardado: pd.DataFrame, universo: set[str],
               tolerancia: float = TOLERANCIA) -> tuple[str | None, pd.DataFrame, dict]:
    """Decide qué filas de un instrumento hay que escribir, y por qué."""
    ticker = ticker_de(archivo)
    informe = {"archivo": archivo.name, "ticker": ticker}
    if ticker is None or ticker not in universo:
        informe["motivo"] = "el ticker no está en el universo"
        return None, pd.DataFrame(), informe

    # Sólo se escribe desde donde los archivos están validados. SALFACORP trae
    # historia desde 2021 y en ese tramo viene ajustada por dividendos: escribirla
    # como cruda inyectaría un desnivel de hasta 18% en 2021-2024, que es
    # justamente el backtest que se decidió no tocar.
    referencia = leer(archivo).set_index("date")
    referencia = referencia.loc[referencia.index >= VALIDAR_DESDE]
    propio = guardado.loc[guardado.alphadata_ticker == ticker].set_index("date").sort_index()
    if propio.empty:
        informe["motivo"] = "no hay serie guardada contra la cual validar"
        return None, pd.DataFrame(), informe

    medida = comparar(referencia["close"], propio["close"], desde=VALIDAR_DESDE, hasta=VALIDAR_HASTA)
    informe.update({"dias_validados": medida["dias"], "razon_mediana": medida["razon_mediana"],
                    "exactos": medida["exactos"], "desvio_p95": medida["desvio_p95"]})
    if not aprueba(medida, minimo_exactos=MINIMO_EXACTOS, maximo_desvio_p95=SIN_LIMITE_DE_DESVIO):
        informe["motivo"] = "el archivo no pasa la validación contra el tramo limpio"
        return None, pd.DataFrame(), informe

    factor = _factores(propio)
    simbolo = propio["yahoo_ticker"].dropna().iloc[-1] if propio["yahoo_ticker"].notna().any() else ""
    filas = []
    for fecha, nueva in referencia.iterrows():
        vieja = propio.loc[fecha] if fecha in propio.index else None
        if vieja is not None:
            anterior = pd.to_numeric(pd.Series([vieja["close"]]), errors="coerce").iloc[0]
            if pd.notna(anterior) and anterior > 0 and abs(nueva["close"] / anterior - 1) <= tolerancia:
                continue  # coinciden: no se toca
            accion, previo = "sobrescribe", float(anterior) if pd.notna(anterior) else None
            ajuste = float(factor.loc[fecha])
        else:
            accion, previo = "agrega", None
            previos = factor.loc[factor.index < fecha]
            ajuste = float(previos.iloc[-1]) if len(previos) else 1.0
        filas.append({"date": fecha, "alphadata_ticker": ticker, "yahoo_ticker": simbolo,
                      "open": nueva.get("open"), "high": nueva.get("high"), "low": nueva.get("low"),
                      "close": float(nueva["close"]), "adjusted_close": float(nueva["close"]) * ajuste,
                      "volume": nueva.get("volume"), "accion": accion, "close_anterior": previo})
    informe["motivo"] = "validado"
    return ticker, pd.DataFrame(filas), informe


def main(carpeta: str, confirmar: bool = False) -> int:
    universo = set(load_universe().alphadata_ticker)
    ruta = DATA / "market_prices_daily.csv"
    guardado = pd.read_csv(ruta, parse_dates=["date"])
    archivos = sorted(Path(carpeta).glob("*.csv"))
    if not archivos:
        print(f"No hay archivos en {carpeta}")
        return 1

    planes, informes, saltados = [], [], []
    for archivo in archivos:
        ticker, plan, informe = planificar(archivo, guardado, universo)
        informes.append(informe)
        if ticker is None:
            saltados.append(informe)
            continue
        planes.append(plan)

    print(f"{'ticker':<12}{'validado':>10}{'mediana':>10}{'exactos':>9}{'sobrescribe':>13}{'agrega':>8}")
    total_sobre = total_agrega = 0
    for plan in planes:
        if plan.empty:
            continue
        t = plan.alphadata_ticker.iloc[0]
        info = next(i for i in informes if i.get("ticker") == t)
        sobre = int((plan.accion == "sobrescribe").sum()); agrega = int((plan.accion == "agrega").sum())
        total_sobre += sobre; total_agrega += agrega
        print(f"{t:<12}{info['dias_validados']:>10}{info['razon_mediana']:>10.6f}{info['exactos']:>9.1%}{sobre:>13}{agrega:>8}")
    for informe in saltados:
        print(f"{str(informe.get('ticker') or informe['archivo'][:11]):<12}  SALTADO — {informe['motivo']}")
    print()
    print(f"Instrumentos validados: {len(planes)} de {len(archivos)}. "
          f"Filas a sobrescribir: {total_sobre}. Filas a agregar: {total_agrega}.")

    if not planes:
        return 1
    cambios = pd.concat(planes, ignore_index=True)
    if not confirmar:
        print("\nEnsayo: no se escribió nada. Repetir con --confirmar para aplicar.")
        return 0

    registro = cambios.loc[cambios.accion == "sobrescribe",
                           ["alphadata_ticker", "date", "close_anterior", "close"]].rename(
        columns={"close_anterior": "valor_anterior", "close": "valor_nuevo"})
    nuevas = cambios[PRICE_COLUMNS].copy()
    clave = ["alphadata_ticker", "date"]
    resto = guardado.merge(nuevas[clave].assign(_tocada=1), on=clave, how="left")
    resto = resto.loc[resto._tocada.isna(), PRICE_COLUMNS]
    resultado = pd.concat([resto, nuevas], ignore_index=True).sort_values(["date", "alphadata_ticker"])
    resultado.to_csv(ruta, index=False, date_format="%Y-%m-%d")
    registro.sort_values(["alphadata_ticker", "date"]).to_csv(REGISTRO, index=False, date_format="%Y-%m-%d")
    print(f"\nEscrito. {len(registro)} filas sobrescritas quedaron registradas en {REGISTRO.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    raise SystemExit(main(argumentos[0] if argumentos else "", "--confirmar" in sys.argv))
