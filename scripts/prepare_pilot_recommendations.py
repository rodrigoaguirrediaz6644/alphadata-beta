from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT.parent / "outputs" / "recomendaciones_ocr_brutas.csv"
OUTPUT = ROOT / "data" / "recommendations_pilot.csv"

SCORES = {
    "Comprar": 1,
    "Sobreponderar": 1,
    "Mantener": 0,
    "Neutral": 0,
    "Vender": -1,
    "Subponderar": -1,
    "Inferior al mercado": -1,
    "En Revisión": 0,
    "No disponible": 0,
}

BROKER_PATTERNS = [
    (r"credicorp capital", "Credicorp Capital"),
    (r"goldman sachs", "Goldman Sachs"),
    (r"morgan stanley", "Morgan Stanley"),
    (r"btg pactual", "BTG Pactual"),
    (r"barclays capital", "Barclays Capital"),
    (r"jpmorgan", "JPMorgan"),
    (r"banchile", "BANCHILE"),
    (r"larrainvial|estudios", "LarrainVial Estudios"),
    (r"bradesco", "BRADESCO"),
    (r"deutsche", "DEUTSCHE"),
    (r"scotia", "SCOTIA"),
    (r"renta4", "Renta4"),
    (r"jefferies", "Jefferies"),
    (r"(^|\s)citi(\s|$)", "Citi"),
    (r"(^|\s)bice(\s|$)", "BICE"),
    (r"(^|\s)bci(\s|$)", "BCI"),
    (r"(^|\s)mbi(\s|$)", "MBI"),
]


def parse_chilean_number(value: object) -> float | None:
    if pd.isna(value) or str(value).strip() in {"", "N/A"}:
        return None
    cleaned = str(value).strip().replace("%", "").replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def infer_pilot_ticker(row: pd.Series) -> str | None:
    ticker = str(row.get("ticker_ocr", "")).strip().upper()
    raw = str(row.get("texto_ocr_crudo", ""))
    raw_lower = raw.lower()

    if ticker in {"CENCOSUD", "FALABELLA", "SQM-B"}:
        if ticker == "SQM-B" and "adr" in raw_lower:
            return None
        return ticker
    if re.search(r"santander-chile|bsantander", raw_lower):
        return "BSANTANDER"
    if "adr" not in raw_lower and re.search(
        r"sociedad qu.mica.*minera|sqm.?b|sam-b|quimica y ?minera", raw_lower
    ):
        return "SQM-B"
    return None


def infer_broker(row: pd.Series) -> str | None:
    raw = str(row.get("texto_ocr_crudo", "")).lower()
    for pattern, broker in BROKER_PATTERNS:
        if re.search(pattern, raw):
            return broker
    normalized = str(row.get("corredora_normalizada", "")).strip()
    if normalized and normalized.lower() != "nan" and normalized != "SANTANDER":
        return normalized
    return None


def build(input_path: Path = DEFAULT_INPUT, output_path: Path = OUTPUT) -> pd.DataFrame:
    raw = pd.read_csv(input_path)
    raw["ticker"] = raw.apply(infer_pilot_ticker, axis=1)
    raw["broker_clean"] = raw.apply(infer_broker, axis=1)
    raw["date"] = pd.to_datetime(raw["fecha"], format="%d/%m/%Y", errors="coerce")
    raw["score"] = raw["recomendacion_normalizada"].map(SCORES)

    clean = raw.loc[
        raw["ticker"].notna()
        & raw["date"].notna()
        & raw["broker_clean"].notna()
        & raw["score"].notna()
    ].copy()
    clean["current_price_ocr"] = clean["precio_actual_ocr"].map(parse_chilean_number)
    clean["target_price_ocr"] = clean["precio_objetivo_nuevo_ocr"].map(parse_chilean_number)

    output = clean.rename(
        columns={
            "pagina_pdf": "source_page",
            "broker_clean": "broker",
            "recomendacion_normalizada": "recommendation",
            "texto_ocr_crudo": "raw_text",
        }
    )[
        [
            "source_page",
            "date",
            "ticker",
            "broker",
            "recommendation",
            "score",
            "current_price_ocr",
            "target_price_ocr",
            "raw_text",
        ]
    ]
    output = output.drop_duplicates(
        subset=["source_page", "date", "ticker", "broker", "recommendation", "target_price_ocr"]
    ).sort_values(["date", "ticker", "broker"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, date_format="%Y-%m-%d")
    return output


if __name__ == "__main__":
    result = build()
    print(f"Recomendaciones piloto: {len(result)}")
    print(result.groupby("ticker").size().to_string())
