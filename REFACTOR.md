# Magic Areas Refactoring Guide

**Status**: 🚧 Active Refactoring - Decomposition Phase
**Last Updated**: 2026-02-08

## Table of Contents
- [Overview](#overview)
- [Current State](#current-state)
- [Refactoring Phases](#refactoring-phases)
- [Current Phase: Decomposition](#current-phase-decomposition)
- [Guidelines for Contributors](#guidelines-for-contributors)
- [Target Architecture](#target-architecture)
- [How to Contribute](#how-to-contribute)
- [FAQ](#faq)

## Overview

This document explains the ongoing refactoring of the Magic Areas integration. We are systematically transforming the codebase from several large, monolithic modules into a cleaner, more maintainable structure while preserving all existing functionality.

**Key Principle**: We are decomposing first, then will recompose deliberately. This means the codebase will temporarily look "messy" with more files than seems necessary. This is intentional and expected.

## Current State

The integration was forked from upstream (commit `d7b5779`) and has been enhanced with:
- Coordinator-based architecture (snapshot pattern)
- Event payloads with state snapshots
- Registry-driven config flow
- Core helper extraction (ongoing)

See `/docs/migration/` for detailed architectural changes from the fork baseline.

### What We're Refactoring

The original codebase had several problems:
1. **`base/magic.py`** (~25KB): Mixed orchestration, filtering, and derived values in one file
2. **Platform files**: Computed entity lists independently, creating duplication and drift risk
3. **`config_flow.py`** (48KB): Large class blending flow mechanics with feature logic
4. **Inconsistent helper usage**: Domain logic scattered across helper modules

### Refactoring Goals

From `implementation-plan.md`:
- Reduce cross-module coupling and duplicated logic
- Centralize runtime data shaping in coordinator snapshot
- Keep platform files focused on entity wiring only
- Preserve current user-facing behavior and config flow UX
- Improve testability by isolating domain logic from HA entity classes
- Make future feature additions require changes in one place

### Non-Goals (What We're NOT Doing)

- ❌ Redesigning user-facing features or behavior
- ❌ Changing config entry data format (unless required by HA)
- ❌ Removing features or reducing platform coverage
- ❌ Introducing new platforms during refactor
- ❌ Rewriting tests for style or aesthetic changes

## Refactoring Phases

### Phase 1: Align Boundaries ✅ COMPLETE
- Snapshot is single source of truth for platform setup
- Coordinator refresh before platform setup (no area fallbacks)
- All platforms now read snapshot fields only

### Phase 2: Extract Core Domain Logic 🔄 IN PROGRESS
- Split `base/magic.py` into focused modules
- Keep pure logic modules free of HA entity references
- Update coordinator to call these modules
- Consolidate filtering and derived-state rules

**Current Progress:**
- ✅ Core helpers extracted for config, presence, entity grouping
- ✅ Unique ID format updated with migration support
- ✅ Entity availability follows coordinator refresh
- 🔄 Aggregates logic extraction ongoing
- 🔄 Reducing `base/magic.py` to orchestration only

### Phase 3-5: Future Phases
- **Phase 3**: Simplify platform adapters
- **Phase 4**: Config flow modularization
- **Phase 5**: Cleanup and consolidation

See `implementation-plan.md` for detailed phase breakdown.

## Current Phase: Decomposition

**We are currently in the decomposition phase of Phase 2.**

### What Decomposition Means

Decomposition is the process of breaking large files into smaller, focused pieces. During this phase:
- **File count will increase** (this is good, not bad)
- **Directory depth may increase** (also expected)
- **Names and locations may be provisional** (we'll refine later)
- **Architectural clarity trumps visual neatness** (always)

### Why More Files Is OK

Home Assistant evaluates integrations based on **runtime behavior**, not internal organization. Home Assistant doesn't care about:
- How many files you have
- Whether your directory structure looks "clean"
- Temporary fragmentation during refactoring
- Intermediate layouts

Home Assistant **does** care about:
- Imports remaining valid
- Config flows remaining stable
- Entities registering correctly
- Async patterns being preserved

**We can have 100 files if that makes responsibilities clearer.** We'll consolidate later during recomposition.

### The File Sprawl Is Temporary

Yes, there are more files now than before. This is **intentional and temporary**. We are:
1. **Exposing seams**: Making logical boundaries visible
2. **Clarifying ownership**: Each file should have one clear job
3. **Enabling recomposition**: You can't recombine well until you've separated well

Think of it like taking apart a machine to understand how it works before putting it back together better.

## Guidelines for Contributors

### DO ✅

1. **Split files when responsibilities are unclear**
   - If a file does multiple things, split it
   - Even if you're not sure where it will end up
   - Better to have clear separation now, consolidate later

2. **Preserve behavior exactly**
   - Structural changes must not alter logic
   - All tests must pass
   - No breaking changes to config entry data

3. **Keep imports directional**
   - Avoid circular dependencies
   - Core → helpers → platforms
   - Models → policy → adapters

4. **Make ownership obvious**
   - If you can't explain what a file does in one sentence, split it
   - File names should describe responsibility clearly
   - If a change makes ownership less clear, it's wrong

5. **Write tests for extracted logic**
   - Core modules should have HA-free unit tests
   - Platform changes need integration tests
   - Maintain 95%+ coverage

### DON'T ❌

1. **Don't consolidate to reduce file count**
   - More files is OK during decomposition
   - Only consolidate when duplication is clear
   - Visual neatness is not the goal

2. **Don't create "utils" dumping grounds**
   - Generic "utils" modules hide responsibility
   - Every module should have a clear purpose
   - Better to have `area_utils.py` than `utils.py`

3. **Don't mix layers**
   - Don't mix Home Assistant glue with domain logic
   - Don't mix policy decisions with data structures
   - Keep boundaries clear

4. **Don't prematurely optimize**
   - Don't try to design the "final" structure now
   - Don't create abstractions before patterns are clear
   - Split first, abstract later

5. **Don't change runtime behavior**
   - This is a refactoring, not a rewrite
   - User-facing behavior must remain identical
   - Config flows must work exactly as before

### File Responsibility Model

Every file should fit into one of these categories:

| Category | Description | Examples |
|----------|-------------|----------|
| **Models** | Data structures, representations, state shapes | `models.py`, `enums.py`, `area_model.py` |
| **Policy** | Decision-making, rules, feature logic | `policy.py`, `features.py`, `presence.py` |
| **Adapters** | Home Assistant-facing glue | Entity classes, platforms, config flow |
| **Plumbing** | Lifecycle, coordination, orchestration | `coordinator.py`, `__init__.py` |

**If a file doesn't clearly fit one category, leave it separate until its role becomes obvious.**

## Target Architecture

This is where we're heading (from `implementation-plan.md`):

```
custom_components/magic_areas/
  __init__.py               # Entry point, config entry lifecycle
  manifest.json             # HA metadata
  const.py                  # Shared constants

  config/                   # Configuration and schemas
    flow.py                 # Config/options flow
    filters.py              # Entity filters for UI
    schemas.py              # Config schemas
    registry.py             # Feature registry

  core/                     # HA-free domain logic
    models.py               # Data structures
    features.py             # Feature definitions
    policy.py               # Feature policy rules
    presence.py             # Presence logic
    aggregates.py           # Aggregation logic
    area.py                 # Area state logic
    enums.py                # Enumerations

  api/                      # HA integration layer
    coordinator.py          # DataUpdateCoordinator
    components.py           # Component helpers
    ha_domains.py           # HA domain constants

  platforms/                # Platform implementations
    binary_sensor/          # Binary sensor platform
    sensor/                 # Sensor platform
    switch/                 # Switch platform
    light.py                # Light platform
    fan.py                  # Fan platform
    cover.py                # Cover platform
    media_player/           # Media player platform

  helpers/                  # HA-aware utilities
    area.py                 # Area lookup helpers
    timer.py                # Timer utilities
    util.py                 # General utilities

  diagnostics.py            # Diagnostic data
  translations/             # i18n
  docs/                     # Developer docs
```

**Note**: This is the target, not a prescription. We'll move toward this structure as responsibilities become clear.

## How to Contribute

### Before Making Changes

1. **Read this document** (you're doing it!)
2. **Check `implementation-plan.md`** for current phase details
3. **Review `/docs/migration/`** to understand architectural changes
4. **Look at `CLAUDE.md`** for comprehensive development guidance

### Making Changes

1. **Identify the responsibility** you're working on
2. **Check if it fits the file responsibility model**
3. **Split if needed** (don't hesitate to create new files)
4. **Write tests** for extracted logic
5. **Ensure all tests pass** (`pytest ./tests`)
6. **Run linters** (`ruff check`, `mypy`)

### Pull Request Guidelines

1. **Small, focused PRs** are better than large ones
2. **One responsibility per PR** when possible
3. **Explain the "why"** in the PR description
4. **Reference the phase** you're working in
5. **Link to `implementation-plan.md`** if relevant

### Commit Messages

Follow conventional commits:
- `refactor: extract presence logic into core/presence.py`
- `test: add unit tests for aggregates core`
- `docs: update refactor status in REFACTOR.md`

## Testing Strategy During Refactoring

### Test Philosophy

**Tests are the safety net during refactoring.** All tests must pass after every change.

**Current Test Status (Phase 2 Ready):**
- ✅ **182 tests passing** with 95% code coverage
- ✅ **0 tight coupling to MagicArea internals** - All tests use coordinator.data
- ✅ **Config flow split into 4 files** - 51 tests organized by purpose
- ✅ **Fixtures documented** - Clear purpose and usage
- ✅ **Ready for decomposition** - Tests won't break when MagicArea is split

### How Tests Work During Decomposition

**Tests interact with the public API (coordinator), not internals:**

1. **Unit tests for core modules** (new):
   - Test pure logic in `core/presence.py`, `core/aggregates.py`, etc.
   - No Home Assistant framework dependencies
   - Run quickly, can be tested in isolation

2. **Integration tests for platforms** (existing):
   - Test through coordinator data (MagicAreasData snapshot)
   - Mock coordinator instead of internal components
   - All 182 tests continue to pass as code is refactored

3. **Config flow tests** (split into 4 files):
   - Basic form lifecycle (8 tests)
   - Options flow mechanics (14 tests)
   - Feature configurations (18 tests)
   - Error handling (11 tests)

### What Tests Can Safely Change

When refactoring, these changes are SAFE:

✅ **Extract functions from MagicArea to core/**
- Tests don't need to change (they use coordinator data)
- Can create new HA-free unit tests for extracted functions

✅ **Move logic between files**
- Tests continue to work (they test behavior, not file location)
- Platform tests unchanged

✅ **Add new core modules**
- Add unit tests for pure logic
- Integration tests verify coordinator still builds correct snapshots

### What Tests CANNOT Change

❌ **Never:**
- Change test assertions without changing code first
- Skip tests to "get things working"
- Mock coordinator data incorrectly
- Return to accessing `.area.` properties directly

### Test Maintenance During Phase 2

**Phase 2 (Current): Extract core domain logic**

Expected test status:
- ✅ All 182 existing tests pass throughout refactoring
- ✅ New unit tests added for each core module extracted
- ✅ No test modifications needed (tests use coordinator interface)

Example workflow:
```python
# Step 1: Extract logic to core/presence.py
def select_presence_sensors(area_entities: dict[str, list]) -> list[str]:
    """Pure function - testable without HA framework."""
    # ... logic extracted from MagicArea ...

# Step 2: Add unit test for pure function
async def test_select_presence_sensors():
    """Test pure logic independently."""
    result = select_presence_sensors({...})
    assert result == [...]

# Step 3: Update MagicArea to call core function
class MagicArea:
    def get_presence_sensors(self):
        return select_presence_sensors(self.entities)

# Step 4: Existing integration tests still pass
# (they call coordinator which calls MagicArea which calls core function)
```

### Coverage Goals

- **95%+ overall coverage** maintained throughout refactoring
- **100% coverage for core/* modules** (pure logic, easy to test)
- **90%+ coverage for platforms/** (test behavior, not mocking)
- **No functionality gaps** - every code path tested

### Running Tests During Development

```bash
# Quick test of specific module
pytest tests/test_core_presence.py -v

# Test a platform
pytest tests/test_light.py -v

# Test config flow
pytest tests/test_config_flow*.py -v

# Full suite (2-3 minutes)
pytest tests/ --cov=custom_components.magic_areas

# Watch for coverage gaps
pytest tests/ --cov-report=html
```

### Regression Prevention

**Tests are organized to catch regressions:**

1. **Presence tracking tests** (test_area_state.py, test_presence_timeouts.py)
   - Catch state transition bugs
   - Verify timeout logic

2. **Light group tests** (test_light.py, test_light_edge_cases.py)
   - Catch occupancy-based control bugs
   - Verify group wiring

3. **Aggregation tests** (test_aggregates.py, test_meta_aggregates.py)
   - Catch sensor grouping bugs
   - Verify aggregation logic

4. **Config flow tests** (test_config_flow*.py)
   - Catch UI/configuration bugs
   - Verify feature enabling/disabling

### When Tests Fail During Refactoring

**If a test fails:**

1. **Check the error message** - Does it indicate the code or the test is wrong?
2. **Review the change** - Did you modify behavior or just structure?
3. **Verify the assertion** - Is the test checking the right thing?
4. **Revert if unclear** - It's better to redo the refactoring than to change tests

**Do NOT:**
- ❌ Comment out failing tests
- ❌ Weaken assertions to make tests pass
- ❌ Modify tests without understanding why they failed

### Adding New Tests

When extracting new core modules:

```python
# tests/test_core_<module>.py

"""Test core/<module>.py pure logic."""

from custom_components.magic_areas.core.<module> import <function>

async def test_<function>():
    """Test <function> behavior."""
    result = <function>(input_data)
    assert result == expected_output
```

**No fixtures needed for pure logic tests!** They run quickly and in isolation.

---

## When to Advance to Recomposition

We can move from decomposition to recomposition when **all** of these are true:

- ✅ Each file's responsibility is obvious
- ✅ Duplicate concepts are visible and understood
- ✅ Import direction is mostly one-way
- ✅ Feature logic has a clear home
- ✅ Constants usage patterns are stable

**Until then, continue to favor clarity and separation over consolidation.**

## FAQ

### Q: There are too many files now. Should I consolidate some?

**A**: No, not during decomposition phase. More files is OK. We want clarity first, consolidation later.

### Q: Where should I put this new function?

**A**: Look at the file responsibility model. If it's domain logic (no HA dependencies), it goes in `core/`. If it's HA integration glue, it goes in adapters or helpers.

### Q: Can I create a new directory?

**A**: Yes! If it makes ownership clearer, create a new directory. We can always flatten later.

### Q: Should I refactor while adding a feature?

**A**: No. Refactoring and feature work should be separate. Either refactor first, then add feature, or add feature first, then refactor. Don't mix.

### Q: The code looks messy. Can I clean it up?

**A**: Define "messy":
- **Unclear responsibilities?** Yes, split files
- **Duplicated logic?** Yes, but keep it separate until patterns are clear
- **Too many files?** No, that's expected
- **Inconsistent naming?** Maybe, but low priority

### Q: How do I know if I'm done?

**A**: You're done with a refactoring task when:
1. All tests pass
2. Linters pass
3. Runtime behavior is unchanged
4. Responsibilities are clearer than before

### Q: What if I break something?

**A**: That's what tests are for! Run `pytest ./tests` frequently. If tests fail, you've changed runtime behavior - revert and try again.

### Q: Can I look at the old code?

**A**: Yes! The fork baseline is commit `d7b5779`. You can use `git diff d7b5779` to see all changes.

## Resources

- **Implementation Plan**: `implementation-plan.md` - Detailed phase breakdown
- **Migration Docs**: `/docs/migration/` - Architectural changes from fork
- **Development Guide**: `CLAUDE.md` - Comprehensive guidance for AI agents
- **HA Guidelines**: `design philosophy.md` - HA integration patterns

## Questions?

If you're unsure about a refactoring decision:
1. Check if it makes responsibilities clearer (if yes, probably good)
2. Check if it preserves behavior (if no, probably bad)
3. Ask in discussions or issues

**Remember**: Clarity precedes elegance. Expose structure first, recombine deliberately later.
