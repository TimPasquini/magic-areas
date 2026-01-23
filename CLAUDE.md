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

**For detailed migration context**, see:
- `/docs/migration/README.md` - Migration overview and delta inventory
- `/docs/migration/architecture.md` - Runtime architecture and event flow changes
- `/docs/migration/coordinator.md` - Snapshot model and availability semantics
- `/docs/migration/config-flow.md` - Config flow restructuring
- `/docs/migration/tests.md` - Test coverage delta mapping

## Development Commands

### Testing
```bash
# Full test suite with coverage
pytest ./tests --cov=custom_components.magic_areas --cov-report term-missing --numprocesses=auto

# Run specific test file
pytest tests/test_area_state.py -v

# Run with durations (slowest tests)
pytest ./tests --durations=10

# Update snapshots (for snapshot-based tests)
pytest ./tests --snapshot-update
```

### Code Quality
```bash
# Run linters via tox
tox -e lint

# Type check with mypy
mypy custom_components/magic_areas

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

**The current architecture** uses a coordinator that owns a **single, typed snapshot** per config entry:

```
DataUpdateCoordinator (MagicAreasCoordinator)
├─ Polls area state every 30 seconds
├─ Updates entity registry for area via MagicArea.load_entities()
├─ Builds MagicAreasData snapshot (SINGLE SOURCE OF TRUTH):
│  ├─ area: MagicArea or MagicMetaArea instance
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

Key file: `custom_components/magic_areas/coordinator.py`

**Platform Setup Guard Pattern:**
1. If `coordinator.data` is missing, refresh once
2. If snapshot remains unavailable, skip platform setup
3. Entities are created from snapshot data only (no direct MagicArea reads)

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

## Code Organization

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
- `entities.py` - Entity grouping and snapshots
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

### Current Refactoring (core-rebuild)

**Active refactoring phase** extracting pure helper functions from MagicArea class to:
- Improve testability (pure functions are easier to unit test)
- Stabilize internal APIs
- Allow testing pure logic independently (without HA framework overhead)
- Use immutable data structures in coordinator snapshots

Note: Platform and integration code still uses HA's testing framework (`pytest-homeassistant-custom-component`). Pure helpers in `core/` are extracted specifically to be testable as simple unit tests, which is faster and more maintainable.

**Recent commits (from git log):**
- `be8e420` - temp guidance docs
- `6ee9616` - refactor: align coordinator snapshot helpers
- `de14e38` - refactor: extract aggregates core and stabilize area events
- `3b45b3e` - refactor: introduce core meta helpers and stabilize area-driven controls
- `38880a4` - refactor: align state handling and document migration deltas

**See `/docs/migration/` for the full context** of architectural changes from the fork baseline.

## Test Structure & Patterns

### Test Organization
```
tests/
├── conftest.py           # pytest fixtures (mock_config_entry, init_integration)
├── const.py              # Test constants
├── helpers.py            # Test utilities (area setup, entity creation)
├── mocks.py              # Mock entity classes (MockLight, MockSensor, etc.)
├── test_aggregates.py    # Sensor aggregation
├── test_area_state.py    # State management
├── test_config_flow.py   # Config UI (58KB, complex)
├── test_coordinator.py   # Coordinator pattern
├── test_core_*.py        # Core module unit tests
└── test_*_platform.py    # Platform-specific tests
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
pytest tests/test_core_aggregates.py -v

# Specific test
pytest tests/test_area_state.py::test_area_presence -v

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

## Debugging Tips

- **Enable HA debug logging**: Add `logger: debug` in configuration.yaml
- **Check entity registry**: Developer Tools → Entities (in Home Assistant UI)
- **Inspect coordinator data**: Use `hass.data[DOMAIN]` → MagicAreasData (snapshot is source of truth)
- **Check coordinator refresh**: Verify `coordinator.last_update_success` for availability issues
- **Snapshots in tests**: Use `pytest --snapshot-update` to regenerate baselines
- **Mock entities**: Use helpers in `tests/helpers.py` to create realistic mocks
- **Migration docs**: If behavior seems inconsistent with expectations, check `/docs/migration/` for fork deltas