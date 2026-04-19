# Magic Areas Refactoring Guide

**Status**: Recomposition streams complete; repository reduction and
de-duplication stream active.
**Last Updated**: 2026-04-11

## Overview

This guide describes how to contribute safely while the integration continues to
refactor from the fork baseline (`d7b5779`) into a cleaner architecture.

The project is no longer in early decomposition. Core boundaries and ownership
guardrails are in place. Current work is compactness and maintainability:
reduce churn, reduce fanout, and collapse low-value indirection.

## Current Architecture Status

Authoritative status lives in:
- `docs/contributing/architecture.md`

High-level status:
- **High-severity hardening stream: Implemented**
  - Runtime-critical broad exception handling was narrowed to expected error
    classes in coordinator ingestion/update and binary-sensor runtime paths.
  - Control-group runtime resolver contracts now use typed registry protocols
    instead of broad `Any`.
  - Light-group entity responsibilities were decomposed into dedicated lifecycle
    and runtime collaborators under `light_groups/`.
  - Feature config accessor internals were consolidated behind shared generic
    helper pathways while preserving the runtime API contract.
- **Snapshot/Ingestion: Implemented**
  - Coordinator-owned ingestion and snapshot assembly now live under
    `custom_components/magic_areas/coordinator/`.
- **Feature Modules: Implemented**
  - Feature entry points live in `custom_components/magic_areas/features/modules/`.
- **Policy Layer: Implemented**
  - Canonical policy contracts are in use across light/fan/climate/media and are
    exported through the `core` package API.
  - Typed policy signal payloads are passed at runtime boundaries.
  - Policy runtime transitions are represented as canonical runtime effects.
- **Execution Layer: Implemented**
  - Shared execution is implemented in `core/controls/` and consumed via `core`
    package exports.
- **Group contracts/registry: Implemented**
  - Group contracts/metadata/registry live in
    `core/runtime_model/groups.py` and are consumed via
    `core.runtime_model`.
- **Constants/Enums cleanup: Implemented**
  - Source imports now use scoped key/default modules with reduced central
    constant fan-out.
- **Entity adapters: Implemented**
  - Entity adapters are now thin and delegate decision/execution concerns to
    helper/policy/runtime boundaries.

## What “Good Refactoring” Means Here

A change is good if it:
1. Preserves user-visible behavior.
2. Makes ownership clearer.
3. Reduces duplicated logic or ad-hoc glue.
4. Moves decisions into policy/core and keeps adapters thin.
5. Keeps strict quality gates green.

A change is not good if it:
- introduces new behavior during structural work,
- adds shims that remain indefinitely,
- increases cross-module side-door access,
- mixes policy and execution concerns.

## Contributor Rules

### Do
- Use existing module boundaries (`coordinator/`, `core/`, `features/modules/`,
  platform adapters) instead of introducing parallel patterns.
- Keep policy code pure and deterministic (no service calls, no runtime writes).
- Route execution through shared executor paths.
- Prefer typed payloads over ad-hoc dict key lookups.
- Remove temporary compatibility paths once replacements are proven.

### Don’t
- Reintroduce monolithic files for convenience.
- Add feature logic into platform setup/entity lifecycle code if it belongs in
  policy/core.
- Keep dual-path runtime behavior unless there is an explicit migration phase.
- Weaken tests to accommodate refactors.

## Testing and Quality Gates

Refactoring is complete only when all three pass:

```bash
uv run ruff check custom_components/magic_areas tests
uv run mypy custom_components/magic_areas tests
uv run pytest tests -q
```

As of this update, latest full run baseline is **966 passing tests**.

Completed refactor streams (runtime-model packaging, snapshot/control packaging,
and broad test hardening) are now reflected directly in:
- `docs/contributing/architecture.md`
- `docs/contributing/runtime-boundaries.md`

## File Responsibility Model (Current)

- **Coordinator (`coordinator/`)**: snapshot/ingestion lifecycle.
- **Core (`core/`)**: policy, domain logic, shared runtime abstractions.
- **Feature modules (`features/modules/`)**: feature assembly and enablement.
- **Platform adapters (`binary_sensor/`, `sensor/`, `switch/`, etc.)**:
  Home Assistant wiring only.
- **Light vertical slice (`light_groups/`)**: light-specific policy/entities/events,
  using shared core contracts.

If a file crosses categories, refactor toward a single primary ownership.

## FAQ

### Should we still split files aggressively?
No. The main boundaries already exist. Prefer consolidation, deletion, and
deduplication over further fragmentation.

### Are temporary shims acceptable?
Only for short migrations. If parity is proven, remove them in the same stream
or immediately after.

### Where should new behavior go?
- Decision logic: `core/` policy modules.
- Execution and side effects: shared executor/runtime layer.
- HA entity wiring: platform/entity adapters.

### Which docs are source-of-truth for active work?
- `docs/contributing/architecture.md`
- `docs/contributing/runtime-boundaries.md`
- `CLAUDE.md` for repo workflow and standards
