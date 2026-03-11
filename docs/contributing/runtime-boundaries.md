# Runtime Boundaries and Entry Points

This document defines the runtime boundaries that contributors should treat as
stable contracts.

## 1) Integration entry point

- `custom_components/magic_areas/__init__.py`

Contract:
- Owns config-entry setup/unload lifecycle.
- Owns coordinator construction and platform forwarding.

## 2) Coordinator snapshot boundary

- `custom_components/magic_areas/coordinator/__init__.py`
- `custom_components/magic_areas/coordinator/snapshot_builder.py`
- `custom_components/magic_areas/coordinator/snapshot_models.py`

Contract:
- Coordinator owns refresh cadence and snapshot creation.
- Platforms/entities read `coordinator.data` only.
- Snapshot model (`MagicAreasData`) is the read contract.

## 3) Entity ingestion boundary (coordinator-owned)

- `custom_components/magic_areas/coordinator/entity_ingestion/__init__.py`
  - public exports:
    - `load_area_entities`
    - `load_meta_area_entities`
- internal modules:
  - `loader.py`
  - `registry_queries.py`
  - `filters.py`
  - `snapshots.py`

Contract:
- Import from package root only (`coordinator.entity_ingestion`).
- Coordinator is the ingestion caller; platforms do not ingest directly.

## 4) Presence ingestion boundary (coordinator-owned)

- `custom_components/magic_areas/coordinator/presence_ingestion/__init__.py`
- `custom_components/magic_areas/coordinator/presence_ingestion/presence.py`

Contract:
- Presence sensor selection for snapshot composition is coordinator-owned.
- Entity runtime state machines remain outside this boundary.

## 5) Feature module boundary (runtime composition)

- `custom_components/magic_areas/features/registry.py`
- `custom_components/magic_areas/features/dispatch.py`
- `custom_components/magic_areas/features/modules/*.py`

Contract:
- Feature modules are runtime entity-construction entry points.
- Platforms use registry/dispatch, not module internals.
- Feature dependencies are declared in feature modules.

## 6) Platform entry points (Home Assistant required)

- `custom_components/magic_areas/binary_sensor/__init__.py`
- `custom_components/magic_areas/sensor/__init__.py`
- `custom_components/magic_areas/light.py`
- `custom_components/magic_areas/fan.py`
- `custom_components/magic_areas/cover.py`
- `custom_components/magic_areas/media_player/__init__.py`
- `custom_components/magic_areas/switch/__init__.py`

Contract:
- Adapter-thin setup: snapshot -> feature dispatch -> entity instances.
- Domain policy and execution logic stay out of platform setup.

## 7) Policy and control-group contract boundary

- `custom_components/magic_areas/core/control_group.py`
- `custom_components/magic_areas/core/fan_control.py`
- `custom_components/magic_areas/core/climate_control.py`
- `custom_components/magic_areas/core/media_control.py`
- `custom_components/magic_areas/light_groups/policy.py`

Contract:
- Policy adapters evaluate `ControlGroupContext`.
- Policy adapters return `ControlGroupDecision`.
- Policy code is pure (no HA service execution).

## 8) Execution/runtime boundary

- `custom_components/magic_areas/core/control_group_executor.py`
- `custom_components/magic_areas/core/control_group_runtime.py`
- `custom_components/magic_areas/core/group_registry.py`

Contract:
- Executor applies runtime effects + service actions.
- Runtime resolver performs registry-driven target lookup.
- Group registry stores default/custom definitions and scoped resolution.

## 9) Config-flow boundary

- `custom_components/magic_areas/config_flow.py`
- `custom_components/magic_areas/config_flows/options_flow.py`
- `custom_components/magic_areas/config_flows/feature_registry.py`
- `custom_components/magic_areas/config_flows/steps/*.py`

Contract:
- Options flow is schema/feature-registry driven.
- Feature menu and step wiring derive from feature metadata.

## Allowed and disallowed cross-boundary usage

Allowed:
- Platforms -> `features.dispatch` / `features.registry`
- Features -> `core/*` domain logic
- Entity/event adapters -> policy adapters + control-group executor

Not allowed:
- Platforms importing feature module internals directly
- Feature modules importing platform setup modules
- Policy modules calling HA service APIs or executor functions directly
- Platform/entity code bypassing coordinator snapshot for runtime/config state
