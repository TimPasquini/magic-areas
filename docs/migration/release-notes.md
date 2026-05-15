# Release notes summary (fork delta)

This is the concise release-delta summary versus fork baseline `d7b5779`.

## Runtime and coordinator model

- Replaced platform-local runtime assembly with coordinator-owned typed snapshots.
- `MagicAreasData` is now the runtime read contract for all platforms/entities.
- Entity ingestion moved under coordinator ownership
  (`coordinator/pipeline/entity_ingestion/*`), including filtering and normalization.
- Coordinator-owned reconciliation now manages Magic Areas-owned HA helper
  config entries, labels, registry metadata, stale cleanup, and Adaptive
  Lighting config entries.

## Feature composition model

- Introduced registry-backed feature modules as the canonical runtime composition
  path for platform entities.
- Feature modules now own feature enablement, dependencies, and config-flow step
  declarations.
- Feature modules can declare desired managed HA surfaces for coordinator-side
  reconciliation.

## Policy and execution boundaries

- Standardized control decisions around canonical control-group contracts
  (`ControlGroupContext`, `ControlGroupDecision`, runtime effects).
- Centralized execution/runtime resolution in shared control-group runtime helpers.
- Light/fan/climate/media control paths now share the same evaluation/execution
  shape, with feature-specific adapters layered on top.
- Added source-neutral control-intent target models for broad HA labels, exact
  native helpers, explicit entity subsets, and hidden compatibility entities.
- Light sleep/accent suppression is member-aware and can dispatch explicit
  entity subsets for overlapping state behavior.
- Adaptive Lighting coordination is optional and modeled as side effects; Magic
  Areas can ignore, adopt, or manage Adaptive Lighting switch sets/configs while
  Adaptive Lighting keeps brightness/color/sleep tuning ownership.

## HA-native surface reduction

- Native HA helper config entries now provide exact group, aggregate,
  threshold, and signal surfaces where HA already owns the primitive.
- HA Labels provide semantic membership surfaces for Magic Areas light roles and
  custom control groups.
- Generated helper entities are area-assigned and excluded from source
  enumeration to prevent recursive grouping/aggregation.

## Config-flow architecture

- Converted options flow to schema/registry-driven routing.
- Removed legacy OPTIONS_* validation-list duplication and dynamicized
  `feature_conf_*` handling.
- Config-flow package surfaces now expose stable entry points for flow helpers
  and step handlers.

## Boundary hardening

- Established import-boundary contract tests that prevent new side-door imports
  into protected slices.
- Hardened package entrypoint usage for high-churn slices:
  - `light_groups`
  - `features.modules`
  - `coordinator.pipeline.entity_ingestion`
  - `config_flows` and `config_flows.steps`
  - `switch`
  - `media_player`

## Validation status

- Current code passes full quality gates (`ruff`, `mypy`, full `pytest`).
