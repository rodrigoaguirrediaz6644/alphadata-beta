from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_module(module: str) -> None:
    subprocess.run([sys.executable, "-m", module], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatización AlphaData 2.0")
    parser.add_argument("command", choices=["run", "prices", "report", "send", "test"])
    parser.add_argument("--offline", action="store_true", help="Usar precios existentes sin descargar")
    args = parser.parse_args()
    if args.command == "test":
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)
        return
    if args.command in {"run", "prices"} and not args.offline:
        run_module("src.fetch_prices")
    if args.command in {"run", "report"}:
        run_module("src.run_pipeline")
    if args.command == "send":
        run_module("src.send_report")


if __name__ == "__main__":
    main()
