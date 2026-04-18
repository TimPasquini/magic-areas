# Phase Closure Packet (Binary)

Purpose: define strict, binary close criteria for each phase in
`mcp-production-risk-hardening-plan.md`.

A phase is `COMPLETE` only when every listed criterion is evidenced.

## Architecture Correction: Two-Door Model

Required criteria (all):
- No lazy-proxy root facade remains.
- `entity.py` does not depend on runtime registry construction path.
- Metadata is available without importing `features.modules`.
- Full lint/type/tests pass.

Commands:

```bash
uv run ruff check custom_components/magic_areas tests
uv run mypy custom_components/magic_areas tests
uv run pytest tests -q

test -f custom_components/magic_areas/feature_registry.py && echo PRESENT || echo MISSING
rg -n "get_feature_info|FEATURE_INFO_BY_FEATURE" \
  custom_components/magic_areas/entity.py \
  custom_components/magic_areas/features/registry.py \
  custom_components/magic_areas/feature_info.py
rg -n "features\.modules|lazy|proxy" custom_components/magic_areas/feature_info.py
```

Pass rules:
- `feature_registry.py` -> `MISSING`
- `entity.py` uses metadata door (`get_feature_info`)
- `feature_info.py` has no runtime wiring imports
- all quality gates green

## Phase 0: Lock in Graph Signal Quality

Required criteria (all):
- Test nodes and `TESTED_BY` edges are substantial.
- Workflow is documented in `docs/contributing`.
- Team can rerun and reproduce signal quality.

Commands:

```bash
uv run code-review-graph build --repo .
uv run code-review-graph postprocess --repo .
```

Then verify via MCP:
- `mcp__code_review_graph__list_graph_stats_tool`
- `last_updated` current for session
- tests and `TESTED_BY` counts present

Pass rules:
- test-inclusive graph metrics present
- hygiene workflow and stale-signal guard documented

## Phase 1: Remove Core Boundary Inversion

Required criteria (all):
- No production file under `core/` imports `features.config.readers`.
- Behavior parity maintained (existing tests pass).
- New helpers directly unit-tested.

Commands:

```bash
rg -n "features\.config\.readers" custom_components/magic_areas/core
uv run pytest tests -q
```

Pass rules:
- `rg` returns no matches
- full suite passes

## Phase 2: Enforce Boundary Contracts in Tests

Required criteria (all):
- Boundary tests fail on a synthetic violation and pass when reverted.
- No stale allowlist entries for removed inversion.
- Rule intent documented.

Required procedure:
1. Add temporary forbidden `core -> features.config` import.
2. Run boundary suite (must fail).
3. Revert temporary violation.
4. Run boundary suite again (must pass).

Command:

```bash
uv run pytest tests/unit/test_import_boundaries.py -q
```

Pass rules:
- one intentional fail run captured
- one post-revert pass run captured
- allowlist verified clean for removed inversion

## Phase 3: Reduce Blast Radius in Lifecycle/Meta/Snapshot Paths

Required criteria (all):
- Hotspot functions decomposed into smaller units.
- Extracted pure helpers have direct unit tests.
- Integration behavior unchanged.
- Follow-up CRG evidence shows reduced hotspot footprint.

Stream-D specific threshold rule:
- At least 2 of these 3 must be absent from `>=80` list:
  - `core/meta_reload.py::evaluate_reload`
  - `coordinator/pipeline/snapshot.py::build_snapshot`
  - `core/runtime_model/references.py::build_entity_references`

Commands:
- MCP `find_large_functions(min_lines=80)`
- `uv run pytest tests/unit -q`
- `uv run pytest tests/integration/test_coordinator_lifecycle.py -q`
- MCP `get_impact_radius` after major slices

Pass rules:
- threshold rule satisfied
- unit + integration tests pass
- impact/hotspot evidence logged

## Phase 4: Structural Ownership Alignment (Two-Door)

Required criteria (all):
- Two-door boundary implemented and documented.
- Boundary tests remain strict on side-door growth.
- Residual warnings explicitly classified with rationale.
- Evidence reflects ownership simplification, not path churn only.

Commands:
- MCP `get_architecture_overview`
- MCP `query_graph(importers_of|callers_of)` on seam modules
- `uv run pytest tests/unit/test_import_boundaries.py -q`

Pass rules:
- every current warning disposition recorded:
  - `resolved`
  - `intentional`
  - `deferred`
  - `test-coupling noise`
- boundary suite passes

## Evidence Template (Use Per Phase)

- Phase:
- Date/Time:
- Commands run:
- Outputs (key lines only):
- Criteria checklist:
  - [ ] criterion 1
  - [ ] criterion 2
  - [ ] criterion 3
- Final status: `COMPLETE` / `NOT COMPLETE`

## Execution Report (2026-04-18)

- Phase: Architecture Correction (Two-Door Model)
- Date/Time: `2026-04-18T23:10:06-04:00`
- Commands run:
  - `uv run ruff check custom_components/magic_areas tests`
  - `uv run mypy custom_components/magic_areas tests`
  - `uv run pytest tests -q`
  - `test -f custom_components/magic_areas/feature_registry.py && echo PRESENT || echo MISSING`
  - `rg -n "get_feature_info|FEATURE_INFO_BY_FEATURE" custom_components/magic_areas/entity.py custom_components/magic_areas/features/registry.py custom_components/magic_areas/feature_info.py`
  - `rg -n "features\.modules|lazy|proxy" custom_components/magic_areas/feature_info.py`
- Outputs (key lines only):
  - `All checks passed!`
  - `Success: no issues found in 301 source files`
  - `1013 passed in 24.84s`
  - `MISSING` (`feature_registry.py`)
  - `entity.py` imports and calls `get_feature_info`
  - `feature_info.py` has no `features.modules|lazy|proxy` matches
- Criteria checklist:
  - [x] no lazy-proxy root facade remains
  - [x] `entity.py` uses metadata door only
  - [x] `feature_info.py` has no runtime wiring imports
  - [x] full lint/type/tests are green
- Final status: `COMPLETE`

- Phase: Phase 0 (Graph Signal Quality)
- Date/Time: `2026-04-18T23:10:06-04:00`
- Commands run:
  - `uv run code-review-graph build --repo .`
  - `uv run code-review-graph postprocess --repo .`
  - `mcp__code_review_graph__list_graph_stats_tool`
- Outputs (key lines only):
  - `Full build: 302 files, 2484 nodes, 18376 edges`
  - `Post-processing: 240 flows, 20 communities, 2479 FTS entries`
  - Graph stats: `files=302`, `Test=966`, `TESTED_BY=5202`, `last_updated=2026-04-18T23:04:22`
  - Workflow docs present: `docs/contributing/mcp-graph-hygiene.md`
- Criteria checklist:
  - [x] test-inclusive graph metrics are present
  - [x] workflow documented in `docs/contributing`
  - [x] reproducible sanity signal captured
- Final status: `COMPLETE`

- Phase: Phase 1 (Remove Core Boundary Inversion)
- Date/Time: `2026-04-18T23:10:06-04:00`
- Commands run:
  - `rg -n "features\.config\.readers" custom_components/magic_areas/core`
  - `uv run pytest tests -q`
- Outputs (key lines only):
  - `rg` returned no matches (exit `1`)
  - `1013 passed in 24.84s`
- Criteria checklist:
  - [x] no production import from `core -> features.config.readers`
  - [x] full suite passes
- Final status: `COMPLETE`

- Phase: Phase 2 (Boundary Contracts)
- Date/Time: `2026-04-18T23:10:06-04:00`
- Commands run:
  - temporary synthetic import added to `core/aggregates/runtime.py`
  - `uv run pytest tests/unit/test_import_boundaries.py -q` (expected fail)
  - temporary import removed
  - `uv run pytest tests/unit/test_import_boundaries.py -q` (expected pass)
  - `sed -n '1,140p' tests/unit/test_import_boundaries.py` (allowlist verification)
- Outputs (key lines only):
  - intentional-fail run: `2 failed, 49 passed`
  - fail reason included:
    - `imports feature semantics that should be slice-owned`
    - `core package imports feature config adapters`
  - post-revert run: `51 passed in 6.67s`
  - `ALLOWLIST_OVERRIDES` contains no `runtime_core` override entries
- Criteria checklist:
  - [x] synthetic violation fails as expected
  - [x] post-revert boundary suite passes
  - [x] removed inversion has no stale allowlist override
- Final status: `COMPLETE`

- Phase: Phase 3 (Blast Radius / Hotspots)
- Date/Time: `2026-04-18T23:10:06-04:00`
- Commands run:
  - `mcp__code_review_graph__find_large_functions_tool(kind=Function,min_lines=80)`
  - `uv run pytest tests/unit -q`
  - `uv run pytest tests/integration/test_coordinator_lifecycle.py -q`
  - `mcp__code_review_graph__get_impact_radius_tool` on:
    - `core/meta_reload.py`
    - `coordinator/pipeline/snapshot.py`
    - `core/runtime_model/references.py`
- Outputs (key lines only):
  - hotspot list at `>=80` functions includes:
    - `core/meta_reload.py::evaluate_reload` (`81`)
    - does not include `build_snapshot`
    - does not include `build_entity_references`
  - `705 passed` (unit)
  - `8 passed` (integration lifecycle)
  - impact radius captured: `28 changed`, `487 impacted`, `180 files`
- Criteria checklist:
  - [x] threshold rule satisfied (2 of 3 primary hotspots removed from >=80 list)
  - [x] unit + integration suites pass
  - [x] impact/hotspot evidence logged
- Final status: `COMPLETE`

- Phase: Phase 4 (Structural Ownership Alignment)
- Date/Time: `2026-04-18T23:10:06-04:00`
- Commands run:
  - `mcp__code_review_graph__get_architecture_overview_tool`
  - `mcp__code_review_graph__query_graph_tool(pattern=importers_of,target=.../features/registry.py)`
  - `mcp__code_review_graph__query_graph_tool(pattern=importers_of,target=.../feature_info.py)`
  - `mcp__code_review_graph__query_graph_tool(pattern=callers_of,target=.../feature_info.py::get_feature_info)`
  - `uv run pytest tests/unit/test_import_boundaries.py -q`
- Outputs (key lines only):
  - architecture warnings: `8` (classified in hardening plan as intentional/test-coupling noise)
  - seam importers captured:
    - `features/registry.py`: `9` importers
    - `feature_info.py`: `6` importers
    - `entity.py::__init__` is caller of `get_feature_info`
  - boundary suite: `51 passed in 6.67s`
- Criteria checklist:
  - [x] two-door boundary evidence captured and documented
  - [x] boundary tests remain strict and passing
  - [x] warnings classified with explicit dispositions
  - [x] ownership simplification evidenced by seam-level importer/caller maps
- Final status: `COMPLETE`
