from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

import pandas as pd

from src.strategy_engine import RECOMMENDATION_COLUMNS, normalize_broker

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INBOX = DATA / "inbox"
ARCHIVE = DATA / "recommendations_archive"
HISTORY = DATA / "recommendations_history.csv"
CONSOLIDATED = DATA / "recommendations_input.csv"


def ingest() -> dict[str, int]:
    """Consolida archivos CSV subidos por el usuario sin borrar el historial."""
    INBOX.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    frames = []
    if HISTORY.exists():
        frames.append(pd.read_csv(HISTORY, dtype=str).fillna(""))
    elif CONSOLIDATED.exists():
        frames.append(pd.read_csv(CONSOLIDATED, dtype=str).fillna(""))
    files = sorted(INBOX.glob("*.csv"))
    for path in files:
        frame = pd.read_csv(path, dtype=str).fillna("")
        missing = set(RECOMMENDATION_COLUMNS).difference(frame.columns)
        if missing:
            raise ValueError(f"{path.name}: faltan columnas {sorted(missing)}")
        frame = frame[RECOMMENDATION_COLUMNS]
        frame["ingested_from"] = path.name
        frames.append(frame)
    if not frames:
        empty = pd.DataFrame(columns=RECOMMENDATION_COLUMNS)
        empty.to_csv(CONSOLIDATED, index=False)
        return {"uploaded_files": 0, "history_rows": 0}
    history = pd.concat(frames, ignore_index=True)
    for column in RECOMMENDATION_COLUMNS:
        if column not in history: history[column] = ""
    keys = ["published_at", "available_at", "broker", "ticker", "recommendation", "source_url"]
    history = history[history["broker"].map(normalize_broker).notna()].copy()
    history = history.drop_duplicates(keys, keep="last").sort_values(["published_at", "ticker"])
    history[RECOMMENDATION_COLUMNS].to_csv(HISTORY, index=False)
    history[RECOMMENDATION_COLUMNS].to_csv(CONSOLIDATED, index=False)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for path in files:
        shutil.move(str(path), ARCHIVE / f"{stamp}_{path.name}")
    return {"uploaded_files": len(files), "history_rows": len(history)}


if __name__ == "__main__":
    print(ingest())
