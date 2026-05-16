#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$repo_root/dev/ha"
docker compose down --remove-orphans || true
rm -rf config
"$repo_root/scripts/ha_dev_init.sh"
exec docker compose up
