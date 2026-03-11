# Magic Areas Refactoring Guide

**Status**: Recomposition and consolidation in progress  
**Last Updated**: 2026-03-12

## Overview

This guide describes how to contribute safely while the integration continues to
refactor from the fork baseline (`d7b5779`) into a cleaner architecture.

The project is no longer in early decomposition. Most core boundaries exist.
Current work is about finishing composition and reducing remaining duplication.

## Current Architecture Status

Authoritative status lives in:
- `docs/notes/theoretical_architecture_map.md`

High-level status:
- **Layer 1 (Snapshot/Ingestion): Implemented**
  - Coordinator-owned ingestion and snapshot assembly now live under
    `custom_components/magic_areas/coordinator/`.
- **Layer 2 (Feature Modules): Implemented**
  - Feature entry points live in `custom_components/magic_areas/features/modules/`.
- **Layer 3 (Policy Layer): Implemented**
  - Canonical policy contract (`core/control_group.py`) is in use across
    light/fan/climate/media.
  - Typed policy signal payloads are passed at runtime boundaries.
  - Policy runtime transitions are represented as canonical runtime effects.
- **Layer 4 (Execution Layer): Implemented**
  - Shared execution in `core/control_group_executor.py`.
- **Layer 5/6/9: Partial**
  - Group-model consolidation, entity thinning, and constants cleanup remain.

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

## Current Priorities

From the architecture roadmap, current order is:
1. **Layer 6**: Thin remaining heavy entity/event adapters (especially light glue).
2. **Layer 5**: Consolidate group lifecycle and lookup patterns.
3. **Layer 9**: Continue constants cleanup to keep only true shared values central.

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
uv run pytest ./tests --numprocesses=auto -q
```

As of this update, latest full run baseline is **823 passing tests**.

## Recommended Workflow

1. Read the relevant plan/roadmap note in `docs/notes/`.
2. Make one focused structural change.
3. Add or update contract tests first when changing boundaries.
4. Run ruff, mypy, and full pytest.
5. Remove shims/fallbacks that are no longer required.
6. Update roadmap/plan docs when status changes.

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
Not by default. The main boundaries already exist. Prefer consolidation and
boundary hardening over further fragmentation.

### Are temporary shims acceptable?
Only for short migrations. If parity is proven, remove them in the same stream
or immediately after.

### Where should new behavior go?
- Decision logic: `core/` policy modules.
- Execution and side effects: shared executor/runtime layer.
- HA entity wiring: platform/entity adapters.

### Which docs are source-of-truth for active work?
- `docs/notes/theoretical_architecture_map.md`
- `docs/notes/*_plan.md` files for active streams
- `CLAUDE.md` for repo workflow and standards
