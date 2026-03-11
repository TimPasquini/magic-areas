# Implementation Plan (Current)

This is the active implementation plan for architecture work after the original
fork baseline (`d7b5779`).

This file reflects **current structure and priorities**.
Historical decomposition details are intentionally omitted to avoid drift.

## Goals

- preserve user-facing behavior while improving internal composition
- keep coordinator snapshot as the runtime read contract
- keep policy deterministic and execution centralized
- reduce duplicated patterns and cross-module side-door access
- improve maintainability for new feature/group capabilities

## Non-goals

- redesign core user workflows during structural work
- broad feature expansion unrelated to active refactor streams
- introducing temporary shims that are not removed promptly

## Constraints

- Python 3.13+
- Home Assistant async integration patterns
- strict typing with mypy
- full test suite must remain green

## Current architecture status

Authoritative layer status is tracked in:
- `docs/notes/theoretical_architecture_map.md`

Snapshot of current state:
- Layer 1 (Snapshot/Ingestion): Implemented
- Layer 2 (Feature Modules): Implemented
- Layer 3 (Policy Layer): Implemented
- Layer 4 (Execution Layer): Implemented
- Layer 5 (Groups): Partial
- Layer 6 (Entities): Partial
- Layer 7 (Platforms): Implemented
- Layer 8 (Config Flow): Implemented
- Layer 9 (Constants/Enums): Partial

## Completed streams (high impact)

- Coordinator-owned ingestion package and snapshot models
- Feature-module composition path across platforms
- Canonical control-group policy contract adoption for light/fan/climate/media
- Typed policy signal payloads at runtime boundaries
- Canonical runtime effects in `ControlGroupDecision`
- Shared runtime effect execution support in executor boundary
- Policy purity contract coverage

## Active priorities

### Priority 1: Layer 6 entity thinning

Target:
- reduce policy/execution glue still embedded in entities/events
- align entity/event handlers to adapter-only responsibilities

Expected work:
- move reusable orchestration logic into shared runtime helpers
- keep entity code focused on lifecycle + dispatch wiring
- remove duplicate event transition handling where shared patterns exist

Acceptance criteria:
- entity/event modules become smaller and more uniform
- no policy-side effects introduced
- full quality gates pass

### Priority 2: Layer 5 group-model consolidation

Target:
- make control/aggregate group lifecycle and lookup behavior consistent

Expected work:
- align registration, resolution, and precedence paths
- reduce feature-specific custom lookup branches
- tighten group metadata contracts

Acceptance criteria:
- shared group lookup patterns across features
- fewer per-feature fallback paths
- parity tests remain green

### Priority 3: Layer 9 constants/enums cleanup

Target:
- keep central constants files limited to true cross-cutting values

Expected work:
- move module-specific tuning constants closer to owning modules
- reduce broad consumer fan-out from central constants files
- preserve public config key contracts while reducing incidental coupling

Acceptance criteria:
- narrower constant dependency surface
- no config behavior regression
- mypy/ruff/pytest green

## Cross-cutting rules for all phases

1. No behavior change unless explicitly scoped and tested.
2. No long-lived shims after replacement path is validated.
3. Policy remains pure; execution remains centralized.
4. Boundary changes must include contract tests.
5. Keep docs synchronized with actual implementation state.

## Required validation commands

```bash
uv run ruff check custom_components/magic_areas tests
uv run mypy custom_components/magic_areas tests
uv run pytest ./tests --numprocesses=auto -q
```

## Working notes and detailed plans

Use targeted notes under `docs/notes/` for stream-specific detail, including:
- `docs/notes/theoretical_architecture_map.md`
- `docs/notes/layer3_policy_completion_plan.md`
- `docs/notes/light_system_recomposition_plan.md`
- `docs/notes/entity_loading_packaging_plan.md`

## Update policy

When a stream or phase state changes:
1. update the corresponding `docs/notes/*` plan/status file first,
2. update this implementation plan summary,
3. ensure `docs/contributing/refactoring-guide.md` remains consistent.
