#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONDONTWRITEBYTECODE=1

poetry run python -m unittest discover -s tests -v
poetry run python - <<'PY'
from pathlib import Path

for path in sorted(Path("src").glob("*.py")):
    compile(path.read_text(), str(path), "exec")
PY
poetry check
