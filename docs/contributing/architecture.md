# Current Architecture (Actual)

This document is the authoritative description of the **current implemented**
runtime architecture.

For historical fork deltas (vs `d7b5779`), see:
- `docs/migration/architecture.md`

## Implementation Status

- Snapshot and ingestion model: implemented
- Feature module composition: implemented
- Policy contracts: implemented
- Execution/runtime contracts: implemented
- Group contracts and registry: implemented
- Entity adapters: implemented
- Platform adapters: implemented
- Config flow architecture: implemented
- Constants/enums ownership cleanup: implemented

## Runtime Ownership

- `__init__.py` owns config-entry lifecycle and coordinator wiring.
- `coordinator/` owns refresh and snapshot creation (`MagicAreasData`).
- `coordinator/pipeline/lifecycle.py` owns meta-area reload orchestration and retry/throttle scheduling.
- `coordinator/pipeline/entity_ingestion/` owns entity ingestion/filtering/snapshot prep.
- `features/modules/` owns feature composition and entity construction contracts.
- `core/` owns policy + runtime abstractions and the canonical cross-slice API
  surface (HA-side effects excluded from policy).
- platform modules (`binary_sensor/`, `sensor/`, `light.py`, `switch/`, etc.) are
  thin adapters: snapshot -> feature dispatch -> entities.
- `features` package root is intentionally small; runtime imports target explicit
  feature surfaces (`features.dispatch`, `features.registry`, `features.base`,
  `features.config`).

## Control and Decision Boundaries

- Canonical decision contracts are exported from `core` (implemented in
  `core/controls/` and `core/runtime_model/groups.py`).
- Shared execution and runtime resolution are exported from `core` and implemented
  in `core/controls/`.
- Group definitions/metadata/registry are exported from `core.runtime_model` and
  implemented in `core/runtime_model/groups.py`.
- Light policy/runtime lives in `light_groups/` vertical slice and uses shared
  control contracts.
- Built-in light categories are declaration-driven via
  `light_groups/config.py` presets, consumed by
  `features/modules/light_groups.py`.
- Light-group area/group orchestration is handled inside
  `light_groups/entities.py` (thin adapter around shared control execution).
- Fan/climate/media control paths use control-group mapping + shared executor.

## Config and Schema Boundaries

- Options flow is schema/feature-registry driven.
- Feature config steps are owned by feature modules + config flow step handlers.
- Feature registration + feature metadata are single-sourced through
  `features/catalog.py` and consumed by `features/registry.py`.
- Feature option defaults are single-sourced in `option_defaults.py` and reused by
  both feature schemas and runtime accessors.
- Feature-module wiring consumes explicit entry surfaces; no deep module
  side-door imports.
- Config key imports are scoped by domain/module (`config_keys.*` submodules).

## Test Architecture State

- Test hardening/repair stream is complete:
  - brittle timing waits were moved to deterministic helpers
  - high-value assertion coverage replaced no-crash-only checks in target slices
  - large legacy test files were split by concern with shared testkits
- Boundary guards in `tests/unit/test_import_boundaries.py` are authoritative
  for import ownership and side-door prevention.

## Boundary Snapshot (Current)

- `config_keys` fanout is reduced through `core.config` adapters.
- Direct `config_keys` imports are intentionally concentrated in:
  - `core.config` (canonical config access surface),
  - feature-module schema declarations,
  - migration/runtime-model identity wiring paths.
- Test-side import boundaries enforce no-growth for high-churn internals:
  - `light_groups`
  - `features.modules`
  - `coordinator.pipeline.entity_ingestion`
  - `config_flows.steps`
  - `config_flows.helpers`
  - `config_flows.options_flow`
  - `config_flows.entity_gatherer`
  - `switch`
  - `media_player`
- These slices should be consumed via package entry points (not side-door module
  imports):
  - `custom_components.magic_areas.light_groups`
  - `custom_components.magic_areas.features.dispatch`
  - `custom_components.magic_areas.features.registry`
  - `custom_components.magic_areas.features.base`
  - `custom_components.magic_areas.features.config`
  - `custom_components.magic_areas.coordinator.pipeline.entity_ingestion`
  - `custom_components.magic_areas.config_flows`
  - `custom_components.magic_areas.config_flows.steps`
  - `custom_components.magic_areas.switch`
  - `custom_components.magic_areas.media_player`

## Invariants

- Behavior-preserving structural changes only unless explicitly scoped.
- Policy remains pure; execution remains centralized.
- Coordinator snapshot remains the read contract for platform/entity setup.
- No long-lived compatibility shims after parity is proven.
- Full validation must stay green:
  - `uv run ruff check custom_components/magic_areas tests`
  - `uv run mypy custom_components/magic_areas tests`
  - `uv run pytest tests -q`
