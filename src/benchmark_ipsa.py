"""Lectura del MSCI IPSA Gross, el benchmark real del informe.

Reemplaza al proxy `CFMITNIPSA.SN`, que quedó congelado el 17-07-2026 junto con
el resto del feed chileno y que además arrastraba un salto de 100 a 212,56 por
el cambio de símbolo. Dejó de ser algo que reparar.

Se usa la variante **Gross** —con dividendos reinvertidos— porque el NAV de las
estrategias se calcula con precios ajustados: comparar un NAV con dividendos
contra un índice sin ellos subestima al mercado todos los años.

Sobre el formato: los archivos de investing.com vienen en formato europeo, con
punto de miles y coma decimal, y fechas dd.mm.aaaa. Leerlos con `thousands="."`
convierte la fecha 17.09.2026 en el número 17092026 y la columna de fechas
queda inservible sin que nada avise. Por eso se lee todo como texto y se
convierte a mano.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNA_FECHA = "Fecha"
COLUMNA_CIERRE = "Último"


def _numero(texto: pd.Series) -> pd.Series:
    """Convierte '11.381,18' en 11381.18."""
    return pd.to_numeric(texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")


def leer(ruta: str | Path, columna: str = COLUMNA_CIERRE) -> pd.Series:
    """Devuelve la serie diaria del índice, indexada por fecha y ordenada."""
    bruto = pd.read_csv(ruta, encoding="utf-8-sig", dtype=str)
    faltan = {COLUMNA_FECHA, columna}.difference(bruto.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el archivo del índice: {sorted(faltan)}")
    serie = pd.Series(
        _numero(bruto[columna]).to_numpy(),
        index=pd.to_datetime(bruto[COLUMNA_FECHA], format="%d.%m.%Y", errors="coerce"),
    )
    serie = serie[serie.index.notna()].dropna().sort_index()
    return serie[~serie.index.duplicated(keep="last")]


def en_base_100(serie: pd.Series, base: pd.Timestamp, fin: pd.Timestamp) -> float:
    """El índice reexpresado en base 100 a la fecha `base`, medido en `fin`.

    Ambos extremos toman la última rueda disponible en o antes de la fecha
    pedida. Alinear la base con la del NAV reconstruido no es un detalle:
    anclar un día más tarde descarta el retorno de mercado de esa jornada y
    favorece artificialmente a las estrategias.
    """
    inicio = serie.loc[:base]
    cierre = serie.loc[:fin]
    if inicio.empty or cierre.empty:
        raise ValueError("El índice no cubre la ventana pedida")
    return float(cierre.iloc[-1] / inicio.iloc[-1] * 100)
