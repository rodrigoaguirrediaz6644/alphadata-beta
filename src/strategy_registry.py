from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class StrategyPlugin:
    code: str
    callable_path: str
    function: Callable


def load_registry(path: Path = ROOT / "config" / "runtime.v2.json") -> dict[str, StrategyPlugin]:
    config = json.loads(path.read_text(encoding="utf-8"))
    registry = {}
    for code in config["enabled_strategies"]:
        callable_path = config["strategy_modules"][code]
        module_name, function_name = callable_path.split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        registry[code] = StrategyPlugin(code, callable_path, function)
    return registry


def validate_registry() -> None:
    registry = load_registry()
    if not registry:
        raise ValueError("No existen estrategias habilitadas")
    for plugin in registry.values():
        if not callable(plugin.function):
            raise TypeError(f"{plugin.callable_path} no es ejecutable")


if __name__ == "__main__":
    validate_registry()
    print("Registro de estrategias válido")
