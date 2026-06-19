$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

Set-Location (Join-Path $PSScriptRoot "..")

poetry run python src/main.py
