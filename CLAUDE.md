# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Magic Areas** is a Home Assistant custom integration that creates presence-aware, intelligent "magic" areas. It transforms Home Assistant's basic area concept into smart zones that automatically understand occupancy, adapt to environmental conditions, and control connected devices without manual automation.

- **Version**: 4.4.1
- **Python**: 3.13+
- **Integration Type**: Helper integration for Home Assistant
- **Quality Scale**: Bronze
- **Current Branch**: core-rebuild (refactoring core logic into testable helpers)

### IMPORTANT: This is a Fork

This repository is **forked from upstream** (baseline commit `d7b5779`) with significant architectural improvements. The `/docs/migration/` directory documents all technical deltas from the fork baseline, including:

- Runtime architecture and data flow changes
- Coordinator snapshot model introduction
- Config flow restructuring
- Platform adapter responsibilities
- Entity identity migration
- Test coverage expansions

**For detailed context**, see:
- `/docs/migration/README.md` - Migration overview and delta inventory
- `/docs/migration/architecture.md` - Runtime architecture and event flow changes
- `/docs/migration/coordinator.md` - Snapshot model and availability semantics
- `/docs/migration/config-flow.md` - Config flow restructuring
- `/docs/migration/tests.md` - Test coverage delta mapping
- `docs/contributing/implementation-plan.md` - **Phased refactoring roadmap (CRITICAL - read this)**
- `docs/contributing/design-philosophy.md` - Home Assistant integration patterns and philosophy

## Project Setup Standards

**CRITICAL: This project uses `uv` for modern Python package management.**

### Purpose
This repository is a Home Assistant custom integration implemented as a modern Python package. Development tooling, dependency resolution, linting, formatting, typing, and testing are owned by **uv** via `pyproject.toml`. Home Assistant runtime behavior and dependencies are owned exclusively by `manifest.json`.

### Standards
- Python packaging: PEP 517, 518, 621, 440, 508
- Home Assistant custom integration guidelines
- Async-only, no blocking I/O
- **No setup.py**
- **No requirements.txt**
- **No runtime dependency installation**

### Authoritative Files
- `pyproject.toml` - Build metadata, dev dependencies, tooling configuration
- `uv.lock` - Single source of truth for resolved dependencies
- `custom_components/<domain>/manifest.json` - Runtime dependencies and HA metadata

### Dependency Rules (CRITICAL)
- **Development dependencies**: Live in `pyproject.toml`, resolved by `uv`
- **Runtime dependencies**: Live ONLY in `manifest.json`
- **No dev-only packages** may be imported by integration code
- Dependency versions must not be duplicated or pinned across systems

### Documentation Placement
- **Developer-only docs**: `custom_components/<domain>/docs/` (ignored by HA at runtime)
- **User-facing docs**: Repository root (e.g., `README.md`, `/docs/`)
- **manifest.json** links to user documentation via `"documentation"` field

### Tooling (configured in pyproject.toml)
- **ruff**: Linting and formatting
- **mypy**: Strict typing (ignore missing imports acceptable)
- **pytest** + pytest-asyncio
- **pytest-homeassistant-custom-component**

### Invariants
- `uv.lock` must be reproducible in CI
- No implicit global state
- No network access during tests unless explicitly mocked
- Formatting and linting must pass with no local overrides

### Goal
Maximize determinism, minimize duplication, and ensure the integration can be developed with `uv` while remaining fully compliant with Home Assistant's runtime model.

## Development Commands

### Testing
```bash
# Full test suite with coverage
pytest ./tests --cov=custom_components.magic_areas --cov-report term-missing --numprocesses=auto

# Run specific test file
pytest tests/integration/test_area_state.py -v

# Run with durations (slowest tests)
pytest ./tests --durations=10

# Update snapshots (for snapshot-based tests)
pytest ./tests --snapshot-update
```

### Code Quality
```bash
# Run linters via tox
tox -e lint

# Type check with mypy (integration)
mypy custom_components/magic_areas

# Type check with mypy (tests)
mypy tests

# Type check both (integration + tests)
mypy custom_components/magic_areas tests

# Lint with pylint
pylint custom_components/magic_areas
```

### Testing Against HA Versions
```bash
# Test with stable Home Assistant
tox -e ha-stable

# Test with beta Home Assistant
tox -e ha-beta
```

## Architecture

### Core Design Pattern: DataUpdateCoordinator

The integration uses Home Assistant's **DataUpdateCoordinator** pattern (not entity-per-domain).

**CRITICAL ARCHITECTURAL CHANGE FROM FORK BASELINE:**

The fork baseline had each platform assemble its own view of area data by reading `MagicArea` properties directly. This caused:
- Duplicated entity filtering logic across platforms
- Inconsistent data reads when multiple platforms updated concurrently
- More surface area to update when adding features

**Current architecture** uses a coordinator that owns a **single, typed snapshot** per config entry:

```
DataUpdateCoordinator (MagicAreasCoordinator)
├─ Manages MagicArea/MagicMetaArea instance privately (_area)
├─ Polls area state every 30 seconds
├─ Updates entity registry and builds snapshot
├─ Builds MagicAreasData snapshot (SINGLE SOURCE OF TRUTH):
│  ├─ area_config: AreaConfig (immutable configuration)
│  ├─ area_runtime: AreaRuntime (mutable runtime state)
│  ├─ entities: resolved entity lists by domain
│  ├─ magic_entities: integration-generated entities by domain
│  ├─ presence_sensors: computed presence sensor IDs
│  ├─ active_areas: active child areas (meta only)
│  ├─ config: merged config options
│  ├─ enabled_features: set of enabled feature IDs
│  ├─ feature_configs: per-feature configuration
│  └─ updated_at: UTC timestamp
└─ Platforms read coordinator.data ONLY (snapshot is authoritative)
```

**Key design principle**: `MagicArea` instance is internal to coordinator (private `_area`). Platforms and entities interact solely through immutable snapshot fields (AreaConfig, AreaRuntime, etc.), never the object itself.

Key file: `custom_components/magic_areas/coordinator.py`

**Platform Setup Guard Pattern:**
1. If `coordinator.data` is missing, refresh once
2. If snapshot remains unavailable, skip platform setup
3. Entities are created from snapshot data only (no direct MagicArea access)

**Entity Constructor Pattern:**
- Entities receive `area_config: AreaConfig` and `coordinator: MagicAreasCoordinator` in constructor
- All necessary data is in immutable snapshot fields (AreaConfig, AreaRuntime)
- Entities do NOT receive MagicArea instance

### Area Hierarchy

- **MagicArea**: Regular areas with presence tracking and feature control
- **MagicMetaArea**: Meta-areas aggregating child areas (Global, Interior, Exterior, Floor-based)
- One config entry per area (not per domain like typical integrations)

### Area State Management

Each area tracks multiple states:
- **Primary**: `occupied` or `clear`
- **Secondary**: `extended` (occupied beyond timeout), `dark`/`bright`, `sleep`, `accented`

State transitions and timeouts: `custom_components/magic_areas/base/magic.py`

### Event Flow (Changed from Fork Baseline)

**CRITICAL CHANGE:** Event payloads now include **current state snapshots** to prevent stale reads.

**Fork baseline:** Handlers read `MagicArea` state directly during async scheduling, causing race conditions.

**Current architecture:**
```
Presence tracking updates
  └─ binary_sensor/presence.py
       ├─ Computes new, lost, and current area states
       └─ Dispatches AREA_STATE_CHANGED(area_id, (new, lost, current))

Platform handlers (light groups, climate control, fan control, media player)
  └─ React to current state snapshot from event payload (not MagicArea)
     └─ Deterministic, no stale reads during async scheduling
```

This ensures handlers see consistent state even during concurrent updates.

## 🚨 CRITICAL: Refactoring Guidelines (Active Decomposition Phase)

**This integration is currently mid-refactor in the DECOMPOSITION phase.**

### Current Phase: Decomposition

The integration is being actively refactored from several very large, monolithic modules into smaller, more focused files. **This has intentionally increased the number of files and directories.** The resulting file sprawl is **expected and temporary**.

**Primary Goal**: Expose logical seams, clarify responsibility boundaries, and make future recomposition possible without changing runtime behavior.

### What This Means for Development

**In the decomposition phase:**
- Large files are split even if the final structure is not yet known
- File count and directory depth may temporarily increase
- Names and locations may be provisional
- **Architectural clarity is more important than visual neatness**

**DO NOT:**
- ❌ Attempt to optimize or finalize structure during this phase
- ❌ Collapse files to reduce visual clutter
- ❌ Create generic "utils" modules as dumping grounds
- ❌ Prematurely recombine files
- ❌ Consolidate solely to reduce file count
- ❌ Optimize for aesthetics instead of clarity
- ❌ Mix Home Assistant glue with domain logic

**DO:**
- ✅ Preserve behavior exactly (structural changes must not alter logic)
- ✅ Prefer smaller, single-responsibility files over merged abstractions
- ✅ Keep imports directional (avoid circular dependencies)
- ✅ Make ownership clear (if a change makes ownership less clear, it's wrong)
- ✅ Split files even if you're not sure of the final structure

### Home Assistant Doesn't Care About

Home Assistant evaluates integrations based on **runtime behavior**, not internal organization. While refactoring:
- ✅ Imports must remain valid
- ✅ Config flows must remain stable
- ✅ Entities must register correctly
- ✅ Async patterns must be preserved

Home Assistant **does not care** about:
- Internal folder count
- File naming symmetry
- Temporary fragmentation
- Intermediate layouts

### File Responsibility Model

Every file should clearly belong to one primary responsibility category:

- **Models**: Data structures, representations, and state shapes
- **Policy**: Decision-making, rules, feature logic
- **Adapters**: Home Assistant-facing glue (entities, platforms, config flow)
- **Plumbing**: Lifecycle, coordination, orchestration

**Files that do not clearly fit one category should remain separate** until their role becomes obvious.

### When to Advance to Recomposition

The project is ready to move from decomposition to recomposition when:
- ✅ Each file's responsibility is obvious
- ✅ Duplicate concepts are visible and understood
- ✅ Import direction is mostly one-way
- ✅ Feature logic has a clear home
- ✅ Constants usage patterns are stable

**Until these conditions are met, continue to favor clarity and separation over consolidation.**

### Reorganization Constraints

When eventually recomposing files:
- No runtime behavior changes permitted
- All imports must remain under `custom_components.magic_areas`
- Platform modules must remain thin and declarative
- Coordinators own data fetching and update logic
- Entities must not perform I/O or policy decisions
- Constants must be centralized and deduplicated
- Config flow logic must remain isolated from core logic

### Intent

**Expose structure first. Recombine deliberately later. Clarity precedes elegance.**

## Target Architecture (from docs/contributing/implementation-plan.md)

The refactoring is moving toward this **target module layout**:

### Target: custom_components/magic_areas/core/ (HA-free helpers)
- **Purpose**: Area model, state evaluation, entity assembly, derived values
- **Key principle**: No HA entity classes or registry calls (pure logic)
- **Modules**:
  - `core/area_model.py` - Core representation of MagicArea state
  - `core/entity_loading/` - Entity ingestion package (`loader.py`, `registry_queries.py`, `filters.py`, `snapshots.py`)
  - `core/presence.py` - Presence, timeouts, and secondary states
  - `core/aggregates.py` - Aggregate sensor logic
  - `core/meta.py` - Meta area orchestration and child area resolution
  - `core/config.py` - Feature configuration normalization

### Target: coordinator.py
- Owns snapshot construction and refresh lifecycle
- Exposes `MagicAreasData` as the **only read model** for platforms
- Translates `MagicArea` into snapshot fields used by entities
- No platform-specific filtering outside snapshot building

### Target: platforms/ (entity wiring only)
- Convert snapshot data into entity instances only
- No domain logic beyond HA entity wiring
- Use shared base entity classes where possible
- All entity filtering snapshot-based, not registry-based

### Target: config/ (schemas and validation)
- Schemas, validation, and feature metadata
- Config flow helpers and selectors
- Reusable option-building helpers with consistent patterns

## Current Code Organization (transitioning to target)

### Core Modules (custom_components/magic_areas/)

**coordinator.py** - DataUpdateCoordinator implementation
- Builds periodic snapshots of area state
- Loads entity registry
- Returns MagicAreasData

**config_flow.py** - Configuration UI (48KB, complex multi-step flow)
- Per-area configuration
- Feature enable/disable
- Sensor selection and thresholds
- **CHANGED FROM FORK:** Now registry-driven (see below)

**config_flows/feature_registry.py** - Feature metadata registry (NEW)
- Declarative feature configuration (name, options, schema, merge behavior)
- Generic feature handler (`async_step_feature_conf`)
- Replaces long class with feature-specific branches
- Centralizes schemas, selectors, and validators

**base/magic.py** - Core MagicArea and MagicMetaArea classes (25KB)
- Entity tracking and registry management
- State transitions and presence logic
- Feature management

**core/** - Pure helper functions (active refactoring target)
- `aggregates.py` - Sensor aggregation by device class
- `presence.py` - Presence sensor selection logic
- `meta.py` - Meta-area helpers
- `entity_loading/` - Entity ingestion + grouping pipeline
- `config.py` - Feature configuration normalization
- `area_model.py` - AreaDescriptor dataclass

**Platform Implementations**
- `light.py` (21KB) - Smart light groups with overhead/task/accent/sleep categories
- `binary_sensor/` - Presence tracking, BLE, "Wasp in a Box" (door+motion hybrid)
- `sensor/` - Aggregated sensor groups (temperature, humidity, CO2, etc.)
- `switch/` - Feature toggles (presence hold, light control, media control)
- `fan.py`, `climate.py`, `cover.py`, `media_player/` - Device aggregation and control

**Configuration & Constants** (RESTRUCTURED FROM FORK)

Fork baseline had centralized `const.py`. Now split into focused modules:
- `features.py` - 12 feature flags (climate_control, light_groups, aggregates, health, etc.)
- `feature_info.py` - Feature metadata and translations
- `enums.py` - MetaAreaType, AreaStates, CalculationMode
- `config_keys.py` - All config keys and default values (NEW)
- `defaults.py` - Default policy values and feature defaults (NEW)
- `policy.py` - Feature availability by area type
- `threshold.py` - Sensor-based automation thresholds
- `area_constants.py` - Area-related constants
- `area_maps.py` - Area mapping utilities
- `ha_domains.py` - Home Assistant domain constants
- `icons.py` - Icon handling

### Helper Functions
- `helpers/area.py` - Area lookup utilities
- `helpers/timer.py` - Presence timeout logic
- `util.py` - General utilities
- `diagnostics.py` - Diagnostic data collection

## Key Architectural Patterns

### Presence Tracking (Multi-Source)
1. Binary sensors (motion, occupancy by device class)
2. Device trackers (GPS location)
3. Media players (entertainment-based presence)
4. BLE trackers (Bluetooth beacons)
5. Presence hold switch (manual override)
6. "Wasp in a Box" - Hybrid door+motion logic to prevent false negatives

See `custom_components/magic_areas/core/presence.py`

### Feature System
Features are individually enabled and configured per area:
- **Light Groups** - Overhead, task, accent, sleep with occupancy control
- **Climate Control** - Preset switching based on area state
- **Aggregates** - Grouped sensors by device class
- **Health** - Safety sensors (gas, smoke, moisture, problem)
- **Fan Groups** - Auto-control by aggregated values
- **Media Player Groups** - Area-aware notification routing
- **Presence Hold** - Manual occupied state override
- **BLE Trackers** - Text-based sensor integration
- **Wasp in a Box** - Door+motion reliability
- **Cover Groups** - Coordinated blind/shade control

Configuration stored per-area in ConfigEntry data/options.

### Current Refactoring (core-rebuild) - Phased Implementation Plan

**CRITICAL: This is a structured, multi-phase refactoring** documented in `docs/contributing/implementation-plan.md`.

**Current Status:** Phase 1 complete, **Phase 2 in progress**

#### Goals (from docs/contributing/implementation-plan.md)
- Reduce cross-module coupling and duplicated logic
- Centralize runtime data shaping in coordinator snapshot
- Keep platform files focused on entity wiring only
- Preserve current user-facing behavior and config flow UX
- Improve testability by isolating domain logic from HA entity classes
- Make future feature additions require changes in one place (core or config)
- Keep identifiers stable and HA-aligned (durable unique_id, no domain in unique_id)
- Align availability semantics with coordinator outcomes

#### Non-Goals (IMPORTANT - DO NOT DO THESE)
- Redesign user-facing features or behavior
- Change config entry data format unless required by HA
- Remove features or reduce existing platform coverage
- Introduce new platforms during refactor
- Rewrite tests for style or aesthetic changes

#### Constraints
- Python 3.13+
- HA integration patterns (config flow, options flow, coordinator, entities)
- Strict typing kept consistent with platinum goal
- **Tests remain green throughout refactors**
- **No breaking changes to existing config entry data**
- Avoid large-scale renames that make diffs hard to review

#### Refactoring Phases

**Phase 1: Align boundaries** ✅ COMPLETE
- Snapshot is single source of truth for platform setup
- Coordinator refresh before platform setup (no area fallbacks)
- All platforms now read snapshot fields only

**Phase 2: Extract core domain logic** ✅ COMPLETE (2026-02-08)
- Split `base/magic.py` into focused modules (presence, aggregates, meta state)
- Keep pure logic modules free of HA entity references
- Update coordinator to call these modules
- Consolidate filtering and derived-state rules into core modules

**Phase 2 Completed:**
- ✅ Core helpers extracted for config, presence, entity grouping
- ✅ Aggregates logic extracted (`core/aggregates.py` - 90% coverage)
- ✅ Unique ID format updated with migration support and tests
- ✅ Entity availability follows coordinator refresh
- ✅ `base/magic.py` reduced to orchestration (88% coverage)
- ✅ Event handlers use payload snapshots (no stale reads)
- ✅ 95% overall test coverage (235 tests passing)

**Phase 3: Simplify platform adapters** ✅ COMPLETE
- Extracted state priority logic (`core/state_priority.py`)
- Extracted climate/fan control policy (`core/climate_control.py`, `core/fan_control.py`)
- Extracted light group control logic (`core/light_control.py`)
- Platform files reduced to HA service calls and event wiring
- 95% coverage maintained

**Phase 4: Config flow modularization** ✅ COMPLETE
- Extracted selector builders (`schemas/selectors.py`)
- Extracted climate preset builder (`schemas/feature_builders.py`)
- Extracted validation helpers (`config_flows/helpers.py`)
- Config flow reduced from 1319 → 1209 lines (110 lines removed)

**Phase 5: Repository alignment & cleanup** ✅ COMPLETE (2026-02-11)
- Removed all legacy packaging files (requirements*, setup.cfg, tox.ini, etc.)
- Removed obsolete directories (scripts/, config/, base/)
- Renamed `core_constants.py` → `const.py` (HA convention)
- Organized documentation in `docs/contributing/`
- Fixed hacs.json (added missing domain field)
- Removed 36 unused imports, fixed deprecated ruff config
- 340 tests passing, 95% coverage maintained

**See `/docs/migration/` for architectural changes** and **`docs/contributing/docs/contributing/implementation-plan.md` for detailed roadmap**.

## Test Structure & Patterns

### Test Organization
```
tests/
├── conftest.py              # pytest fixtures (mock_config_entry, init_integration)
├── const.py                 # Test constants
├── helpers.py               # Test utilities (area setup, entity creation)
├── mocks.py                 # Mock entity classes (MockLight, MockSensor, etc.)
├── unit/                    # Core logic unit tests
├── integration/             # HA integration tests (area/coordinator lifecycle)
├── platforms/               # Platform-specific tests (light/switch/etc.)
├── config_flow/             # Config flow and options flow tests
└── snapshots/               # Syrupy snapshot tests
```

### Key Test Patterns

**Fixtures (conftest.py)**:
- `mock_config_entry` - MockConfigEntry with defaults
- `init_integration` - Full integration initialization
- Platform-specific fixtures
- Auto-patching for reload delays

**Mock Objects (mocks.py)**:
- MockBinarySensor, MockLight, MockSensor, etc.
- Realistic entity metadata (object_id, entity_id, device_class, etc.)

**Test Helpers (helpers.py)**:
- `create_mock_area_registry()` - Set up area fixture
- `create_entity_registry_entry()` - Create mock entities
- `create_config_entry()` - Generate ConfigEntry
- `async_init_integration()` - Full HA setup

### Running Tests

```bash
# Full suite
pytest tests/

# Specific test file
pytest tests/unit/test_core_aggregates.py -v

# Specific test
pytest tests/integration/test_area_state.py::test_area_presence -v

# With snapshots
pytest tests/test_config_flow.py --snapshot-update
```

### Coverage & Type Checking

- Target: 95%+ coverage
- Type checking: mypy (strict mode - check_untyped_defs, disallow_incomplete_defs)
- Code style: black (88 char line), ruff

## Important Files to Understand

**Start here (CRITICAL - this is a fork):**
1. `/docs/migration/README.md` - **READ THIS FIRST** - Explains all deltas from fork baseline
2. `/docs/migration/architecture.md` - Runtime architecture changes
3. `/docs/migration/coordinator.md` - Snapshot model and platform setup
4. `README.md` - Feature overview and installation
5. `AGENTS.md` - Comprehensive Home Assistant coding standards (1174 lines)

**Core to understand the integration:**
1. `custom_components/magic_areas/models.py` - Runtime data structures (MagicAreasData)
2. `custom_components/magic_areas/coordinator.py` - Data flow pattern (FORK DELTA)
3. `custom_components/magic_areas/base/magic.py` - MagicArea core class
4. `custom_components/magic_areas/__init__.py` - Entry point with unique ID migration

**Logic to understand:**
1. `custom_components/magic_areas/core/presence.py` - Presence sensor selection
2. `custom_components/magic_areas/core/aggregates.py` - Sensor grouping
3. `custom_components/magic_areas/features.py` - Feature definitions
4. `custom_components/magic_areas/config_flow.py` - Configuration UI (registry-driven)
5. `custom_components/magic_areas/config_flows/feature_registry.py` - Feature metadata (NEW)

## Important Notes

- **One Config Entry Per Area**: Unlike typical HA integrations, this has a config entry per area (not per domain). Each area is independently configured.
- **Coordinator Pattern**: Platform entities subscribe to coordinator updates via listeners rather than polling individually.
- **Immutable Snapshots**: MagicAreasData is a frozen dataclass passed to platforms - don't mutate it.
- **Policy-Based Features**: Feature availability is controlled by `policy.py` - check area type and feature rules before assuming a feature is enabled.
- **Pure vs. Impure Code**: New code should extract pure helpers into `core/` modules (see current refactoring phase). These are easier to test and maintain.
- **Device Class Assumptions**: The integration heavily uses device classes for entity grouping. Entities without proper device_class won't be aggregated.
- **Unique ID Migration (CHANGED FROM FORK)**: Unique IDs updated to remove domain prefixes and use stable area IDs. Migration code in `__init__.py` updates entity registry on startup. See `/docs/migration/architecture.md` for details.
- **Availability Semantics (CHANGED FROM FORK)**: Entity availability is tied to coordinator refresh success (`area.last_update_success`). Diagnostics read snapshot data for consistency.

## Home Assistant Integration Patterns

This follows Home Assistant's patterns from AGENTS.md:
- DataUpdateCoordinator for data management (not entity-per-domain)
- Unique IDs for all entities
- Entity registry tracking
- Config entry options flow for runtime config
- Async/await throughout
- Proper error handling and logging

For detailed Home Assistant standards and patterns, see `AGENTS.md` (1174 lines).

## Configuration Entry Structure

```python
config_entry.data:
  "areas": [list of area UUIDs]

config_entry.options:
  Per-area feature configuration:
  {
    "features": {...},
    "features_config": {
      "light_groups": {...},
      "climate_control": {...},
      ...
    }
  }
```

See `config_flow.py` for configuration structure details.

## Home Assistant Integration Patterns Reference

This section captures essential Home Assistant patterns. For comprehensive HA guidelines, see the original `AGENTS.md` in repository history.

### Quality Scale (Bronze Tier - Current Target)

Home Assistant uses a quality scale: Bronze (baseline) → Silver → Gold → Platinum

**This integration targets Bronze tier**. Key Bronze requirements:
- ✅ UI config flow with automated tests
- ✅ Unique IDs for all entities
- ✅ DataUpdateCoordinator pattern
- ✅ Async-only, no blocking I/O
- ✅ Proper availability semantics
- ✅ Type hints (working toward Platinum strict typing)

### Critical HA Rules

**Async Programming**:
- All I/O operations must be async
- No blocking calls in event loop
- Use `await hass.async_add_executor_job()` for blocking operations
- Group operations with `asyncio.gather()` instead of awaiting in loops

**Entity Patterns**:
- Properties must be cheap, memory-only reads (no I/O)
- Use `unique_id` for entity registry (durable, no domain prefix)
- Entities link to devices via `device_info`
- Mark unavailable when data cannot be fetched (don't show stale state)

**DataUpdateCoordinator**:
- Single coordinator per config entry
- Centralized data fetching
- Entities read coordinator data (no direct polling)
- `coordinator.data` is the single source of truth

**Config Entry Runtime Data**:
```python
type MyIntegrationConfigEntry = ConfigEntry[MyClient]

async def async_setup_entry(hass: HomeAssistant, entry: MyIntegrationConfigEntry) -> bool:
    client = MyClient(entry.data[CONF_HOST])
    entry.runtime_data = client
```

**Import Rules**:
- Use shared constants from `homeassistant.const` when available
- No circular dependencies
- Keep imports directional (core → helpers → platforms)

### Code Quality Standards

**Formatting & Linting**:
- **ruff**: Primary linter and formatter
- **mypy**: Strict type checking
- **pytest**: Testing framework
- Address issues at the source before using suppressions

**Python Requirements**:
- Python 3.13+ (use modern features: pattern matching, type hints, dataclasses)
- American English for all code/comments/docs
- Sentence case for user-facing messages

**Testing**:
- All Bronze tier integrations require automated tests
- Use pytest with fixtures
- Mock external I/O
- Aim for 95%+ coverage

## Debugging Tips

- **Enable HA debug logging**: Add `logger: debug` in configuration.yaml
- **Check entity registry**: Developer Tools → Entities (in Home Assistant UI)
- **Inspect coordinator data**: Use `hass.data[DOMAIN]` → MagicAreasData (snapshot is source of truth)
- **Check coordinator refresh**: Verify `coordinator.last_update_success` for availability issues
- **Snapshots in tests**: Use `pytest --snapshot-update` to regenerate baselines
- **Mock entities**: Use helpers in `tests/helpers.py` to create realistic mocks
- **Migration docs**: If behavior seems inconsistent with expectations, check `/docs/migration/` for fork deltas
