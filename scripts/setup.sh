#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v pyenv >/dev/null 2>&1; then
  pyenv install -s "$(cat .python-version)"
fi

poetry install
