"""Lectura de los archivos de referencia de investing.com.

Vienen en dos formatos según el idioma de la sesión desde la que se bajaron, y
hay que manejar los dos:

| | inglés | español |
|---|---|---|
| columnas | `Date, Price, Open, High, Low, Vol., Change %` | `Fecha, Último, Apertura, Máximo, Mínimo, Vol., % var.` |
| fecha | `09/17/2026` | `17.09.2026` |
| miles | coma | punto |
| decimal | punto | coma |
| nombre | `Salfacorp Stock Price History.csv` | `Datos históricos de Cap (CAP).csv` |

La trampa que ya costó una vez: leer con `thousands="."` convierte la fecha
`17.09.2026` en el entero `17092026` y deja la columna de fechas en `NaT` sin
que nada avise. Por eso se lee todo como texto y se convierte a mano.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

COLUMNAS = {
    "date": "date", "fecha": "date",
    "price": "close", "último": "close", "ultimo": "close",
    "open": "open", "apertura": "open",
    "high": "high", "máximo": "high", "maximo": "high",
    "low": "low", "mínimo": "low", "minimo": "low",
    "vol.": "volume", "vol": "volume",
}
MULTIPLICADOR = {"K": 1e3, "M": 1e6, "B": 1e9}

# Los archivos en inglés no llevan el ticker en el nombre.
NOMBRES_EN_INGLES = {
    "banco de chile (sn)": "CHILE",
    "banco de credito e inversiones": "BCI",
    "enel chile": "ENELCHILE",
    "engie energia chile": "ECL",
    "inv la constru": "ILC",
    "latam airlines": "LTM",
    "parq arauco": "PARAUCO",
    "plaza": "MALLPLAZA",
    "salfacorp": "SALFACORP",
    "santander chile": "BSANTANDER",
    "soquimich b": "SQM-B",
}


def ticker_de(ruta: str | Path) -> str | None:
    """Deduce el ticker AlphaData desde el nombre del archivo."""
    base = Path(ruta).stem
    entre_parentesis = re.search(r"\(([^)]+)\)\s*$", base)
    if entre_parentesis:
        return entre_parentesis.group(1).strip().upper()
    limpio = base.lower().replace(" stock price history", "").strip()
    return NOMBRES_EN_INGLES.get(limpio)


def _numero(texto: pd.Series, decimal_es_coma: bool) -> pd.Series:
    if decimal_es_coma:
        texto = texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        texto = texto.str.replace(",", "", regex=False)
    return pd.to_numeric(texto, errors="coerce")


def _volumen(texto: pd.Series, decimal_es_coma: bool) -> pd.Series:
    """'60,22K' y '28.95K' son el mismo volumen escrito en dos idiomas."""
    limpio = texto.fillna("").astype(str).str.strip().str.upper().replace({"-": "", "": None})
    sufijo = limpio.str.extract(r"([KMB])$", expand=False)
    cuerpo = limpio.str.replace(r"[KMB]$", "", regex=True)
    valores = _numero(cuerpo, decimal_es_coma)
    factor = sufijo.map(MULTIPLICADOR).fillna(1.0)
    return valores * factor


def leer(ruta: str | Path) -> pd.DataFrame:
    """Devuelve un panel con date, open, high, low, close y volume."""
    bruto = pd.read_csv(ruta, encoding="utf-8-sig", dtype=str)
    renombre = {c: COLUMNAS[c.strip().lower()] for c in bruto.columns if c.strip().lower() in COLUMNAS}
    datos = bruto.rename(columns=renombre)
    if "date" not in datos or "close" not in datos:
        raise ValueError(f"{Path(ruta).name}: no se reconocen las columnas de fecha y cierre")
    en_espanol = "Fecha" in bruto.columns
    fechas = pd.to_datetime(datos["date"], format="%d.%m.%Y" if en_espanol else "%m/%d/%Y", errors="coerce")
    salida = pd.DataFrame({"date": fechas})
    for columna in ["open", "high", "low", "close"]:
        salida[columna] = _numero(datos[columna], en_espanol) if columna in datos else pd.NA
    salida["volume"] = _volumen(datos["volume"], en_espanol) if "volume" in datos else pd.NA
    salida = salida.dropna(subset=["date", "close"]).sort_values("date")
    return salida.drop_duplicates("date", keep="last").reset_index(drop=True)


def serie(ruta: str | Path, columna: str = "close") -> pd.Series:
    """El cierre de un archivo, indexado por fecha."""
    panel = leer(ruta)
    return panel.set_index("date")[columna]
