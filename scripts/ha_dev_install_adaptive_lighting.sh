#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
vendor_dir="$repo_root/dev/ha/vendor/adaptive-lighting"
ref="${ADAPTIVE_LIGHTING_REF:-main}"
url="${ADAPTIVE_LIGHTING_REPO:-https://github.com/basnijholt/adaptive-lighting.git}"
component_dir="$vendor_dir/custom_components/adaptive_lighting"

if [[ ! -d "$vendor_dir/.git" ]]; then
  rm -rf "$vendor_dir"
  mkdir -p "$(dirname "$vendor_dir")"
  git clone --depth 1 --branch "$ref" "$url" "$vendor_dir"
elif [[ ! -d "$component_dir" ]]; then
  git -C "$vendor_dir" fetch --depth 1 origin "$ref"
  git -C "$vendor_dir" checkout FETCH_HEAD
fi

if [[ ! -d "$component_dir" ]]; then
  echo "Adaptive Lighting component was not found at: $component_dir" >&2
  exit 1
fi

printf 'Adaptive Lighting dev component ready: %s\n' "$component_dir"
