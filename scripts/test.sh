#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

poetry run python -m unittest discover -s tests -v
poetry run python -m py_compile src/main.py src/gui.py
poetry check
