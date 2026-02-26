# Entity Loading Packaging Plan

## Goal
Package the entity-loading pipeline into a single, explicit module boundary so it is
clear, discoverable, and reusable as a standalone unit. This cluster already does
one job (collect + filter + snapshot entities) and only feeds snapshot building.

## Scope
- Recompose the entity-loading cluster into a package boundary only.
- Preserve current runtime behavior and snapshot structure.

## Non-Goals
- No feature behavior changes.
- No config-flow changes.
- No entity ID naming changes.

## Compatibility Invariants
- `MagicAreasData.entities` and `MagicAreasData.magic_entities` shape stays identical.
- Snapshot builder call sites and return semantics remain unchanged.
- Existing tests for entity loading and snapshot behavior pass without fixture rewrites.

## Current State
Files involved:
- `core/entity_loading.py` — orchestrates loading and grouping
- `core/registry_queries.py` — registry queries and filtering
- `core/entity_loader.py` — exclusion helpers
- `core/entities.py` — snapshot + grouping helpers

Usage:
- Only imported by `core/snapshot_builder.py`

## Target Structure
Create a small package:
```
core/entity_loading/
  __init__.py              # public API exports
  registry_queries.py      # registry access + queries
  filters.py               # exclusion logic (currently entity_loader.py)
  snapshots.py             # snapshot/group helpers (currently entities.py)
  loader.py                # orchestration (currently entity_loading.py)
```

Public API surface (from `__init__.py`):
- `load_area_entities`
- `load_meta_area_entities`

## Steps
1. **Create package directory**
   - Add `core/entity_loading/` with `__init__.py`.

2. **Move orchestration**
   - Move `core/entity_loading.py` → `core/entity_loading/loader.py`.
   - Update imports inside the module to point to `filters`, `registry_queries`,
     and `snapshots`.

3. **Move helpers**
   - Move `core/entity_loader.py` → `core/entity_loading/filters.py`.
   - Move `core/entities.py` → `core/entity_loading/snapshots.py`.

4. **Move registry queries**
   - Move `core/registry_queries.py` → `core/entity_loading/registry_queries.py`.
   - Update imports to reference `filters` inside the package.

5. **Create the public API**
   - In `core/entity_loading/__init__.py`, re-export:
     - `load_area_entities`, `load_meta_area_entities`.

6. **Update callers**
   - Update `core/snapshot_builder.py` to import from the new package:
     - `from custom_components.magic_areas.core.entity_loading import load_area_entities, load_meta_area_entities`
   - Update any internal imports to the new paths.

7. **Delete old files**
   - Remove `core/entity_loading.py`, `core/entity_loader.py`, `core/entities.py`,
     and `core/registry_queries.py` from the root of `core/`.

## Test-First Plan (write before code moves)
Add package-level contract tests first, expecting initial failures after import-target
updates, but ensuring pytest collection remains stable.

1. Add `tests/unit/test_entity_ingestion_contract.py`.
2. Add contract tests for:
   - `load_area_entities` parity: same domain keys and entity counts as baseline fixture.
   - `load_meta_area_entities` parity: same child-entity resolution behavior.
   - exclusion parity: diagnostic/config exclusion behavior unchanged.
   - include/exclude list precedence unchanged.
3. For initial failing state:
   - update tests to import new target package paths,
   - keep old implementation in place until move phase begins,
   - assert known expected output from fixtures so failures are deterministic.
4. Add a focused `pytest` invocation for rapid iteration:
   - `uv run pytest tests/unit/test_entity_ingestion_contract.py -q`

## Phase Acceptance Criteria
- Package exists and only exports intended public API from `__init__.py`.
- No remaining imports to removed root files.
- Contract tests pass and prove parity with baseline behavior.
- Full suite, mypy, and ruff pass.

## Risk / Rollback
- Risk: hidden import paths in less-used code paths.
- Mitigation: run `rg` for old import paths before deletion.
- Rollback: restore old root files and re-point imports to legacy paths if parity breaks.

## Validation
- `uv run ruff check custom_components/magic_areas tests`
- `uv run mypy custom_components/magic_areas tests`
- `uv run pytest ./tests --cov=custom_components.magic_areas --cov-report term-missing --numprocesses=auto`

## Expected Outcome
- Clear, single-purpose package boundary.
- Reduced cognitive load and clearer entry points for future refactors.
