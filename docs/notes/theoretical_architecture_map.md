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
**Status:** `Partial`
**Goal:** Make existing boundaries explicit without large behavior changes.

Implemented:
- Feature schemas moved into feature modules.
- Feature modules are the practical feature entry points.
- Entity-loading cluster packaged under `core/entity_loading/` with public API exports.

Partial:
- Entry-point/boundary documentation still needs final canonicalization.

Remaining:
- Canonicalize docs around current entry-point expectations.

Exit criteria:
- Entity loading is packaged as one cohesive boundary.
- Feature modules remain the only place that creates feature entities.

---

## Phase 1: Control Group Foundation
**Status:** `Planned`
**Goal:** Establish a reusable abstraction for control actions.

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
**Status:** `Partial`
**Goal:** Collapse light sprawl and prove the control-group abstraction.

Implemented:
- Light decision logic consolidated in policy code.

Partial:
- Light-related files remain spread across multiple locations.
- Light control is improved but not yet expressed as a generalized control group.

Remaining:
- Execute `docs/notes/light_system_recomposition_plan.md`.
- Move light implementation into a cohesive vertical slice package.
- Migrate from light-specific control tracking to shared control-group tracking.

Exit criteria:
- Light behavior unchanged, with clear package boundaries.
- Light no longer relies on bespoke control plumbing.

---

## Phase 3: Fan / Climate / Media Control Migration
**Status:** `Planned`
**Goal:** Replace bespoke control paths with control groups.

Deliverables:
- Fan control uses control-group policy + executor.
- Climate control uses control-group policy + executor.
- Media control uses control-group policy + executor where applicable.

Exit criteria:
- Consistent control behavior across features.
- Reduced per-feature control special cases.

---

## Phase 4: Group Registry + Custom Control Groups
**Status:** `Planned`
**Goal:** Support both defaults and custom cross-domain groups.

Deliverables:
- Group registry for default and user-defined groups.
- Config flow/schema support for custom control groups.
- Templates for common scenarios (task, reading, media, etc.).

Exit criteria:
- Custom cross-domain groups are possible without writing new feature code.

---

## Phase 5: Aggregation Generalization
**Status:** `Partial`
**Goal:** Make aggregates a reusable, universal mechanism.

Implemented:
- Strong aggregate foundation exists (selection/specs/factory + entities).

Partial:
- Aggregates are feature-oriented and not yet fully abstracted as a universal
  aggregation subsystem shared by all group types.

Remaining:
- Define a general aggregation policy contract.
- Align binary and numeric aggregation paths under shared definitions.
- Tie aggregate definitions into the future group registry.

Exit criteria:
- Aggregation behavior is unified and reusable across features.

---

# Layer Map (Target Architecture + Current Status)

## Layer 1: Snapshot / Ingestion (Coordinator-owned)
**Status:** `Partial`
**Purpose:** Build a single snapshot from HA registries + runtime state.

Current:
- `custom_components/magic_areas/core/snapshot_builder.py`
- `custom_components/magic_areas/core/entity_loading/loader.py`
- `custom_components/magic_areas/core/entity_loading/registry_queries.py`
- `custom_components/magic_areas/core/entity_loading/filters.py`
- `custom_components/magic_areas/core/entity_loading/snapshots.py`

Target:
- `coordinator/snapshot_builder.py`
- `coordinator/snapshot_models.py`
- `coordinator/entity_ingestion/`
- `coordinator/presence_ingestion/`

## Layer 2: Feature Modules (Entry Points)
**Status:** `Implemented`
**Purpose:** Feature entry points for schema + entity assembly + enablement.

Current:
- `custom_components/magic_areas/features/modules/*.py`
- `custom_components/magic_areas/features/registry.py`

## Layer 3: Policy Layer (Pure Decisions)
**Status:** `Partial`
**Purpose:** Deterministic decision logic with no HA side-effects.

Current:
- Light/fan/climate policy code exists.
- Generalized control-group policy does not exist yet.

## Layer 4: Execution Layer (Service Calls / Echo Tracking)
**Status:** `Partial`
**Purpose:** Apply actions and track command echo/ownership.

Current:
- Light has control-tracking mechanics.
- Shared executor and generalized echo tracker are not implemented.

## Layer 5: Groups (Definitions + Membership)
**Status:** `Planned`
**Purpose:** Explicit group definitions for control and aggregation.

Current:
- Domain-specific group concepts exist.
- Unified group registry and cross-domain control groups are not implemented.

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
1. Finish entity-loading packaging (Phase 0 completion).
2. Build control-group foundation (Phase 1).
3. Recompose light system around control groups (Phase 2).
4. Migrate fan/climate/media onto shared control infrastructure (Phase 3).
5. Add group registry and custom groups, then finalize aggregation unification (Phases 4-5).
