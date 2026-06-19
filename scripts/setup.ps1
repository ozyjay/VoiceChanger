$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (Get-Command pyenv -ErrorAction SilentlyContinue) {
    $pythonVersion = Get-Content -Raw -LiteralPath ".python-version"
    pyenv install -s $pythonVersion.Trim()
}

poetry install
