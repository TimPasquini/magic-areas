# Boundary Constraint Census (2026-04-18)

## Purpose

Create a concrete inventory of test-enforced boundary constraints so cleanup can
target real friction points without weakening architectural intent.

This census is read-only analysis input for follow-up cleanup PRs.

## Context

- Source of truth for boundary enforcement:
  - `tests/unit/test_import_boundaries.py`
  - `docs/contributing/runtime-boundaries.md`
  - `docs/contributing/architecture.md`
- Current boundary test status:
  - `uv run pytest tests/unit/test_import_boundaries.py -q` passes (`51 passed`)

## Enforcement Model Inventory

The boundary suite currently enforces five distinct constraint families:

1. Side-door import blocking for runtime packages (`BOUNDARY_RULES`).
2. Side-door import blocking for tests (`TEST_SIDE_DOOR_RULES`).
3. Per-module ownership bans (`OWNERSHIP_IMPORT_RULES`).
4. Package-level ownership bans:
   - `core` cannot import `features.config.*`.
   - `features.modules` cannot import `core.controls.*` directly.
5. Surface contracts:
   - no root `core` facade imports
   - no entrypoint bypass imports
   - no feature-semantic leaks from central `__all__` exports

Interpretation:
- The project is not under-constrained. It is strongly constrained.
- Current friction is mostly overlap between side-door constraints and
  import-path-specific exceptions.

## Allowlist Census

Current explicit override entries in `ALLOWLIST_OVERRIDES`: **6**

### Runtime allowlist entries

| Key | Consumer | Target | Classification | Reason | Cleanup Direction |
|---|---|---|---|---|---|
| `runtime_schemas` | `custom_components.magic_areas.config_flows.selector_builders` | `custom_components.magic_areas.schemas.selectors` | `intentional-permanent` | Explicit adapter seam to prevent direct step-level selector side-doors. | Keep as explicit intentional seam; document as permanent exception. |

### Test allowlist entries

| Key | Consumer | Target | Classification | Reason | Cleanup Direction |
|---|---|---|---|---|---|
| `test_light_groups` | `tests/unit/test_listener_entity_write_contracts` | `custom_components.magic_areas.light_groups.entities` | `intentional-permanent` | Contract test targets entity write-path behavior at implementation level. | Keep, but tag as implementation-contract test seam. |
| `test_light_groups` | `tests/unit/test_listener_entity_write_contracts` | `custom_components.magic_areas.light_groups.runtime` | `intentional-permanent` | Same test validates runtime callback write semantics. | Keep. |
| `test_light_groups` | `tests/unit/test_light_control_group_parity` | `custom_components.magic_areas.light_groups.runtime` | `intentional-permanent` | Parity tests use runtime host contract directly. | Keep. |
| `test_switch` | `tests/unit/test_listener_entity_lifecycle_contracts` | `custom_components.magic_areas.switch.base` | `intentional-permanent` | Lifecycle contracts intentionally exercise base class behavior. | Keep. |
| `test_switch` | `tests/unit/test_switch_base_write_contract` | `custom_components.magic_areas.switch.base` | `intentional-permanent` | Write-path contracts intentionally exercise base class behavior. | Keep. |

## Reader Ownership Census (Primary Friction Point)

Two parallel reader surfaces currently exist:

- `custom_components/magic_areas/core/config/feature_readers.py`
- `custom_components/magic_areas/features/config/readers.py`

Import census (runtime, post Stream A):

- `core.config.feature_readers` importers: **4**
  - Core modules: 4 (expected)
  - Non-core modules: 0
- `features.config.readers` importers: feature-module + edge adapter layers

Assessment:

- The architectural model is coherent (separate ownership doors).
- Practical enforcement drift identified at census time has been reduced:
  - non-core modules no longer consume core reader internals
  - feature-specific overlap across core vs feature reader surfaces has been
    removed
- Remaining generic scaffolding duplication identified at census time has also
  been addressed by centralizing shared reader scaffolding in
  `custom_components.magic_areas.feature_reader_common`.

## Constraint Quality Assessment

### Good constraints (keep strict)

- Core package ban on `core -> features.config` imports.
- Feature-module ban on direct `features.modules -> core.controls` imports.
- Entry-surface enforcement (no root `core` imports, no entrypoint bypass).
- Policy purity and typing guardrails in dedicated contract tests.

### Constraints needing recalibration

- Generic reader helper duplication across two owned surfaces.
  - Feature-semantic overlap is addressed; generic helper overlap remains.

### Constraints that are intentional and should stay explicit

- `config_flows.selector_builders -> schemas.selectors` adapter seam.
- Test-only implementation seams for `light_groups.runtime/entities` and
  `switch.base`.

## Targeted Cleanup Plan (Post-Census)

1. Decide and document reader ownership boundary: ✅
   - keep two-door intent explicit
   - define which door edge modules should use
2. Execute a focused migration for the 6 `runtime_core` entries. ✅
3. Remove those allowlist entries immediately after migration. ✅
4. Keep test-side allowlist entries, and annotate them as intentional ✅
   implementation-contract seams.
5. Keep schema selector adapter allowlist as intentional-permanent unless a ✅
   better ownership-preserving seam is introduced.
6. Remove feature-specific reader overlap across core vs feature surfaces. ✅

Success criteria for cleanup stream(s):

- `runtime_core` allowlist entries drop from 6 to 0. ✅
- No increase in any other allowlist bucket.
- `uv run pytest tests/unit/test_import_boundaries.py -q` remains green.
- Full quality gates remain green.

## Relationship to MCP Hardening Plan

This census directly feeds:

- Phase 2 (boundary contracts): remove stale/temporary allowlist debt.
- Phase 4 (ownership alignment): preserve no-side-door guarantees while
  avoiding path-shape brittleness where ownership is equivalent.

The census should be treated as the working input for the next targeted
boundary cleanup stream.
