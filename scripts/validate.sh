#!/usr/bin/env bash
set -euo pipefail

export MYPYPATH="${MYPYPATH:-.}"

uv run --extra dev --extra test ruff check custom_components tests scripts
uv run --extra dev mypy --no-incremental --explicit-package-bases custom_components tests scripts
uv run --extra dev --extra test pytest tests -q
