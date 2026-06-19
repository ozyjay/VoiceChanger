$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$env:PYTHONDONTWRITEBYTECODE = "1"

poetry run python -m unittest discover -s tests -v
poetry run python -c "from pathlib import Path; [compile(path.read_text(), str(path), 'exec') for path in sorted(Path('src').glob('*.py'))]"
poetry check
