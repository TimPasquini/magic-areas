#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$repo_root/scripts/ha_dev_init.sh"
cd "$repo_root/dev/ha"
exec docker compose up
