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
- `custom_components/magic_areas/coordinator/pipeline/lifecycle.py`
- `custom_components/magic_areas/coordinator/pipeline/snapshot.py`

Contract:
- Coordinator owns refresh cadence and snapshot creation.
- Lifecycle managers own:
  - meta-area reload orchestration/retry state, and
  - non-meta readiness convergence reload scheduling.
- Platforms/entities read `coordinator.data` only.
- Snapshot model (`MagicAreasData`) is the read contract.

## 3) Entity ingestion boundary (coordinator-owned)

- `custom_components/magic_areas/coordinator/pipeline/entity_ingestion/__init__.py`
  - public exports:
    - `is_magic_area_entity`
    - `should_exclude_entity`
    - `filter_entity_list`
    - `EntitySnapshot`
    - `build_entity_dict`
    - `group_entities`
    - `get_entity_registry`
    - `get_device_registry`
    - `load_area_entities`
    - `load_meta_area_entities`
- internal modules:
  - `loader.py`
  - `registry_queries.py`

Contract:
- Import from package root only (`coordinator.pipeline.entity_ingestion`).
- Coordinator is the ingestion caller; platforms do not ingest directly.

## 4) Presence ingestion boundary (coordinator-owned)

- `custom_components/magic_areas/coordinator/pipeline/presence_ingestion.py`

Contract:
- Presence sensor selection for snapshot composition is coordinator-owned.
- Entity runtime state machines remain outside this boundary.

## 5) Feature module boundary (runtime composition)

- `custom_components/magic_areas/features/registry.py`
- `custom_components/magic_areas/features/dispatch.py`
- `custom_components/magic_areas/features/modules/*.py`
- `custom_components/magic_areas/features/config/__init__.py`
- `custom_components/magic_areas/features/base.py`

Contract:
- Feature modules are runtime entity-construction entry points.
- `features.config` and explicit feature config slices
  (`features.config.<feature_slice>`) are the public feature-owned runtime config
  accessor surfaces.
- Runtime consumers import explicit feature surfaces (`features.dispatch`,
  `features.registry`, `features.base`, `features.config`) instead of relying on
  package-root convenience imports.
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

- `custom_components/magic_areas/core/controls/control_group.py`
- `custom_components/magic_areas/core/controls/policies/fan.py`
- `custom_components/magic_areas/core/controls/policies/climate.py`
- `custom_components/magic_areas/core/controls/policies/media.py`
- `custom_components/magic_areas/light_groups/policy.py`
- `custom_components/magic_areas/light_groups/config.py`
- `custom_components/magic_areas/light_groups/entities.py`

Contract:
- Policy adapters evaluate `ControlGroupContext`.
- Policy adapters return `ControlGroupDecision`.
- Policy code is pure (no HA service execution).
- Light category wiring is preset-driven (`light_groups/config.py`) and consumed
  by feature composition (`features/modules/light_groups.py`).
- Parent light-group child linkage resolves through control-group metadata in
  deterministic category order.
- Light policy signal parsing is guarded: missing `is_primary` identity produces
  a `NOOP` decision (`invalid_light_policy_signals`) instead of evaluating a
  potentially incorrect branch; missing `control_state` alone uses deterministic
  fallback command-echo state.

## 8) Execution/runtime boundary

- `custom_components/magic_areas/core/controls/control_group.py`
- `custom_components/magic_areas/core/controls/control_group_runtime.py`
- `custom_components/magic_areas/core/runtime_model/groups.py`

Contract:
- Executor applies runtime effects + service actions.
- Runtime resolver performs registry-driven target lookup.
- Group registry stores default/custom definitions and scoped resolution.
- Registry instances are runtime-injected (no process-global singleton).

## 9) Config-flow boundary

- `custom_components/magic_areas/config_flow.py`
- `custom_components/magic_areas/config_flows/__init__.py`
- `custom_components/magic_areas/config_flows/options_flow.py`
- `custom_components/magic_areas/config_flows/entity_gatherer.py`
- `custom_components/magic_areas/config_flows/steps/__init__.py`
- `custom_components/magic_areas/config_flows/steps/*.py`

Contract:
- Options flow is schema/feature-registry driven.
- Feature menu and step wiring derive from feature metadata.
- Import config-flow helpers through package entry points (`config_flows` and
  `config_flows.steps`) instead of side-door imports into implementation modules.

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

## Boundary enforcement policy

- Central modules may contain only shared generic primitives.
- Feature-specific semantics must live in the owning feature slice.
- Import-boundary tests must block side-door imports that bypass slice entry
  points (`tests/unit/test_import_boundaries.py`).
- Ownership guardrails also enforce:
  - `core.config.feature` remains generic-only (normalization/access primitives).
  - central facades do not re-export feature semantics unintentionally.
  - runtime imports consume entry surfaces, not internal implementation modules.
