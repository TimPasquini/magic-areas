#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

exec uv run --with websockets python "$repo_root/scripts/ha_dev_bootstrap.py" "$@"
