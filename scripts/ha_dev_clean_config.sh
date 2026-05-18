#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ha_dir="$repo_root/dev/ha"

cd "$ha_dir"
mkdir -p config/custom_components

docker compose run --rm --entrypoint /bin/sh homeassistant -c '
  # Keep auth/onboarding identity so existing local dev tokens survive resets.
  find /config -mindepth 1 -maxdepth 1 \
    ! -name custom_components \
    ! -name .storage \
    -exec rm -rf {} +

  mkdir -p /config/.storage
  find /config/.storage -mindepth 1 -maxdepth 1 \
    ! -name auth \
    ! -name auth_provider.homeassistant \
    ! -name onboarding \
    ! -name person \
    ! -name core.config \
    ! -name core.uuid \
    ! -name http \
    ! -name http.auth \
    -exec rm -rf {} +

  if [ -d /config/custom_components ]; then
    find /config/custom_components -mindepth 1 -maxdepth 1 \
      ! -name magic_areas \
      ! -name adaptive_lighting \
      -exec rm -rf {} +
  fi
'
