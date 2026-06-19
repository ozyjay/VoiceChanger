$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

poetry run python src/main.py
