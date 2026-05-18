#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ha_dir="$repo_root/dev/ha"
config_dir="$ha_dir/config"
seed_dir="$ha_dir/seed"

mkdir -p "$config_dir/custom_components"
"$repo_root/scripts/ha_dev_install_adaptive_lighting.sh"

if [[ ! -f "$config_dir/configuration.yaml" ]]; then
  cp "$seed_dir/configuration.yaml" "$config_dir/configuration.yaml"
fi

if [[ ! -d "$config_dir/packages" ]]; then
  cp -a "$seed_dir/packages" "$config_dir/packages"
fi

cat <<MSG
Prepared production-like HA dev config at:
  $config_dir

Magic Areas is mounted into the HA container from:
  $repo_root/custom_components/magic_areas

Adaptive Lighting is mounted into the HA container from:
  $repo_root/dev/ha/vendor/adaptive-lighting/custom_components/adaptive_lighting
MSG
