#!/bin/zsh
cd "$(dirname "$0")"
export UV_CACHE_DIR="${TMPDIR:-/tmp}/little-wins-uv-cache"
export UV_PYTHON_INSTALL_DIR="${TMPDIR:-/tmp}/little-wins-python"
if [ -x .venv/bin/python ]; then
  .venv/bin/python run.py
elif command -v uv >/dev/null 2>&1; then
  uv run run.py
else
  echo 'Install uv (https://docs.astral.sh/uv/) or follow README.md to use Python.'
fi
read '?Press Return to close this window…'
