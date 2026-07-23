$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$env:PYTHONDONTWRITEBYTECODE = "1"

function Invoke-CheckedNative {
    param(
        [scriptblock] $Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$compileSource = @'
from pathlib import Path

for path in sorted(Path("src").glob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
'@

Invoke-CheckedNative { poetry run python -m unittest discover -s tests -v }
Invoke-CheckedNative { $compileSource | poetry run python - }
Invoke-CheckedNative { poetry check }
