# Release notes summary (fork delta)

This is the concise release-delta summary versus fork baseline `d7b5779`.

## Runtime and coordinator model

- Replaced platform-local runtime assembly with coordinator-owned typed snapshots.
- `MagicAreasData` is now the runtime read contract for all platforms/entities.
- Entity ingestion moved under coordinator ownership
  (`coordinator/entity_ingestion/*`), including filtering and normalization.

## Feature composition model

- Introduced registry-backed feature modules as the canonical runtime composition
  path for platform entities.
- Feature modules now own feature enablement, dependencies, and config-flow step
  declarations.

## Policy and execution boundaries

- Standardized control decisions around canonical control-group contracts
  (`ControlGroupContext`, `ControlGroupDecision`, runtime effects).
- Centralized execution/runtime resolution in shared control-group runtime helpers.
- Light/fan/climate/media control paths now share the same evaluation/execution
  shape, with feature-specific adapters layered on top.

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
  - `coordinator.entity_ingestion`
  - `config_flows` and `config_flows.steps`
  - `switch`
  - `media_player`

## Validation status

- Current code passes full quality gates (`ruff`, `mypy`, full `pytest`).
