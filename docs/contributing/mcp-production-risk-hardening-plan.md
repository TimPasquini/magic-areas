# MCP-Driven Production Risk Hardening Plan

## Scope

This plan addresses risks surfaced by `code-review-graph` analysis that are not covered well by pass/fail quality gates (`pytest`, `mypy`, `ruff`):

1. Core-layer boundary inversion (`core -> features.config.readers` imports).
2. High cross-community coupling hotspots.
3. High blast-radius lifecycle/meta/snapshot paths.
4. Graph analysis blind spots caused by test exclusion.

## Baseline Findings (From MCP)

- Cross-community coupling warnings:
  - `controls-group <-> features-feature` (21 edges)
  - `config-flows-step <-> schemas-selector` (17 edges)
  - `magic-areas-id <-> features-feature` (16 edges)
- High blast radius for lifecycle/meta/snapshot changes:
  - 43 directly changed nodes
  - 487 impacted nodes (2 hops)
  - 139 impacted files
- High-complexity hotspots:
  - `core/meta_reload.py::evaluate_reload` (110 lines)
  - `core/runtime_model/references.py::build_entity_references` (89 lines)
  - `coordinator/pipeline/snapshot.py::build_snapshot` (87 lines)
  - `light_groups/policy.py::LightGroupPolicy.evaluate` (82 lines)

## Operating Constraints

- Preserve Home Assistant integration contracts (`async_setup_entry`, platform setup shape, dispatcher/listener cleanup semantics).
- Preserve runtime behavior while moving boundaries. Any behavior change requires an explicit note and dedicated test.
- Prefer additive refactors (new helper + migrate call sites + delete old path) over in-place rewrites.
- No new `ignore`/`cast`/`Any` workarounds as part of this effort.

## Plan of Record

### Phase 0: Lock in Graph Signal Quality

Goal: Ensure MCP analysis remains trustworthy and reproducible.

Implementation tasks:
1. Remove/neutralize any graph ignore that excludes tests.
2. Document the required pre-analysis graph build workflow in contributing docs.
3. Add a lightweight “graph sanity checklist” section:
   - tests included
   - graph rebuilt after structural changes
   - architecture/impact checks run from repo root
4. Record expected rough baseline graph stats in docs for quick drift detection.

Validation commands:
- `uvx code-review-graph build`
- `mcp__code_review_graph__list_graph_stats_tool`

Exit criteria:
- Graph stats show substantial `Test` nodes and `TESTED_BY` edges.
- Documented workflow exists and is discoverable in `docs/contributing`.
- Team can repeat the same commands and get equivalent signal quality.

Failure conditions:
- Graph excludes tests or returns mostly empty `tests_for` relationships.
- Architecture review is performed without a rebuild after changes.

### Phase 1: Remove Core Boundary Inversion (`core -> features.config.readers`)

Goal: Eliminate production dependency inversion where domain/policy code in `core` reads feature-layer adapters.

Implementation tasks:
1. Inventory all `core` imports of `features.config.readers`.
2. Define core-owned config access boundary in `core/config`:
   - typed option readers/value objects for aggregates
   - typed option readers/value objects for control policies
3. Move normalization/defaulting logic needed by `core` into `core/config` helpers.
4. Refactor core call sites to depend on new core config APIs.
5. Narrow `features.config.readers` to an adapter module consumed by feature/platform edge code only.
6. Remove old import paths and dead compatibility branches.

Primary likely file set:
- `custom_components/magic_areas/core/aggregates/runtime.py`
- `custom_components/magic_areas/core/aggregates/selection.py`
- `custom_components/magic_areas/core/controls/policies/climate.py`
- `custom_components/magic_areas/core/controls/policies/fan.py`
- `custom_components/magic_areas/core/config/feature.py`
- `custom_components/magic_areas/features/config/readers.py`

Required tests:
- Existing unit tests around aggregates and policies.
- New unit tests for any new core config helper.
- Integration parity tests for lifecycle/feature behaviors touched by moved defaults.

Exit criteria:
- No production file under `custom_components/magic_areas/core/` imports `custom_components.magic_areas.features.config.readers`.
- Behavior parity maintained (all existing tests pass).
- New helpers have direct unit tests for defaults and edge values.

Failure conditions:
- Refactor shifts behavior silently (for example default semantics change).
- New dependencies reintroduce reverse imports indirectly through helper modules.

### Phase 2: Enforce Boundary Contracts in Tests

Goal: Convert architectural intent into hard CI-enforced guarantees.

Implementation tasks:
1. Extend import-boundary rules in `tests/unit/test_import_boundaries.py`:
   - explicit deny path for `core -> features.config`
   - keep allowlists minimal and time-bounded
2. Add a targeted contract test for adapter seam ownership:
   - verify feature config adapters remain outside core domain modules
3. Add comments in boundary test definitions documenting rationale for each rule.
4. Remove stale allowlist entries once Phase 1 lands.

Validation commands:
- `uv run pytest tests/unit/test_import_boundaries.py -q`

Exit criteria:
- Boundary tests fail on intentional synthetic violation and pass when reverted.
- No stale allowlist entries remain for the removed inversion.
- Rule intent is documented for future contributors.

Failure conditions:
- Broad allowlist exceptions that nullify the rule.
- Test only checks one direct import and misses package-level leakage.

### Phase 3: Reduce Blast Radius in Lifecycle/Meta/Snapshot Paths

Goal: Decompose high-impact orchestration into testable units to lower change risk.

Priority targets:
- `custom_components/magic_areas/coordinator/pipeline/lifecycle.py`
- `custom_components/magic_areas/core/meta_reload.py::evaluate_reload`
- `custom_components/magic_areas/coordinator/pipeline/snapshot.py::build_snapshot`

Implementation tasks:
1. For each target, separate layers explicitly:
   - pure decision logic
   - side-effect orchestration (events, HA calls, scheduling)
2. Introduce typed input/output dataclasses for decision steps where useful.
3. Extract deterministic helpers and cover them with focused unit tests.
4. Keep orchestration wrappers thin and covered by integration tests.
5. Remove duplicated conditional branches discovered during extraction.

Recommended decomposition checkpoints:
- `evaluate_reload`: split trigger classification, child-area readiness checks, retry decision.
- `build_snapshot`: split source data collection, reference resolution, feature metadata assembly.
- lifecycle manager: split readiness convergence policy from task scheduling and guard timers.

Validation commands:
- `uv run pytest tests/unit -q`
- `uv run pytest tests/integration/test_coordinator_lifecycle.py -q`
- `mcp__code_review_graph__get_impact_radius_tool` after each major refactor slice

Exit criteria:
- Each hotspot function reduced to smaller composable units.
- New unit tests cover extracted pure logic branches.
- Integration behavior remains unchanged.
- Follow-up CRG impact on equivalent diffs trends downward (nodes/files affected).

Failure conditions:
- Refactor mixes decision and side effects in extracted helpers.
- Blast radius remains flat because moves are superficial (no actual decoupling).

### Phase 4: Triage Coupling Hotspots (Keep Intentional, Remove Accidental)

Goal: Reduce accidental coupling while preserving necessary HA/platform wiring.

Hotspots to triage first:
- `controls-group <-> features-feature`
- `config-flows-step <-> schemas-selector`
- `magic-areas-id <-> features-feature`

Implementation tasks:
1. For each hotspot, produce an edge-level classification table:
   - edge
   - why it exists
   - intentional vs accidental
   - action (keep, move, split, delete)
2. Attack accidental edges first:
   - move shared semantics to neutral domain modules
   - collapse duplicated translation/conversion code
   - remove convenience imports that bypass boundaries
3. Keep intended coupling explicit and documented (entrypoint/platform integration).
4. Re-run architecture overview and compare warning counts.

Validation commands:
- `mcp__code_review_graph__get_architecture_overview_tool`
- `mcp__code_review_graph__query_graph_tool` (`importers_of`, `callers_of`) on hotspots

Exit criteria:
- Every hotspot has a documented disposition.
- At least one high-coupling pair shows measurable reduction in edge count.
- Remaining high coupling is documented as intentional with rationale.

Failure conditions:
- Coupling reduction is achieved by hiding imports rather than changing ownership.
- Necessary HA integration edges are removed and recreated elsewhere as implicit coupling.

## Execution Tracking Template (Per PR)

- Phase:
- Target files:
- Boundary rule changes:
- Behavior changes (expected none unless noted):
- Tests run:
- CRG outputs captured:
- Residual risk:
- Follow-up tasks:

## Test Strategy Per Phase

- Run targeted unit tests first for touched modules.
- Run affected integration suites for lifecycle/reload/snapshot behavior.
- Run `ruff` and `mypy` before full test pass to catch fast failures.
- Run full suite before merge.
- Re-run CRG architecture + impact analysis after each phase to validate structural improvements.

## Rollout Strategy

- Keep behavior-preserving changes separate from policy changes.
- For risky refactors, use temporary compatibility shims with explicit cleanup tickets.
- Prefer merge order: Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 4.
- Do not start Phase 3 decomposition until Phase 2 contract tests are green and protecting boundaries.

## Definition of Done

All of the following are true:

- Boundary inversion removed (`core` no longer depends on `features.config.readers`).
- Boundary tests enforce the rule permanently.
- High-blast-radius paths are decomposed with retained behavior.
- CRG signal remains test-aware and usable.
- Coupling hotspots are either reduced or explicitly justified as intentional architecture.
- Documentation reflects final boundaries and review workflow.

## Current Status (2026-04-17)

- Phase 1 in progress, major objective completed:
  - Core no longer imports `features.config.readers` for aggregate/control policy paths.
  - New core-owned readers live in `core/config/feature_readers.py`.
- Phase 2 in progress:
  - Ownership rules added for former inversion modules.
  - Added package-level guard that blocks all `core -> features.config` imports.
- Phase 3 in progress:
  - `core/meta_reload.py::evaluate_reload` decomposed into pure helper steps.
  - `coordinator/pipeline/snapshot.py::build_snapshot` split into smaller helper functions.
  - `coordinator/pipeline/lifecycle.py` now uses pure meta reload planning (`build_meta_reload_plan`) and explicit schedule selection helper.
  - `coordinator/pipeline/lifecycle.py` readiness convergence now uses pure request planning (`build_readiness_request_plan`) for window/cap/pending-handle decisions.
  - `coordinator/pipeline/lifecycle.py` readiness state transition checks and registry `changes.area_id` parsing are now centralized in pure helpers.
  - `coordinator/pipeline/lifecycle.py` meta snapshot retry bounding now uses pure retry planning (`build_meta_snapshot_retry_plan`) for schedule-vs-drop decisions.
  - `coordinator/pipeline/lifecycle.py` callback coalescing now uses pure schedule planning (`build_reload_schedule_plan`) and `evaluate_and_schedule_reload` now uses shared schedule helper path.
  - `coordinator/pipeline/lifecycle.py` registry-listener setup now centralizes merged config/options and runtime snapshot access in dedicated helpers.
  - `coordinator/pipeline/lifecycle.py` readiness request entry-gates now use pure gating (`build_readiness_gate_plan`) covering disabled/not-running/in-flight decisions.
  - `core/runtime_model/references.py::build_entity_references` reduced to declarative spec loop.
- Phase 4 in progress:
  - Reduced accidental `config-flows-step -> schemas-selector` coupling by introducing a config-flow-local selector seam (`config_flows/selector_builders.py`) and moving step imports to that seam.
  - Boundary contract updated to keep exactly one explicit schema-selector adapter edge (`config_flows.selector_builders -> schemas.selectors`), avoiding direct step-level side-door imports.
  - Switch control modules now consume core-owned config readers (`core.config.feature_readers`) instead of `features.config.readers` for climate/fan/presence-hold paths.
  - Binary-sensor runtime modules now consume core-owned config readers for BLE and Wasp feature config access (`aggregate_factory`, `ble_tracker`, `wasp_in_a_box`).
  - Boundary allowlist now tracks six explicit side-door edges (`switch` and selected `binary_sensor` modules -> `core.config.feature_readers`) while preserving facade constraints on `core.config.__all__`.
  - Top-level platform setup modules now use a local dispatch facade (`platform_dispatch.py`) instead of importing `features.dispatch` directly; this collapses repeated feature-boundary imports into one owned adapter seam.
  - Config-flow feature step key handling now reads directly from `config_keys.area` constants (instead of `features.config.readers` alias constants), reducing non-runtime coupling to feature adapters.
  - Legacy feature/group ID builders were moved out of `feature_info.py` into `core/runtime_model/feature_ids.py`; runtime resolution and feature modules now consume that core-owned helper module, and `feature_info.py` is metadata-only again.
  - Runtime feature metadata lookup (`get_feature_info`) moved to the root `feature_registry.py` facade with lazy registry resolution; this keeps `feature_info.py` as a pure metadata contract and avoids `entity -> feature_registry -> features.registry -> binary_sensor -> entity` import cycles.
  - Feature modules now consume a features-local control adapter seam (`features/control_builders.py`) instead of importing `core.controls` and `core.controls.builders` directly, reducing repeated cross-community edges.
  - Config-flow selector imports now route through module-level adapter aliases in `config_flows/selector_builders.py`, preserving boundary contracts while reducing symbol-level coupling noise.
  - Follow-up CRG architecture warnings remain unchanged (`10 warnings`, including `controls-group <-> features-feature`, `config-flows-step <-> schemas-selector`, `magic-areas-id <-> features-feature`), indicating remaining hotspots are dominated by structural ownership/test coupling rather than import syntax.
  - Added root-level registry facade (`feature_registry.py`) and moved non-feature callers (`config_flows.base`, `config_flows.steps.feature_config`, `schemas.features`, `feature_info`) to consume it, reducing repeated direct imports of `features.registry`.
  - Added root-level feature contract facade (`feature_contracts.py`) and moved non-feature callers (`config_flows.base`, `schemas.features`) off direct `features.base` imports.

Validation snapshot:
- `uv run ruff check custom_components/magic_areas tests` passes.
- `uv run mypy custom_components/magic_areas tests` passes.
- `uv run pytest tests -q` passes (`1007 passed`).
