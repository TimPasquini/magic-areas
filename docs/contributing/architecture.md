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
- Managed Home Assistant helper/label surfaces: implemented
- Control-intent target model and light suppression adapter: implemented
- Adaptive Lighting coordination: implemented as optional light-group side effects
- Entity adapters: implemented
- Platform adapters: implemented
- Config flow architecture: implemented
- Constants/enums ownership cleanup: implemented

## Runtime Ownership

- `__init__.py` owns config-entry lifecycle and coordinator wiring.
- `coordinator/` owns refresh and snapshot creation (`MagicAreasData`).
- `coordinator/pipeline/lifecycle.py` owns meta-area reload orchestration and retry/throttle scheduling.
- `coordinator/pipeline/entity_ingestion/` owns entity ingestion/filtering/snapshot prep.
- `coordinator/managed_surfaces.py` owns reconciliation for Magic Areas-managed
  Home Assistant helper config entries, scoped labels, registry metadata, and
  stale-surface repair issues.
- `coordinator/adaptive_lighting.py` owns reconciliation of Magic Areas-managed
  Adaptive Lighting config entries.
- `features/modules/` owns feature composition and entity construction contracts.
- `core/` owns policy + runtime abstractions and the canonical cross-slice API
  surface (HA-side effects excluded from policy).
- platform modules (`binary_sensor/`, `sensor/`, `light.py`, `switch/`, etc.) are
  thin adapters: snapshot -> feature dispatch -> entities.
- `features` package root is intentionally small; runtime imports target explicit
  feature surfaces (`features.dispatch`, `features.registry`, `features.base`,
  `features.config`).

## Feature Two-Door Ownership (Current)

- Metadata door:
  - `custom_components/magic_areas/feature_info.py`
  - Owns canonical `FeatureInfo` metadata map + lookup (`get_feature_info`).
  - Must remain free of runtime module wiring imports.
- Runtime door:
  - `custom_components/magic_areas/features/registry.py`
  - Owns feature module registration, availability/configurability checks, and
    dependency validation.
- Entity/runtime usage:
  - `entity.py` consumes metadata door directly.
  - No root `feature_registry.py` lazy/proxy compatibility layer is present.

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
- `core/control_intents/` owns source-neutral intent/target models, pure
  arbitration, target resolution, and Adaptive Lighting intent helpers.
- Runtime target resolution can represent broad HA labels, exact native helper
  entities, explicit entity subsets, and hidden compatibility policy entities.
- Normal room/role control prefers exact native helper entities where available.
  Broad HA `label_id` targets are valid only for intentionally broad actions;
  filtered/intersection/suppression decisions must resolve explicit entity IDs.

## Managed HA Surfaces (Current)

Magic Areas now delegates durable HA-native storage and control surfaces where
Home Assistant already provides the primitive:

- Native `group` helper config entries are reconciled for exact room/domain/role
  surfaces such as light roles, fan groups, media-player groups, cover groups,
  health groups, and aggregate helper outputs.
- Native `threshold` helpers are reconciled for calculated light-state sensors
  from the area illuminance aggregate, threshold, and hysteresis settings.
- Native signal helpers are reconciled where they are generic measured-condition
  inputs, starting with a Trend helper for adaptive-switching ambient-rise
  evidence.
- Magic Areas-owned HA Labels are reconciled for semantic membership:
  `ma:overhead`, `ma:task`, `ma:sleep`, `ma:accent`, and `ma:control:*`.
- Managed helper entities are assigned to the appropriate HA area and are
  excluded from Magic Areas source enumeration so they do not recursively feed
  their own managed outputs.
- Magic Areas-managed helpers and labels are reconciled from Magic Areas config
  and entity catalogs. Users should edit managed surfaces through Magic Areas
  config, not by hand-editing the generated helper config entries.

The origin of semantic grouping remains Magic Areas. HA Labels and helper
entities provide storage, display, target selection, and service surfaces; they
do not infer what a "sleep light", "accent light", or custom control group means
for a particular room.

## Light Runtime and Adaptive Lighting (Current)

- Hidden `AreaLightGroup` policy entities remain enabled but hidden. They own
  listener registration, command echo/manual override state, fallback dispatch,
  and debug attributes.
- Native light helper groups are the preferred HA-facing exact command/dashboard
  targets for room/role light groups.
- Light sleep/accent suppression consumes reconciled labels first, bounded by
  the current area light entity set, with config lists retained only as a
  startup/reconciliation fallback.
- The light intent adapter computes explicit member subsets for sleep/accent
  suppression instead of requiring hidden combo entities.
- Adaptive Lighting is optional and external. Magic Areas can ignore it, adopt
  existing switch sets, or manage selected Adaptive Lighting config entries for
  light roles. Adaptive Lighting still owns brightness, color temperature, sleep
  appearance, transitions, and related tuning.
- Magic Areas coordinates Adaptive Lighting as runtime side effects only:
  sleep switch coordination, accent adaptation pause/restore, and clearing
  Adaptive Lighting manual-control state when Magic Areas resumes control.

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
- Native helper/label reconciliation, managed Adaptive Lighting, control-intent
  targets, and light suppression behavior have dedicated unit/integration tests.

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
- Core boundary inversion is removed:
  - production `core/` modules do not import `features.config.readers`.
  - boundary tests enforce this contract.

## Invariants

- Behavior-preserving structural changes only unless explicitly scoped.
- Policy remains pure; execution remains centralized.
- Coordinator snapshot remains the read contract for platform/entity setup.
- Managed HA helper/label surfaces are generated from Magic Areas config and
  catalog state, not treated as independent Magic Areas-internal truth.
- No long-lived compatibility shims after parity is proven.
- Full validation must stay green:
  - `uv run --extra dev --extra test ruff check custom_components tests scripts`
  - `uv run --extra dev --extra test mypy custom_components tests scripts`
  - `uv run --extra dev --extra test pytest tests -q`
