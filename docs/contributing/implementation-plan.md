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
- Layer 5 (Groups): Implemented
- Layer 6 (Entities): Implemented
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
- Layer 5 group-model consolidation:
  - canonical group/policy contracts (`core/group_contracts.py`)
  - typed metadata contracts (`core/group_metadata.py`)
  - deterministic metadata-based resolution for fan/climate/media targets
  - unified metadata-filtered runtime lookup surface for aggregate/control paths
  - custom-group guardrails in schema + normalization
  - stale-default prevention across rebuild cycles
- Layer 9 progress:
  - moved fan/climate/wasp/presence-hold/aggregate/media feature defaults into
    feature-local default modules
  - reduced cross-cutting `defaults.py` to area-level shared defaults only
  - removed duplicated empty-string constants from `const.py`/`config_keys.py`
    and localized empty-name handling at call sites
  - moved sensor display precision and presence polling interval constants to
    their owning modules
  - kept config-flow light-tracking extras in
    `config_flows/entity_gatherer.py` (instead of global `const.py`)
  - split `config_keys` into a package with feature/domain-scoped key modules
    while preserving `custom_components.magic_areas.config_keys` public imports
  - migrated nearly all source imports to scoped key modules
    (`config_keys.area`, `config_keys.entities`, etc.); only mixed-purpose
    schema/config-flow forms still use broad imports

## Active priorities

### Priority 1: Layer 9 constants/enums cleanup

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
