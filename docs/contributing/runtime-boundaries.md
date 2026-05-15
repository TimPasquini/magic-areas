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
- `custom_components/magic_areas/coordinator/managed_surfaces.py`
- `custom_components/magic_areas/coordinator/adaptive_lighting.py`

Contract:
- Coordinator owns refresh cadence and snapshot creation.
- Lifecycle managers own:
  - meta-area reload orchestration/retry state, and
  - non-meta readiness convergence reload scheduling.
- Managed-surface reconciliation owns Magic Areas-managed HA helper config
  entries, scoped HA labels, registry metadata, cleanup, and stale-surface
  repair issues.
- Adaptive Lighting reconciliation owns Magic Areas-managed Adaptive Lighting
  config entries and preserves Adaptive Lighting/user-owned tuning options.
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

- `custom_components/magic_areas/feature_info.py`
- `custom_components/magic_areas/features/registry.py`
- `custom_components/magic_areas/features/dispatch.py`
- `custom_components/magic_areas/features/modules/*.py`
- `custom_components/magic_areas/features/config/__init__.py`
- `custom_components/magic_areas/features/base.py`

Contract:
- Two-door ownership is enforced:
  - metadata door: `feature_info.py` (pure feature metadata lookup only)
  - runtime door: `features/registry.py` (module wiring, availability, dependency checks)
- Base entities consume metadata door (`get_feature_info`) and do not depend on
  runtime registry construction.
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
- Parent light-group child linkage resolves through stable light-group policy
  unique IDs in deterministic category order.
- Light policy signal parsing is guarded: missing `is_primary` identity produces
  a `NOOP` decision (`invalid_light_policy_signals`) instead of evaluating a
  potentially incorrect branch; missing `control_state` alone uses deterministic
  fallback command-echo state.
- Light sleep/accent suppression is member-aware. Runtime resolves role
  membership from reconciled labels first, bounded by the current area light
  entity set, and uses explicit entity IDs when suppression/intersection logic
  narrows the target.

## 8) Execution/runtime boundary

- `custom_components/magic_areas/core/controls/control_group.py`
- `custom_components/magic_areas/core/controls/control_group_runtime.py`
- `custom_components/magic_areas/core/runtime_model/groups.py`
- `custom_components/magic_areas/core/runtime_model/managed_surfaces.py`
- `custom_components/magic_areas/core/runtime_model/signal_helpers.py`
- `custom_components/magic_areas/core/managed_surface_registry.py`

Contract:
- Executor applies runtime effects + service actions.
- Runtime resolver performs registry-driven target lookup.
- Group registry stores default/custom definitions and scoped resolution.
- Registry instances are runtime-injected (no process-global singleton).
- Managed-surface runtime models describe desired HA helper, label, and signal
  surfaces. They do not apply HA side effects directly.
- Managed-surface registry helpers resolve Magic Areas-owned helper entities by
  stable ownership metadata/unique IDs.

## 8a) Control intent boundary

- `custom_components/magic_areas/core/control_intents/__init__.py`
- `custom_components/magic_areas/core/control_intents/models.py`
- `custom_components/magic_areas/core/control_intents/engine.py`
- `custom_components/magic_areas/core/control_intents/targets.py`
- `custom_components/magic_areas/core/control_intents/adaptive_lighting.py`
- `custom_components/magic_areas/core/control_intents/adaptive_lighting_registry.py`
- `custom_components/magic_areas/core/control_intents/adaptive_lighting_executor.py`

Contract:
- Pure intent models and arbitration remain HA-free.
- Target records can represent broad HA labels, exact native helper entities,
  explicit entity subsets, and hidden compatibility policy entities.
- Runtime adapters gather HA state/registry data before invoking pure intent
  logic and execute returned decisions through existing runtime/executor paths.
- Adaptive Lighting is modeled as an external behavior system. Magic Areas
  emits side-effect intents for switch-set coordination; Adaptive Lighting owns
  brightness/color/sleep tuning.

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
- Reintroducing root-level lazy/proxy feature registry facades

## Boundary enforcement policy

- Central modules may contain only shared generic primitives.
- Feature-specific semantics must live in the owning feature slice.
- Home Assistant labels and managed helper config entries are external durable
  surfaces. Magic Areas reconciles the surfaces it owns, but feature/policy
  code should consume them through managed-surface and target resolver APIs.
- Import-boundary tests must block side-door imports that bypass slice entry
  points (`tests/unit/test_import_boundaries.py`).
- A small set of explicit allowlist seams is intentional and documented:
  - config-flow selector adapter seam
    (`config_flows.selector_builders -> schemas.selectors`)
  - test-only implementation contract seams (`light_groups.*`, `switch.base`)
- Graph-backed architecture/risk reviews must follow
  `docs/contributing/mcp-graph-hygiene.md` before interpreting MCP warnings.
- Ownership guardrails also enforce:
  - `core.config.feature` remains generic-only (normalization/access primitives).
  - `core/` does not import `features.config.readers` (feature adapter surface).
  - `ALLOWLIST_OVERRIDES` contains only intentional seams; no temporary
    `runtime_core` inversion overrides.
  - central facades do not re-export feature semantics unintentionally.
  - runtime imports consume entry surfaces, not internal implementation modules.
