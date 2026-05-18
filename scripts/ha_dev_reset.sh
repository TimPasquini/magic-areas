#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/dev/ha"

docker compose down --remove-orphans || true
"$repo_root/scripts/ha_dev_clean_config.sh"
"$repo_root/scripts/ha_dev_init.sh"
