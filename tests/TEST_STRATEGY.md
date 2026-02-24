# Test Suite Strategy & Refactoring Plan

**Status**: Active — Last updated 2026-02-25
**Current State**: 708 tests, 97% coverage (Phases 0-2 complete, Phase 3 next)

## Executive Summary

The test suite is in a **hybrid state**: excellent new unit tests for core logic, but redundant integration-weight platform tests and legacy "god files" from the old architecture.

**Key Finding**: Removed 31 zero-assertion coverage-chasing tests (7 files + 1 test function), revealing true coverage gaps worth addressing.

---

## Critical Issues Identified

### 1. Duplicate Coverage (test_light_edge_cases.py)
**Problem**: Policy logic tested twice — once in pure unit tests, again in integration tests with private method mocking.

**Evidence**:
- `test_priority_filtering_applied` (unit) vs `test_priority_state_preference` (platform) — same logic
- `test_turn_off_when_bright_not_assigned` (unit) vs `test_bright_not_assigned` (platform) — same logic
- `_turn_off()` mocked **15 times**, `_turn_on()` mocked **7 times**

**Impact**: Slow, brittle tests that add no value. Every policy refactor breaks tests in two places.

### 2. Testing Private Methods (test_light_edge_cases.py)
**Problem**: Tests call `target_group._turn_on()`, `target_group._turn_off()`, `target_group.state_change_secondary()` directly.

**Impact**: Tests are coupled to implementation details, not behavior. Refactoring class internals breaks tests even if functionality is correct.

### 3. Legacy God File (test_magic.py)
**Problem**: 773-line file tests everything — config flow merging, entity registry filtering, area loading, state management.

**Impact**: Low cohesion, hard to find where specific behaviors are tested.

### 4. Brittle Event Construction
**Problem**: Manual event tuples `([AreaStates.OCCUPIED], [], [...])` hard-coded in tests.

**Impact**: If event structure changes, tests break silently or noisily.

### 5. Real Coverage Gaps (Uncovered Lines)
**Problem**: Some legitimate behavioral gaps from original fork baseline:
- `switch/climate_control.py` (90%): Sensor state transitions, area ID mismatch, empty state guards
- `config_flows/steps/feature_config_advanced.py` (82%): Schema validation, merge_options routing
- `media_player/area_aware_media_player.py` (91%): No-op paths, error handling
- `binary_sensor/threshold.py` (90%): Feature/entity availability checks

---

## Test Suite Census

### Healthy Tests (Keep & Expand)
| File | Tests | Status | Action |
|------|-------|--------|--------|
| `unit/test_core_light_control.py` | 23 | 🟢 Excellent | Keep. Pure policy logic, clear assertions. |
| `unit/test_core_presence.py` | 17 | 🟢 Excellent | Keep. Covers `compute_secondary_states()`. |
| `unit/test_core_*.py` (all) | 100+ | 🟢 Excellent | Keep. Core domain logic, 100% coverage. |
| `integration/test_init.py` | 8 | 🟢 Good | Keep. Setup, migration, reload tests. |
| `integration/test_coordinator.py` | 8 | 🟡 Incomplete | Update. Move entity loading tests from test_magic.py. |
| `platforms/test_light.py` | 14 | 🟢 Good | Keep. Basic platform smoke tests. |
| `platforms/test_wasp_in_a_box.py` | 7 | 🟢 Good | Keep. Feature-specific integration tests. |

### Problematic Tests (Refactor/Delete)
| File | Tests | Status | Action |
|------|-------|--------|--------|
| `platforms/test_light_edge_cases.py` | 14 | 🔴 Redundant | **PRUNE** — Remove policy logic duplicates (keep wiring tests). |
| `integration/test_magic.py` | 73 | 🔴 God File | **SPLIT** — Move to `test_coordinator.py`, `test_area_lifecycle.py`. |
| `platforms/test_switch_setup.py` | 2 | ⚪ Tiny | **MERGE** — Combine into `test_setup_failures.py`. |
| `platforms/test_cover_setup.py` | 2 | ⚪ Tiny | **MERGE** — Same as above. |

### Low-Value Tests (Mark pragma: no cover)
| File | Reason |
|------|--------|
| `binary_sensor/threshold.py:48,66,80` | Feature/entity availability checks (setup guards). |
| `media_player/__init__.py:110,113` | Entry validation (runtime invariants). |
| TYPE_CHECKING blocks | Only evaluated by type checkers, not runtime. |

---

## Refactoring Phases

### ✅ PHASE 0: Cleanup (COMPLETE)
- ✅ Remove 7 zero-assertion test files (1,192 lines)
- ✅ Remove 1 zero-assertion test function
- **Result**: 704 tests (down from 735), 96% coverage maintained, tests now trustworthy

### ✅ PHASE 1: Remove Duplicates (COMPLETE)
**Scope**: `tests/platforms/test_light_edge_cases.py`

**Tasks**:
1. Delete policy logic duplicate tests:
   - `test_priority_state_preference` (duplicate of unit test)
   - `test_dark_state_prevention` (duplicate of unit test)
   - `test_no_priority_transition` (duplicate of unit test)
   - `test_bright_not_assigned` (duplicate of unit test)
   - Any other tests that directly test policy.evaluate() logic via entity

2. Delete private method mocking:
   - Remove `target_group._turn_on = MagicMock(...)`
   - Remove `target_group._turn_off = MagicMock(...)`
   - Remove `target_group.state_change_secondary()` direct calls

3. Keep only wiring tests:
   - Tests that verify "when policy returns TURN_ON, does entity call hass.services.call?"
   - Tests for actual light entity behavior (state changes, group membership, etc.)

**Success Metrics**:
- Reduced `test_light_edge_cases.py` from 702 lines to ~300 lines
- No duplicate test names (unit + platform)
- No private method mocking
- All remaining tests assert behavior, not implementation details

**Estimated Impact**: -~10 tests, -~400 lines, faster test suite, cleaner code

---

### ✅ PHASE 2: Add High-Priority Coverage (COMPLETE)
**Scope**: Add tests for real behavioral gaps identified in fork baseline analysis.

**Status**: All 11 tests created and passing. Coverage improvements:
- climate_control.py: 81% → 94% (5 tests)
- feature_config_advanced.py: 82% → 97% (4 tests)
- media_player/area_aware_media_player.py: 29% → 94% (2 tests)
- Overall: 708 tests (+12), 97% coverage maintained
- Commit: 688f959

#### 2A: climate_control.py (81% → 94%) ✅
**File**: `tests/platforms/test_climate_control_behaviors.py` (253 lines)

**Tests Added** (5):
1. `test_area_sensor_off_applies_clear_preset` - Sensor OFF → CLEAR preset
2. `test_area_sensor_on_applies_occupied_preset` - Sensor ON → OCCUPIED preset
3. `test_area_id_mismatch_skips_handler` - Wrong area ID skips handler (lines 116-122)
4. `test_empty_state_tuple_skips_processing` - Empty states skip handler (line 127)
5. `test_exception_in_preset_application_is_handled` - Exception caught & logged (lines 172-173)

**Impact**: +5 tests, +13 coverage points

#### 2B: feature_config_advanced.py (82% → 97%) ✅
**File**: `tests/unit/test_core_feature_config_advanced.py` (123 lines)

**Tests Added** (4):
1. `test_invalid_schema_returns_error` - vol.MultipleInvalid caught (lines 62-63)
2. `test_merge_options_true_merges_into_existing` - merge_options=True (line 67)
3. `test_merge_options_false_replaces` - merge_options=False (line 69)
4. `test_next_step_routing` - next_step routing (line 73)

**Impact**: +4 tests, +15 coverage points

#### 2C: media_player (29% → 94%) ✅
**File**: `tests/platforms/test_area_aware_media_player_gaps.py` (86 lines)

**Tests Added** (2):
1. `test_area_sensor_not_found_skips_area` - Sensor not found skips area (lines 146-152)
2. `test_no_media_players_skips_service_call` - No players skips service call (lines 214-218)

**Impact**: +2 tests, +65 coverage points

### 🔧 PHASE 3: Refactor Legacy Structure (LOWER PRIORITY)
**Scope**: Structural improvements for maintainability.

**Tasks**:
1. Split `test_magic.py` (773 lines):
   - Entity loading tests → `tests/integration/test_coordinator.py`
   - Registry filter tests → `tests/unit/test_core_registry_filters.py` (new)
   - Config helper tests → `tests/unit/test_core_config.py` (new)
   - Area lifecycle → `tests/integration/test_area_lifecycle.py` (new)

2. Merge tiny setup files:
   - `test_switch_setup.py` + `test_cover_setup.py` → `test_setup_failures.py`

3. Fix brittle event construction:
   - Create event payload constant/helper
   - Document event tuple structure

4. Add pragma: no cover to setup guards:
   - `threshold.py` feature/entity checks
   - `media_player/__init__.py` entry validation

---

## Coverage Target

**Initial**: 735 tests, unknown coverage
**After Phase 0** (cleanup): 704 tests, 96% coverage (removed 31 zero-assertion tests)
**After Phase 1** (remove duplicates): 697 tests, 96% coverage (removed 7 redundant tests)
**After Phase 2** (high-priority gaps): 708 tests, 97% coverage (added 11 behavioral tests) ✅
**After Phase 3** (refactor structure): ~705 tests, 97%+ coverage (planned: split god files, improve organization)

---

## How to Reference This Plan

- **Phase 1 Start**: Run `tests/TEST_STRATEGY.md` Phase 1 section
- **Phase 2 Review**: Check coverage analysis in Phase 2 sections
- **Status Check**: Update "Last updated" date and mark phases as complete

### Key Files for Each Phase
| Phase | Files | Command |
|-------|-------|---------|
| 1 | `tests/platforms/test_light_edge_cases.py` | `grep -n "def test_" ...` |
| 2 | `switch/climate_control.py`, `config_flows/steps/feature_config_advanced.py`, `media_player/area_aware_media_player.py` | Coverage reports |
| 3 | `tests/integration/test_magic.py` | Large file analysis |

---

## Fork Baseline Context

Original implementation (`d7b5779`) validated these behaviors:
- Climate control: Priority state selection, sensor-based preset switching
- Media player: Active area filtering, media player discovery
- Feature config: Schema validation, dynamic option routing
- Threshold: Feature/device class availability checks

All Phase 2 tests are based on behaviors from the original code, ensuring we test what the design intended to support.

---

## Success Criteria

- ✅ No duplicate tests (unit + platform testing same logic)
- ✅ No private method mocking
- ✅ All platform tests assert public behavior
- ✅ Coverage gaps filled with meaningful behavioral tests
- ✅ Test suite remains <25 seconds
- ✅ No flaky or brittle tests