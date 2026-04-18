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

### Architecture Correction: Feature Metadata/Registry Split (Two-Door Model)

Goal: Remove lazy registry loading and make feature ownership explicit without reintroducing import cycles.

Corrected structure:
1. Metadata door (pure contract):
   - `feature_info.py` owns `FeatureInfo` and canonical metadata lookup (`FEATURE_INFO_BY_FEATURE`, `get_feature_info`).
   - This module must remain free of `features.modules` / registry-construction imports.
2. Runtime registry door (module wiring):
   - `features/registry.py` owns feature-module registration, availability/configurability logic, and dependency validation.
   - It may consume metadata from `feature_info.py`, but metadata lookups used by base entities must not require importing the runtime registry.
3. Facade policy:
   - Root `feature_registry.py` should be a thin compatibility seam (or removed after migration), not a lazy-proxy behavior layer.
   - Avoid introducing import-time global proxies that obscure ownership.

Rationale:
- Current lazy facade avoided a real cycle (`entity -> feature_registry -> features.registry -> features.modules -> binary_sensor -> entity`) but adds complexity and weakens clarity.
- Two explicit doors preserve boundary intent while allowing strict typing and simpler runtime behavior.

Implementation tasks:
1. Move canonical feature metadata map/builders into `feature_info.py` as pure data/functions.
2. Update `entity.py` to read metadata via metadata door only.
3. Update `features/catalog.py` and `features/registry.py` to consume metadata from `feature_info.py` (one-way dependency).
4. Replace lazy proxy in `feature_registry.py` with direct compatibility exports (or remove module after callsite migration).
5. Update docs (`features/AGENTS.md`) to reflect corrected ownership.

Validation commands:
- `uv run ruff check custom_components/magic_areas tests`
- `uv run mypy custom_components/magic_areas tests`
- `uv run pytest tests/unit/test_import_boundaries.py -q`
- `uv run pytest tests -q`

Exit criteria:
- No lazy-proxy registry object remains in root facade.
- `entity.py` no longer depends on runtime feature registry construction path.
- Feature metadata remains available without importing `features.modules`.
- Full lint/type/tests pass.

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

### Phase 4: Structural Ownership Alignment (Two-Door Model)

Goal: Align architecture to explicit ownership boundaries so coupling reductions come from real structural changes, not import-shape churn.

Primary structure targets:
- Two-door feature boundary:
  - Metadata door (`feature_info`) is pure/static and safe for base runtime consumers.
  - Runtime registry door (`features.registry`) owns module wiring/enabling/dependency logic.
- Boundary contracts enforce ownership intent first, and only pin exact import paths for explicitly intentional seams.

Hotspots to resolve with this model:
- `controls-group <-> features-feature`
- `config-flows-step <-> schemas-selector`
- `magic-areas-id <-> features-feature`

Implementation tasks:
1. Produce ownership maps for each hotspot:
   - source owner
   - target owner
   - intentional vs accidental relationship
   - required move/split/keep decision
2. Execute ownership moves before path cleanups:
   - separate metadata responsibilities from runtime registry wiring
   - remove accidental cross-slice dependencies by relocating shared semantics to true owners
   - keep compatibility shims temporary and explicitly tracked
3. Recalibrate boundary tests:
   - preserve no-side-door guarantees
   - avoid brittle path-shape constraints where equivalent ownership is maintained
4. Re-run CRG architecture checks and classify residual warnings as:
   - improved by ownership changes
   - intentional and accepted
   - deferred with rationale

Validation commands:
- `mcp__code_review_graph__get_architecture_overview_tool`
- `mcp__code_review_graph__query_graph_tool` (`importers_of`, `callers_of`) on ownership seams
- `uv run pytest tests/unit/test_import_boundaries.py -q`

Exit criteria:
- Two-door feature boundary is implemented and documented.
- Boundary tests reflect ownership intent and remain strict on side-door growth.
- Residual hotspot warnings are explicitly classified (intentional vs follow-up), with rationale.
- Coupling changes are evidenced by ownership simplification, not only by edge-count movement.

Failure conditions:
- Import path reshuffling is used as a substitute for ownership correction.
- New hidden/global indirection is introduced (for example lazy proxy seams) to bypass structural fixes.
- Boundary rules become so specific that they block equivalent ownership-preserving simplifications.

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

## Phase Closure Evaluation (2026-04-18)

Packet used:
- `docs/contributing/phase-closure-packet.md`

Binary closure status:
- Architecture Correction (Two-Door Model): `COMPLETE`
- Phase 0 (Graph Signal Quality): `COMPLETE`
- Phase 1 (Core Boundary Inversion Removal): `COMPLETE`
- Phase 2 (Boundary Contracts): `COMPLETE`
- Phase 3 (Blast Radius/Hotspot Reduction): `COMPLETE`
- Phase 4 (Structural Ownership Alignment): `COMPLETE`

Phase 2 validation note:
- Synthetic violation proof was executed in-session:
  - intentional temporary `core -> features.config` import caused boundary test fail
  - immediate revert restored boundary suite to pass

Evidence source:
- Full command/output checklist is recorded in
  `docs/contributing/phase-closure-packet.md` under
  `Execution Report (2026-04-18)`.

## Current Status (2026-04-18)

Execution state:
- Streams A, B, and C are complete.
- Plan now transitions from boundary cleanup to hotspot/coupling reduction.

Completed outcomes:
- Temporary runtime side-door debt removed:
  - `runtime_core` allowlist entries reduced from 6 to 0.
- Intentional seams are explicit and documented:
  - runtime: `config_flows.selector_builders -> schemas.selectors`
  - tests: implementation-contract seams for `light_groups` and `switch.base`
- Reader ownership is now explicit and enforced:
  - `core.config.feature_readers` is core-domain only.
  - `features.config.readers` is feature/edge adapter surface.
- Reader duplication was reduced and shared generic scaffolding centralized in
  `custom_components.magic_areas.feature_reader_common`.

Validation snapshot (latest full gate run in Stream C):
- `uv run ruff check custom_components/magic_areas tests` passes.
- `uv run mypy custom_components/magic_areas tests` passes.
- `uv run pytest tests -q` passes (`1008 passed`).

Live MCP snapshot (2026-04-18 pull):
- Graph stats:
  - files: 295
  - nodes: 2388
  - edges: 17956
  - tests: 936
  - `TESTED_BY` edges: 5130
  - graph updated: `2026-04-17T23:23:26`
- Architecture warnings: 8 total.
  - remaining product-relevant warning:
    - `controls-group <-> features-feature` (21 edges)
  - other top warnings are test-coupling heavy (`tests-* <-> *`) and should be
    tracked separately from production architecture debt.
- Large-function hotspots still open:
  - `core/meta_reload.py::evaluate_reload` (110 lines)
  - `core/runtime_model/references.py::build_entity_references` (89 lines)
  - `coordinator/pipeline/snapshot.py::build_snapshot` (87 lines)
  - `light_groups/policy.py::LightGroupPolicy.evaluate` (82 lines)

## Boundary Census Integration (2026-04-18)

Reference census:
- `docs/contributing/boundary-census-2026-04-18.md`

How to use it in this plan:
1. Keep census classifications as the contract baseline:
   - temporary seams must trend to zero
   - intentional seams stay explicit and documented
2. Validate no regression in allowlist growth as Streams D/E/F execute.
3. Use census ownership notes when evaluating whether a coupling warning is:
   - accidental structural coupling
   - intentional adapter seam

Post-Streams A/B/C state:
- `runtime_core` cleanup objective is complete (6 -> 0).
- Census follow-up now moves to preventing regression and guiding hotspot cuts.

## Execution Mode (Incremental Commits)

This plan is executed directly on `main` with incremental commits (no PR queue).

Rules for this execution mode:
- Each commit should close one bounded checklist slice.
- Each commit must include acceptance evidence (tests/linters run).
- Keep behavior-preserving refactors separate from any behavior changes.
- Update this plan after each commit with status and residual risk.

## Active Cleanup Queue (Census-Driven)

### Stream A: Runtime Core Allowlist Debt (`runtime_core` = 6 -> 0)

Scope:
- Remove temporary side-door exceptions where non-core modules import
  `core.config.feature_readers`.

Checklist:
- [x] Confirm target owner surface for non-core feature readers.
- [x] Migrate `binary_sensor.aggregate_factory` reader imports.
- [x] Migrate `binary_sensor.ble_tracker` reader imports.
- [x] Migrate `binary_sensor.wasp_in_a_box` reader imports.
- [x] Migrate `switch.__init__` reader imports.
- [x] Migrate `switch.climate_control` reader imports.
- [x] Migrate `switch.fan_control` reader imports.
- [x] Remove migrated `runtime_core` allowlist entries.
- [x] Run targeted boundary tests.
- [x] Run focused unit/platform tests for touched modules.
- [x] Run full quality gates.

Acceptance criteria:
- No non-core runtime module imports `custom_components.magic_areas.core.config.feature_readers`.
- `ALLOWLIST_OVERRIDES["runtime_core"]` is empty/removed.
- `uv run pytest tests/unit/test_import_boundaries.py -q` passes.
- `uv run ruff check custom_components/magic_areas tests` passes.
- `uv run mypy custom_components/magic_areas tests` passes.
- `uv run pytest tests -q` passes.

Exit criteria:
- Completed checklist with evidence logged.
- No new allowlist entries introduced in any bucket.
- No behavior changes observed in touched feature/platform paths.

Status (2026-04-18):
- Completed.
- Evidence:
  - `uv run pytest tests/unit/test_import_boundaries.py tests/unit/test_listener_entity_write_contracts.py tests/unit/test_listener_entity_lifecycle_contracts.py tests/unit/test_switch_base_write_contract.py tests/unit/test_feature_module_contracts_control_groups.py -q` (pass)
  - `uv run ruff check custom_components/magic_areas tests` (pass)
  - `uv run mypy custom_components/magic_areas tests` (pass)
  - `uv run pytest tests -q` (pass, `1008 passed`)

### Stream B: Intentional Seam Documentation Tightening

Scope:
- Keep intentional seams explicit and prevent reclassification churn.

Checklist:
- [x] Add rationale comments for intentional-permanent allowlist entries.
- [x] Mark test-only seams as implementation-contract seams.
- [x] Ensure schema selector adapter seam is documented as intentional.
- [x] Re-run boundary tests.

Acceptance criteria:
- Intentional seams are documented inline in boundary tests and docs.
- No runtime allowlist growth.

Exit criteria:
- Documentation and tests agree on intentional seams.

Status (2026-04-18):
- Completed.
- Evidence:
  - `uv run pytest tests/unit/test_import_boundaries.py -q` (pass)

### Stream C: Reader Ownership Consolidation Decision

Scope:
- Resolve duplicated reader surfaces (`core/config/feature_readers.py` vs
  `features/config/readers.py`) under two-door ownership intent.

Checklist:
- [x] Decide canonical ownership for non-core reader usage.
- [x] Map required exports/functions by consumer type (core vs edge/features).
- [x] Remove one-way duplication without reintroducing cycles.
- [x] Re-run boundary/type/behavior tests.

Acceptance criteria:
- Single clear ownership model documented and enforced by imports/tests.
- No duplicate reader logic maintained in parallel for the same consumer class.

Exit criteria:
- Census no longer flags reader-surface duplication as primary friction.

Ownership decision (2026-04-18):
- `core.config.feature_readers` is core-domain only.
  - Allowed consumers: `core/aggregates/*`, `core/controls/policies/*`.
- `features.config.readers` is feature/edge adapter surface.
  - Allowed consumers: `features/modules/*`, platform/entity edge adapters
    (for example `switch/*`, `binary_sensor/*`).
- Rationale:
  - Preserves `core -> features.config` ban.
  - Preserves no-side-door rules for core internals.
  - Keeps non-core runtime modules out of core-internal feature reader paths.

Status (2026-04-18):
- Completed.
- Completed in this step:
  - ownership decision and consumer mapping.
- Completed in follow-up sub-step:
  - reduced duplicated reader surface by removing edge-only readers from
    `core.config.feature_readers` (`ble_tracker`, `presence_hold`,
    `wasp_in_a_box`).
- Completed in second follow-up sub-step:
  - reduced duplicated reader surface by removing core-owned aggregate/health
    reader implementations from `features.config.readers`.
- Completed in third follow-up sub-step:
  - removed climate/fan reader overlap from `core.config.feature_readers` by
    moving core climate/fan policy config parsing to policy-local builders
    backed by generic config helpers/defaults.
- Completed in optional follow-up sub-step:
  - deduplicated shared generic reader scaffolding
    (`FeatureOptions`/`options_for_feature`) into
    `custom_components.magic_areas.feature_reader_common`.
- Remaining:
  - none for Stream C scope.

Status:
- Stream C acceptance criteria fully met.

### Stream D: Lifecycle/Snapshot Hotspot Decomposition (Phase 3 Continuation)

Scope:
- Reduce blast radius in remaining large orchestration functions while keeping
  behavior stable.

Checklist:
- [x] Slice `core/meta_reload.py::evaluate_reload` into pure decision helpers +
  thin side-effect wrapper.
- [x] Further decompose `coordinator/pipeline/snapshot.py::build_snapshot`
  into deterministic data assembly helpers.
- [x] Revisit `core/runtime_model/references.py::build_entity_references`
  and split remaining mixed concerns (collection vs shaping).
- [x] Add focused unit tests for extracted pure helper branches.
- [x] Re-run targeted lifecycle/snapshot integration tests.

Acceptance criteria:
- Hotspot functions are reduced in size/branching with equivalent behavior.
- Extracted pure helpers are directly unit-tested.
- `uv run pytest tests/unit -q` and affected integration tests pass.

Exit criteria:
- MCP `find_large_functions` no longer lists at least two of the three primary
  production hotspots above the current threshold.
- No net increase in boundary allowlist entries.

Status (2026-04-18):
- Completed.
- Completed in this sub-step:
  - `build_entity_references` now separates:
    - deterministic spec construction (`_build_reference_specs`)
    - registry lookup collection
    - runtime object shaping (`_shape_entity_references`)
  - `evaluate_reload` now separates:
    - precondition evaluation (`_evaluate_reload_preconditions`)
    - positive decision shaping (`_build_scheduled_reload_decision`)
  - added focused unit tests for extracted pure helpers in:
    - `tests/unit/test_core_entity_ids_references.py`
    - `tests/unit/test_core_meta_reload.py`
- Validation (sub-step):
  - `uv run ruff check custom_components/magic_areas/core/runtime_model/references.py custom_components/magic_areas/core/meta_reload.py tests/unit/test_core_entity_ids_references.py tests/unit/test_core_meta_reload.py` (pass)
  - `uv run mypy custom_components/magic_areas/core/runtime_model/references.py tests/unit/test_core_entity_ids_references.py` (pass)
  - `uv run mypy custom_components/magic_areas/core/meta_reload.py tests/unit/test_core_meta_reload.py` (pass)
  - `uv run pytest tests/unit/test_core_meta_reload.py tests/unit/test_core_entity_ids_references.py tests/unit/test_core_entity_ids_builders.py -q` (pass)
- Remaining for Stream D:
  - none

Completed in second sub-step (snapshot):
- `build_snapshot` now separates:
  - feature config normalization (`_resolve_feature_config`)
  - presence projection assembly (`_resolve_presence_projection`)
  - final snapshot object shaping (`_build_magic_areas_data`)
- added focused helper test in:
  - `tests/unit/test_entity_ingestion_contract.py`
- additional validation:
  - `uv run ruff check custom_components/magic_areas/coordinator/pipeline/snapshot.py tests/unit/test_entity_ingestion_contract.py` (pass)
  - `uv run mypy custom_components/magic_areas/coordinator/pipeline/snapshot.py tests/unit/test_entity_ingestion_contract.py` (pass)
  - `uv run pytest tests/unit/test_entity_ingestion_contract.py tests/integration/test_coordinator_lifecycle.py -q` (pass)
  - `uv run code-review-graph build --repo . --skip-flows` (pass)
  - `mcp__code_review_graph__list_graph_stats_tool` refreshed timestamp:
    - `2026-04-18T18:09:48`
  - `mcp__code_review_graph__find_large_functions_tool` (>=80):
    - `build_snapshot` and `build_entity_references` no longer listed
    - `evaluate_reload` reduced to 81 lines

### Stream E: Coupling Warning Triage and Ownership Cuts (Phase 4 Continuation)

Scope:
- Close or explicitly classify remaining production architecture warnings.

Checklist:
- [x] Produce warning-by-warning classification:
  - accidental and actionable
  - intentional and documented
  - test-coupling noise (tracked separately)
- [x] Target `controls-group <-> features-feature` with ownership-preserving
  structural cuts.
- [x] Re-run architecture overview after each structural slice.
- [x] Update boundary tests only where ownership intent changes, not for path
  reshuffling.

Acceptance criteria:
- Remaining production warnings are either reduced or explicitly justified.
- Boundary contracts remain strict on side-door prevention.

Exit criteria:
- Architecture warning set has explicit per-warning disposition recorded in this
  plan (resolved/intentional/deferred).

Status (2026-04-18):
- Completed.
- Production warning triage summary:
  - No active production-to-production warning currently requires a structural
    ownership move.
  - Prior hotspot `controls-group <-> features-feature` is no longer emitted as
    a top warning after Streams C/D and full graph postprocess.

Warning-by-warning disposition (MCP architecture refresh):
- `tests-mock <-> platforms-setup` (388): `test-coupling noise`
- `core-group <-> unit-area` (243): `intentional test pressure` on core APIs
- `tests-mock <-> integration-area` (232): `test-coupling noise`
- `pipeline-reload <-> unit-area` (37): `intentional test pressure` on
  lifecycle/meta reload planners
- `features-feature <-> unit-area` (28): `intentional test pressure` on feature
  module contracts
- `tests-mock <-> snapshots-snapshot` (14): `test-coupling noise`
- `binary-sensor-sensor <-> unit-area` (13): `intentional test pressure` on
  binary sensor runtime behavior
- `magic-areas-async <-> integration-area` (12): `intentional integration
  coupling`

Controls/features ownership seam review:
- Evaluated narrowing `features/control_builders.py` to import
  `core.controls.control_group` directly.
- Rejected/reverted because boundary tests correctly flag it as a side-door
  import into core internals.
- Kept existing owned adapter seam (`features.control_builders ->
  core.controls` facade) to preserve no-side-door guarantees without allowlist
  growth.

Validation:
- `uv run code-review-graph postprocess --repo .` (pass)
- `mcp__code_review_graph__get_architecture_overview_tool` (8 warnings
  classified above)
- `uv run pytest tests/unit/test_import_boundaries.py tests/unit/test_feature_module_contracts_control_groups.py -q` (pass)

### Stream F: CRG Signal Hygiene Lock-In (Phase 0 Completion)

Scope:
- Make test-inclusive MCP signal reproducible and non-optional.

Checklist:
- [x] Confirm graph build path and ignore configuration include tests by
  default.
- [x] Document required rebuild cadence and minimum sanity checks.
- [x] Add a short "do not trust stale graph" guard section with timestamp/size
  expectations.

Acceptance criteria:
- Team members can rerun graph build + stats and get test-aware signal.
- Docs include explicit sanity checks and failure modes.

Exit criteria:
- Graph workflow is documented as a repeatable baseline, not tribal knowledge.

Status (2026-04-18):
- Completed.
- Completed in this stream:
  - Confirmed `.code-review-graphignore` is empty (tests are not excluded).
  - Added reproducible graph hygiene workflow doc:
    - `docs/contributing/mcp-graph-hygiene.md`
  - Added runtime-boundary policy pointer to graph hygiene workflow:
    - `docs/contributing/runtime-boundaries.md`
  - Captured baseline sanity stats and stale-graph guardrails in docs.

Validation:
- `uv run code-review-graph build --repo .` (pass)
- `uv run code-review-graph postprocess --repo .` (pass)
- `mcp__code_review_graph__list_graph_stats_tool`:
  - files: `302`
  - nodes: `2479`
  - edges: `18321`
  - test nodes: `966`
  - `TESTED_BY` edges: `5202`
  - `last_updated`: `2026-04-18T18:09:48`

## Commit Log (Incremental)

Use this section as an append-only execution ledger.

- `2026-04-18`: `9f28fd6` - `Stream F / graph hygiene workflow + stale-signal guardrails`  
  - Files:  
    - `docs/contributing/mcp-graph-hygiene.md`
    - `docs/contributing/runtime-boundaries.md`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Validation:
    - `uv run code-review-graph build --repo .`
    - `uv run code-review-graph postprocess --repo .`
    - `mcp__code_review_graph__list_graph_stats_tool`
  - Result:  
    - Stream F completed with documented build/postprocess workflow, sanity
      checklist, and stale-graph guard guidance.
  - Residual risk:
    - Graph interpretation still requires human classification for
      test-coupling-heavy warnings.
- `2026-04-18`: `41ac953` - `Stream E / architecture warning triage and disposition`  
  - Files:  
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Validation:
    - `uv run code-review-graph postprocess --repo .`
    - `mcp__code_review_graph__get_architecture_overview_tool`
    - `uv run pytest tests/unit/test_import_boundaries.py tests/unit/test_feature_module_contracts_control_groups.py -q`
  - Result:  
    - Stream E checklist completed with explicit warning-by-warning
      classification and controls/features ownership seam disposition.
  - Residual risk:
    - High warning counts remain test-coupling heavy; Stream F should lock in
      recurring graph hygiene and interpretation guidance.
- `2026-04-18`: `c22b949` - `Stream D / completion status + MCP refresh evidence`  
  - Files:  
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Validation:
    - `uv run code-review-graph build --repo . --skip-flows`
    - `mcp__code_review_graph__list_graph_stats_tool`
    - `mcp__code_review_graph__find_large_functions_tool` (`min_lines=80`)
  - Result:  
    - Stream D marked complete with refreshed graph timestamp and hotspot delta
      evidence (`build_snapshot` and `build_entity_references` removed from
      >=80 list).
  - Residual risk:
    - `evaluate_reload` remains at 81 lines and may need further slice if strict
      <=80 threshold is later enforced.
- `2026-04-18`: `54fa790` - `Stream D / snapshot decomposition (slice 2)`  
  - Files:  
    - `custom_components/magic_areas/coordinator/pipeline/snapshot.py`
    - `tests/unit/test_entity_ingestion_contract.py`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run ruff check custom_components/magic_areas/coordinator/pipeline/snapshot.py tests/unit/test_entity_ingestion_contract.py`
    - `uv run mypy custom_components/magic_areas/coordinator/pipeline/snapshot.py tests/unit/test_entity_ingestion_contract.py`
    - `uv run pytest tests/unit/test_entity_ingestion_contract.py tests/integration/test_coordinator_lifecycle.py -q`
  - Result:  
    - `build_snapshot` now uses explicit helper stages for feature config,
      presence projection, and final snapshot shaping.
  - Residual risk:
    - MCP hotspot deltas cannot yet be confirmed because `build_or_update_graph`
      times out at 120s in-tool.
- `2026-04-18`: `c497e44` - `Stream D / reload + reference pipeline decomposition (slice 1)`  
  - Files:  
    - `custom_components/magic_areas/core/meta_reload.py`
    - `custom_components/magic_areas/core/runtime_model/references.py`
    - `tests/unit/test_core_meta_reload.py`
    - `tests/unit/test_core_entity_ids_references.py`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run ruff check custom_components/magic_areas/core/runtime_model/references.py custom_components/magic_areas/core/meta_reload.py tests/unit/test_core_entity_ids_references.py tests/unit/test_core_meta_reload.py`
    - `uv run mypy custom_components/magic_areas/core/runtime_model/references.py tests/unit/test_core_entity_ids_references.py`
    - `uv run mypy custom_components/magic_areas/core/meta_reload.py tests/unit/test_core_meta_reload.py`
    - `uv run pytest tests/unit/test_core_meta_reload.py tests/unit/test_core_entity_ids_references.py tests/unit/test_core_entity_ids_builders.py -q`
  - Result:  
    - `evaluate_reload` and `build_entity_references` now follow explicit
      pure-helper decomposition boundaries with direct unit coverage for
      extracted logic.
  - Residual risk:
    - `build_snapshot` hotspot slice remains for Stream D completion.
- `2026-04-18`: `d5545ef` - `State refresh / post-Stream A-B-C baseline + next queue`  
  - Files:  
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Validation:
    - MCP snapshot refresh:
      - `mcp__code_review_graph__list_graph_stats_tool`
      - `mcp__code_review_graph__get_architecture_overview_tool`
      - `mcp__code_review_graph__find_large_functions_tool`
  - Result:  
    - Plan status updated to completed Streams A/B/C with live graph evidence and
      explicit next streams (D/E/F) including acceptance/exit criteria.
  - Residual risk:
    - Streams D/E/F are not yet executed.
- `2026-04-18`: `cc0cdb0` - `Stream A / runtime_core allowlist debt removal`  
  - Files:  
    - `custom_components/magic_areas/binary_sensor/aggregate_factory.py`
    - `custom_components/magic_areas/binary_sensor/ble_tracker.py`
    - `custom_components/magic_areas/binary_sensor/wasp_in_a_box.py`
    - `custom_components/magic_areas/switch/__init__.py`
    - `custom_components/magic_areas/switch/climate_control.py`
    - `custom_components/magic_areas/switch/fan_control.py`
    - `tests/unit/test_import_boundaries.py`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run pytest tests/unit/test_import_boundaries.py tests/unit/test_listener_entity_write_contracts.py tests/unit/test_listener_entity_lifecycle_contracts.py tests/unit/test_switch_base_write_contract.py tests/unit/test_feature_module_contracts_control_groups.py -q`
    - `uv run ruff check custom_components/magic_areas tests`
    - `uv run mypy custom_components/magic_areas tests`
    - `uv run pytest tests -q`
  - Result:  
    - `runtime_core` temporary allowlist entries removed; quality gates green.
  - Residual risk:
    - Reader-surface duplication (`core/config/feature_readers.py` and `features/config/readers.py`) still exists and remains tracked in Stream C.
- `2026-04-18`: `b1fe86a` - `Stream B / intentional seam documentation tightening`  
  - Files:  
    - `tests/unit/test_import_boundaries.py`
    - `docs/contributing/runtime-boundaries.md`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run pytest tests/unit/test_import_boundaries.py -q`
  - Result:  
    - Intentional allowlist seams now have explicit inline and docs rationale.
  - Residual risk:
    - Reader-surface duplication remains tracked in Stream C.
- `2026-04-18`: `21a223e` - `Stream C / reader ownership decision and census refresh`  
  - Files:  
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
    - `docs/contributing/boundary-census-2026-04-18.md`
  - Tests:  
    - `uv run pytest tests/unit/test_import_boundaries.py -q`
  - Result:  
    - Canonical reader ownership model documented; census updated post Stream A.
  - Residual risk:
    - reader logic duplication remains pending consolidation.
- `2026-04-18`: `bf3df48` - `Stream C / trim edge-only readers from core surface`  
  - Files:  
    - `custom_components/magic_areas/core/config/feature_readers.py`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run ruff check custom_components/magic_areas tests`
    - `uv run mypy custom_components/magic_areas tests`
    - `uv run pytest tests/unit/test_core_aggregates.py tests/unit/test_aggregate_policy.py tests/unit/test_core_climate_control.py tests/unit/test_core_fan_control.py tests/unit/test_import_boundaries.py -q`
  - Result:  
    - Edge-only reader duplication removed from core-owned reader module.
  - Residual risk:
    - overlapping core/feature reader logic remains for aggregate/health/climate/fan.
- `2026-04-18`: `c31a388` - `Stream C / remove aggregate-health reader overlap from features surface`  
  - Files:  
    - `custom_components/magic_areas/features/config/readers.py`
    - `tests/unit/test_aggregates_edge_cases.py`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run ruff check custom_components/magic_areas tests`
    - `uv run mypy custom_components/magic_areas tests`
    - `uv run pytest tests/unit/test_aggregates_edge_cases.py tests/unit/test_core_aggregates.py tests/unit/test_aggregate_policy.py tests/unit/test_import_boundaries.py -q`
  - Result:  
    - aggregate/health reader overlap removed from feature-owned reader module.
  - Residual risk:
    - overlap remained for climate/fan reader implementations.
- `2026-04-18`: `d47bd76` - `Stream C / remove climate-fan reader overlap from core surface`  
  - Files:  
    - `custom_components/magic_areas/core/controls/policies/climate.py`
    - `custom_components/magic_areas/core/controls/policies/fan.py`
    - `custom_components/magic_areas/core/config/feature_readers.py`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run ruff check custom_components/magic_areas tests`
    - `uv run mypy custom_components/magic_areas tests`
    - `uv run pytest tests/unit/test_core_climate_control.py tests/unit/test_core_fan_control.py tests/unit/test_feature_module_contracts_control_groups.py tests/unit/test_import_boundaries.py -q`
  - Result:  
    - Feature-specific reader overlap eliminated across core vs feature reader surfaces.
  - Residual risk:
    - duplicated generic reader scaffolding remains.
- `2026-04-18`: `673711a` - `Stream C / deduplicate generic reader scaffolding`  
  - Files:  
    - `custom_components/magic_areas/feature_reader_common.py`
    - `custom_components/magic_areas/core/config/feature_readers.py`
    - `custom_components/magic_areas/features/config/readers.py`
    - `docs/contributing/mcp-production-risk-hardening-plan.md`
  - Tests:  
    - `uv run ruff check custom_components/magic_areas tests`
    - `uv run mypy custom_components/magic_areas tests`
    - `uv run pytest tests/unit/test_import_boundaries.py tests/unit/test_core_config_helpers.py tests/unit/test_aggregates_edge_cases.py tests/unit/test_feature_module_contracts_control_groups.py -q`
    - `uv run pytest tests -q`
  - Result:  
    - Shared generic feature-reader scaffolding is centralized and reused by
      both core and features reader surfaces.
  - Residual risk:
    - none within Stream C scope.
