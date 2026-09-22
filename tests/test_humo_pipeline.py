"""La corrida completa llega al final. Nada mas, y no es poco.

Es lo mas grave que aparecio en todo el proyecto: **248 pruebas en verde con el
pipeline caido en dos sitios.** Quitar los valores por omision de la tarifa dejo
a `delta12_historical_nav` y a `sigma6_historical_nav` sin su argumento, la
corrida murio en la reconstruccion, y la suite siguio verde. «Verde» y
«funciona» eran dos afirmaciones distintas y nadie lo sabia.

Todas las demas pruebas llaman funciones sueltas con datos de juguete. Esta
llama **al pipeline**, con los datos de verdad, como lo llama produccion.

No verifica contenido a proposito: de eso se encargan las otras, que son
rapidas y precisas. Esta contesta una sola pregunta, la que ninguna contestaba.

Corre en un arbol copiado, asi que no toca nada del repositorio.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
# Lo que la corrida necesita leer. `reports` va porque escribe ahi.
ARBOL = ["src", "config", "data", "reports"]


@pytest.fixture(scope="module")
def corrida(tmp_path_factory):
    destino = tmp_path_factory.mktemp("humo")
    for parte in ARBOL:
        shutil.copytree(RAIZ / parte, destino / parte,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    entorno = {**os.environ, "PYTHONPATH": str(destino), "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run([sys.executable, "-W", "ignore", "-m", "src.run_pipeline"],
                             cwd=destino, env=entorno, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=900)
    return destino, proceso


def test_la_corrida_completa_termina_sin_reventar(corrida):
    destino, p = corrida
    assert p.returncode == 0, (
        "el pipeline no llego al final:\n"
        + "\n".join((p.stderr or "").strip().splitlines()[-25:]))


def test_la_corrida_produce_informe(corrida):
    """Que termine sin error no alcanza: tiene que haber escrito el informe."""
    destino, _ = corrida
    for archivo in ["reports/latest_report.md", "reports/latest_report.html",
                    "reports/cartera_de_ingreso.md"]:
        ruta = destino / archivo
        assert ruta.exists(), f"no se escribio {archivo}"
        assert len(ruta.read_text(encoding="utf-8")) > 500, f"{archivo} salio practicamente vacio"
