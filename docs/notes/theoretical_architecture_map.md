# Architecture Roadmap & Implementation Status

This document defines the north-star architecture and tracks what is already
implemented, what is partial, and what is still planned.

## Guiding Principle
Magic Areas is a higher-level layer on top of Home Assistant that replaces
repetitive automations with structured, area-based policies. Users define the
signals and devices that belong together; Magic Areas manages state, grouping,
and control logic.

## Status Legend
- `Implemented`: completed and in use.
- `Partial`: exists, but still needs structural cleanup or migration work.
- `Planned`: not implemented yet.

---

## Phase 0: Stabilize & Clarify Current Boundaries
**Status:** `Implemented`
**Goal:** Make existing boundaries explicit without large behavior changes.

Implemented:
- Feature schemas moved into feature modules.
- Feature modules are the practical feature entry points.
- Entity ingestion is now packaged under
  `coordinator/entity_ingestion/` with public API exports.
- Canonical runtime entry-point and boundary documentation exists in
  `docs/contributing/runtime-boundaries.md`.

Exit criteria:
- Entity loading is packaged as one cohesive boundary.
- Feature modules remain the only place that creates feature entities.

---

## Phase 1: Control Group Foundation
**Status:** `Implemented`
**Goal:** Establish a reusable abstraction for control actions.

Implemented:
- `core/control_group.py` now defines control-group contracts
  (definitions, context, actions, policy protocol, decision type).
- `core/command_echo.py` now provides a generic command-echo ownership tracker.
- `core/control_group_executor.py` now provides shared service execution for
  control-group decisions.
- Light runtime commands are now executed through control-group mapping +
  shared executor.
- Foundation contract tests exist for control-group objects and echo transitions.

Deliverables:
- `control_group` model (members, triggers, actions, policy binding).
- `control_group_policy` (pure decisions).
- `control_group_executor` (service call application).
- `command_echo` tracker (generalized ownership/echo handling).

Exit criteria:
- One generic control-group implementation exists and is testable.
- Echo tracking is no longer light-specific.

---

## Phase 2: Light System Recomposition
**Status:** `Implemented`
**Goal:** Collapse light sprawl and prove the control-group abstraction.

Implemented:
- Light decision logic consolidated in policy code.
- Light implementation moved into `custom_components/magic_areas/light_groups/`
  (`config.py`, `entities.py`, `events.py`, `actions.py`, `policy.py`).
- Feature module now imports light entities from the vertical-slice package.
- Light runtime control tracking now uses shared command-echo state/tracker
  (`core/command_echo.py`) rather than direct `core/control.py` usage.
- Light evaluation now runs through a canonical control-group adapter in
  `light_groups/policy.py` (`LightControlGroupPolicy`) with context-driven
  evaluation in `light_groups/events.py`.
- Light compatibility control-state shims were removed; runtime uses explicit
  echo-state internals only.
- Added adapter coverage in
  `tests/unit/test_light_control_group_policy_adapter.py`.

Remaining:
- Ongoing maintenance and parity checks only.

Exit criteria:
- Light behavior unchanged, with clear package boundaries.
- Light no longer relies on bespoke control plumbing.

---

## Phase 3: Fan / Climate / Media Control Migration
**Status:** `Implemented`
**Goal:** Replace bespoke control paths with control groups.

Implemented:
- Added shared executor: `core/control_group_executor.py`.
- Added shared runtime target resolution helper:
  `core/control_group_runtime.py`.
- Fan control now maps policy decisions through `fan_decision_to_control_group`
  and executes via the shared executor.
- Climate control now maps preset application through
  `climate_preset_to_control_group` and executes via the shared executor.
- Media player control now maps area-state changes through
  `media_state_change_to_control_group` and executes via the shared executor.
- Fan/media target entity resolution now uses the shared registry runtime
  resolver path.
- Added Phase C contract tests:
  - `tests/unit/test_fan_control_group_parity.py`
  - `tests/unit/test_climate_control_group_parity.py`
  - `tests/unit/test_media_control_group_parity.py`
  - `tests/unit/test_control_group_executor.py`
  - `tests/unit/test_control_group_runtime.py`
  - `tests/unit/test_control_group_registry_runtime_resolution.py`

Deliverables:
- Fan control uses control-group policy + executor.
- Climate control uses control-group policy + executor.
- Media control uses control-group policy + executor where applicable.

Exit criteria:
- Consistent control behavior across features.
- Reduced per-feature control special cases.

---

## Phase 4: Group Registry + Custom Control Groups
**Status:** `Implemented`
**Goal:** Support both defaults and custom cross-domain groups.

Implemented:
- Added registry foundation in `core/group_registry.py` with:
  - default group registration
  - area-scoped custom group registration
  - area resolution with custom-over-default precedence
  - policy-scoped area-default replacement (`register_area_defaults`) to prevent
    stale defaults during config/category changes
  - policy-filtered lookups for runtime consumers
- Feature modules now register area-scoped default control-group definitions
  for light, fan, climate, and media-player groups.
- Area schema/config now supports `custom_control_groups` definitions and
  snapshot build registers them as area-scoped custom groups at runtime.
- Options flow now exposes a `custom_control_groups` step for authoring
  validated custom group definitions in UI.
- Added starter templates for custom control groups (task/reading/media) in
  `core/control_group_templates.py`, seeded by options flow when unset.
- Fan/media control switches now resolve their target group entity IDs through
  group-registry definitions.
- Climate control runtime can resolve its target climate entity from
  group-registry members as a runtime fallback.
- Light ALL-group child resolution now consumes group-registry metadata first
  (with entity-registry fallback retained).
- Removed legacy fallback unique-id target resolution from
  `core/control_group_runtime.py`; control target resolution is now
  registry-driven.
- Added unit coverage in `tests/unit/test_group_registry.py`.

Deliverables:
- Group registry for default and user-defined groups.
- Config flow/schema support for custom control groups.
- Templates for common scenarios (task, reading, media, etc.).

Exit criteria:
- Custom cross-domain groups are possible without writing new feature code.
- Control target resolution is registry-driven only (no dual-path fallback).

---

## Phase 6: Migration Cleanup (Fallback + Shim Removal)
**Status:** `Implemented`
**Goal:** Eliminate dual-path runtime behavior after parity is proven.

Deliverables:
- Remove `fallback_unique_id` usage from `core/control_group_runtime.py` call
  sites and helper internals.
- Remove light compatibility control-state shims from
  `light_groups/entities.py`.
- Add explicit contract tests for:
  - registry target resolution coverage for fan/climate/media/light paths,
  - expected behavior when registry entries are missing (deterministic NOOP),
  - no direct legacy control-state access in light runtime/event flow.

Exit criteria:
- No runtime control path depends on legacy unique-id fallback.
- No light runtime code relies on legacy compatibility state properties.
- Full suite remains green with parity maintained.

---

## Phase 5: Aggregation Generalization
**Status:** `Implemented`
**Goal:** Make aggregates a reusable, universal mechanism.

Implemented:
- Strong aggregate foundation exists (selection/specs/factory + entities).
- Added canonical aggregate policy layer:
  - `core/aggregate_policy.py` with `AggregatePolicyContext` and
    `AggregateSelectionPolicy`.
  - Binary/sensor/health aggregate consumers now execute through the shared
    policy contract rather than directly calling selection helpers.
- Canonical aggregate definition model now unifies aggregate outputs:
  - `AggregateDefinition` + `AggregateKind` in `core/aggregate_policy.py`.
  - Sensor/binary aggregate entity factories now consume shared definitions.
- Aggregate definitions are now registered in the shared group registry:
  - `core/aggregate_runtime.py` registers area aggregate definitions under
    policy scope `aggregate`.
  - Threshold and Wasp runtime resolution now consume aggregate-runtime
    registry lookups first, with deterministic metadata-driven resolution.
- Added contract coverage:
  - `tests/unit/test_aggregate_policy.py`
  - `tests/unit/test_aggregate_runtime.py`
  - `tests/unit/test_feature_module_contracts.py`

Exit criteria:
- Aggregation behavior is unified and reusable across features.

---

# Layer Map (Target Architecture + Current Status)

## Layer 1: Snapshot / Ingestion (Coordinator-owned)
**Status:** `Implemented`
**Purpose:** Build a single snapshot from HA registries + runtime state.

Current:
- `custom_components/magic_areas/coordinator/snapshot_builder.py`
- `custom_components/magic_areas/coordinator/snapshot_models.py`
- `custom_components/magic_areas/coordinator/entity_ingestion/loader.py`
- `custom_components/magic_areas/coordinator/entity_ingestion/registry_queries.py`
- `custom_components/magic_areas/coordinator/entity_ingestion/filters.py`
- `custom_components/magic_areas/coordinator/entity_ingestion/snapshots.py`
- `custom_components/magic_areas/coordinator/presence_ingestion/presence.py`

## Layer 2: Feature Modules (Entry Points)
**Status:** `Implemented`
**Purpose:** Feature entry points for schema + entity assembly + enablement.

Current:
- `custom_components/magic_areas/features/modules/*.py`
- `custom_components/magic_areas/features/registry.py`

## Layer 3: Policy Layer (Pure Decisions)
**Status:** `Implemented`
**Purpose:** Deterministic decision logic with no HA side-effects.

Current:
- Light/fan/climate/media policy adapters evaluate canonical
  `ControlGroupContext` and return canonical `ControlGroupDecision`.
- Typed feature signal payloads are used at runtime boundaries.
- Light runtime command-echo transitions are encoded as canonical runtime
  effects on decisions.
- Policy purity is locked via contract tests (no executor/service calls in
  policy modules).

## Layer 4: Execution Layer (Service Calls / Echo Tracking)
**Status:** `Implemented`
**Purpose:** Apply actions and track command echo/ownership.

Current:
- Shared control-group executor: `core/control_group_executor.py`.
- Shared runtime resolver: `core/control_group_runtime.py`.
- Generalized echo tracker: `core/command_echo.py`.
- Light/fan/climate/media control execution paths run through shared
  control-group execution.

## Layer 5: Groups (Definitions + Membership)
**Status:** `Partial`
**Purpose:** Explicit group definitions for control and aggregation.

Current:
- Unified group registry exists for defaults and area-scoped custom groups.
- Feature modules register area-scoped default control-group definitions.
- Cross-domain custom control groups are exposed through config flow, with
  starter templates for common scenarios.

## Layer 6: Entities (Thin Adapters)
**Status:** `Partial`
**Purpose:** HA entity adapters without policy-heavy logic.

Current:
- Some entities are thin; light still has meaningful event/control glue.

## Layer 7: Platforms (HA Required)
**Status:** `Implemented`
**Purpose:** HA platform entry points.

Current:
- All required platforms exist; most are already adapter-style.

## Layer 8: Config Flow
**Status:** `Implemented`
**Purpose:** Schema-driven config handling.

Current:
- Config flow is schema-driven and feature-module aligned.

## Layer 9: Core Constants & Enums
**Status:** `Partial`
**Purpose:** Shared values only.

Current:
- Improved but still evolving (`config_keys.py` + `defaults.py` split).
- Additional consolidation may follow during control-group work.

---

## Near-Term Recommended Order
1. Continue entity-thinning work (Layer 6), especially reducing light event
   glue and pushing remaining orchestration into shared runtime helpers.
2. Continue group-model consolidation (Layer 5) so control/aggregate group
   lifecycle and lookup patterns remain consistent across features.
3. Continue constants cleanup (Layer 9) to keep only true cross-cutting shared
   values in central constants modules.
