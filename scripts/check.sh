#!/bin/sh
# Run every check. Stop at the first check that fails.
set -eu
cd "$(dirname "$0")/.."
uv run ruff check .
uv run ruff format --check .
uv run pytest -q "$@"
