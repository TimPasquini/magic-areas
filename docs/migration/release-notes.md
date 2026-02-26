# Release notes summary (fork delta)

This is a concise summary of the major changes since the fork baseline
(`d7b5779`) intended for upstream review.

## Runtime architecture

- Coordinator-driven snapshots are the single source of truth for platforms.
- Platforms are thin, registry-driven routers that only read snapshots.
- Event payloads include full current state snapshots to avoid stale reads.

## Feature modules

- Feature modules are the single source of truth for:
  - entity construction per feature
  - feature dependencies
  - config flow steps and schemas
- Added modules for light/fan/media/cover groups, presence hold, climate control,
  BLE trackers, health, aggregates, wasp-in-a-box, and area-aware media player
  (config-only).

## Config flow

- Config flow registry builds from the runtime FeatureRegistry.
- Options flow is schema-driven; feature steps are routed dynamically.
- OPTIONS_* lists were removed and `schemas/validation.py` deleted.

## Entity model

- Group entities extracted into dedicated modules to avoid circular imports.
- Light control switch moved to a dedicated module and used via the registry.

## Consolidation

- Shared platform dispatch helper reduces duplicated registry wiring logic.
- Feature module boilerplate consolidated via `BaseFeatureModule`.

## Validation

- Full test, mypy, and ruff runs confirm parity after refactors.
