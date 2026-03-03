# Runtime Boundaries and Entry Points

This document is the canonical reference for **where runtime behavior enters**
the integration and which boundaries are intentionally stable.

## 1) Integration entry point

- `custom_components/magic_areas/__init__.py`
  - Sets up config entries and coordinator lifecycle.
  - This is the only top-level integration bootstrap.

## 2) Coordinator snapshot boundary

- `custom_components/magic_areas/coordinator.py`
- `custom_components/magic_areas/core/snapshot_builder.py`

Contract:
- Coordinator owns refresh cadence and snapshot creation.
- Platforms and entities read `coordinator.data` only.
- No platform/entity code reaches behind this boundary.

## 3) Entity-loading boundary

- `custom_components/magic_areas/core/entity_loading/__init__.py`
  - Public exports:
    - `load_area_entities`
    - `load_meta_area_entities`
- Internal implementation modules:
  - `loader.py`
  - `registry_queries.py`
  - `filters.py`
  - `snapshots.py`

Contract:
- Callers import from `core.entity_loading` package root, not internals.

## 4) Feature module boundary (runtime composition)

- `custom_components/magic_areas/features/registry.py`
- `custom_components/magic_areas/features/dispatch.py`
- `custom_components/magic_areas/features/modules/*.py`

Contract:
- Feature modules are the runtime entity-construction entry points.
- Platforms consume modules via registry/dispatch, not by importing feature internals.
- Feature-specific dependencies are declared on modules, not platforms.

## 5) Platform entry points (Home Assistant required)

- `custom_components/magic_areas/binary_sensor/__init__.py`
- `custom_components/magic_areas/sensor/__init__.py`
- `custom_components/magic_areas/light.py`
- `custom_components/magic_areas/fan.py`
- `custom_components/magic_areas/cover.py`
- `custom_components/magic_areas/media_player/__init__.py`
- `custom_components/magic_areas/switch/__init__.py`

Contract:
- Platforms stay adapter-thin: snapshot -> feature dispatch -> entities.
- Domain policy and control logic stays out of platform setup.

## 6) Control-group runtime boundary

- `custom_components/magic_areas/core/control_group.py`
- `custom_components/magic_areas/core/control_group_executor.py`
- `custom_components/magic_areas/core/control_group_runtime.py`
- `custom_components/magic_areas/core/group_registry.py`

Contract:
- Policy mapping produces `ControlGroupDecision`.
- Executor applies service actions.
- Runtime resolver handles registry-first target lookup + fallback.
- Group registry stores default/custom control-group definitions.

## 7) Config-flow boundary

- `custom_components/magic_areas/config_flow.py`
- `custom_components/magic_areas/config_flows/options_flow.py`
- `custom_components/magic_areas/config_flows/feature_registry.py`

Contract:
- Options flow is schema-driven.
- Feature menu and step wiring are derived from feature module metadata.

## 8) Allowed cross-boundary usage

Allowed:
- Platforms -> `features.dispatch`/`features.registry`
- Features -> `core/*` domain logic
- Switch/entity adapters -> `core.control_group_*` helpers

Not allowed:
- Platforms importing feature module internals directly.
- Feature modules importing platform setup modules.
- Entities bypassing snapshot/coordinator boundaries for config/runtime state.
