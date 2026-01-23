# Test Directory Organization

This directory contains 209 tests organized into logical categories for the Magic Areas Home Assistant integration.

## Directory Structure

```
tests/
├── conftest.py              # Global pytest fixtures (shared by all tests)
├── const.py                 # Test constants and mock area definitions
├── helpers.py               # Shared test helper functions
├── mocks.py                 # Mock entity classes for testing
├── __init__.py              # Package marker
│
├── unit/                    # Unit tests (HA-free core logic)
│   ├── test_core_*.py       # Core module tests: aggregates, config, entities, meta, presence
│   ├── test_icons.py        # Icon mapping tests
│   └── test_timer.py        # Timer utility tests
│   └── Total: 7 tests
│
├── integration/             # Integration tests (requires Home Assistant framework)
│   ├── test_init.py         # Component initialization tests
│   ├── test_component_init.py # Component setup tests
│   ├── test_coordinator.py   # Data coordinator tests
│   ├── test_area_*.py        # Area management: state, reload
│   ├── test_meta_area_state.py # Meta area state tests
│   ├── test_availability.py  # Entity availability tests
│   ├── test_presence_timeouts.py # Presence timeout tests
│   ├── test_cleanup.py       # Cleanup and shutdown tests
│   ├── test_restore.py       # State restoration tests
│   ├── test_diagnostics.py   # Diagnostics tests
│   ├── test_exceptions.py    # Exception handling tests
│   ├── test_magic.py         # Core magic entity tests
│   └── test_helpers_area.py  # Area helper function tests
│   └── Total: 14 tests
│
├── platforms/               # Platform-specific implementation tests
│   ├── test_light*.py        # Light entity tests (4 files)
│   ├── test_binary_sensor*.py # Binary sensor tests (2 files)
│   ├── test_sensor*.py        # Sensor tests (2 files)
│   ├── test_switch*.py        # Switch tests (3 files)
│   ├── test_climate_control.py # Climate control tests
│   ├── test_fan*.py          # Fan tests (2 files)
│   ├── test_cover*.py        # Cover tests (2 files)
│   ├── test_media_player.py  # Media player tests
│   ├── test_threshold.py     # Threshold tests
│   ├── test_health.py        # Health monitoring tests
│   ├── test_wasp_in_a_box.py # BLE device monitoring tests
│   └── test_ble_tracker_monitor.py # BLE tracker monitoring tests
│   └── Total: 20+ tests
│
├── config_flow/             # Configuration flow tests
│   ├── test_config_flow_basic.py # Basic config flow tests
│   ├── test_config_flow_options.py # Options flow tests
│   ├── test_config_flow_features.py # Feature configuration tests
│   └── test_config_flow_errors.py # Error handling tests
│   └── Total: 38 tests
│
└── snapshots/               # Snapshot tests (Syrupy)
    ├── test_snapshots_config_flow.py # Config flow structure snapshots
    ├── test_snapshots_coordinator.py # Coordinator data snapshots
    ├── test_snapshots_entities.py # Entity structure snapshots
    └── __snapshots__/        # Generated snapshot baseline files (.ambr)
    └── Total: 27 tests
```

## Test Categories

### Unit Tests (`unit/`)
- **Purpose**: Test core business logic without Home Assistant framework dependencies
- **Requirements**: None (pure Python tests)
- **Examples**: Config parsing, aggregate selection, presence calculations
- **Run with**: `pytest tests/unit/`

### Integration Tests (`integration/`)
- **Purpose**: Test component integration with Home Assistant
- **Requirements**: Home Assistant test framework
- **Examples**: Coordinator setup, area state management, entity availability
- **Run with**: `pytest tests/integration/`

### Platform Tests (`platforms/`)
- **Purpose**: Test platform-specific entity implementations (Light, Switch, Sensor, etc.)
- **Requirements**: Home Assistant test framework
- **Examples**: Light group creation, sensor value calculations, switch control logic
- **Run with**: `pytest tests/platforms/`

### Config Flow Tests (`config_flow/`)
- **Purpose**: Test user configuration flows and validation
- **Requirements**: Home Assistant test framework
- **Examples**: Config entry creation, options updates, feature configuration
- **Run with**: `pytest tests/config_flow/`

### Snapshot Tests (`snapshots/`)
- **Purpose**: Verify data structure consistency using baseline snapshots
- **Framework**: Syrupy snapshot testing
- **Examples**: Config entry structure, coordinator data layout, entity definitions
- **Update snapshots**: `pytest tests/snapshots/ --snapshot-update`
- **Run with**: `pytest tests/snapshots/`

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run tests by category
```bash
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest tests/platforms/      # Platform tests only
pytest tests/config_flow/    # Config flow tests only
pytest tests/snapshots/      # Snapshot tests only
```

### Run specific test file
```bash
pytest tests/integration/test_coordinator.py -v
```

### Run with coverage
```bash
pytest tests/ --cov=custom_components.magic_areas --cov-report=html
```

### Update snapshots
When snapshot tests fail with legitimate changes:
```bash
pytest tests/snapshots/ --snapshot-update
```

## Fixtures and Helpers

### Global Fixtures (in `conftest.py`)
- `hass`: Home Assistant test instance
- `init_integration`: Initialized integration with config entry
- `mock_config_entry`: Mock config entry for areas
- `mock_areas_and_entities`: Pre-created mock entities for testing
- Various timer and delay fixtures

### Test Constants (in `const.py`)
- `DEFAULT_MOCK_AREA`: Default test area configuration
- `MOCK_AREAS`: Collection of pre-defined test areas
- `MockAreaIds`: Enumeration of mock area identifiers

### Test Helpers (in `helpers.py`)
- `get_basic_config_entry_data()`: Create basic config entry
- `init_integration()`: Initialize integration with test setup
- `async_call_service()`: Call Home Assistant service
- Various entity setup helpers

### Mock Entities (in `mocks.py`)
- `MockLight`: Mock light entity
- `MockBinarySensor`: Mock binary sensor
- `MockSwitch`: Mock switch entity
- Other platform-specific mock entities

## Test Statistics

- **Total Tests**: 209
- **Unit Tests**: 7
- **Integration Tests**: 14
- **Platform Tests**: 20+
- **Config Flow Tests**: 38
- **Snapshot Tests**: 27 (captured structure snapshots)

## Coverage

Current test coverage: ~95% of core components

To view detailed coverage:
```bash
pytest tests/ --cov=custom_components.magic_areas --cov-report=html
```

## Adding New Tests

1. **For core logic**: Add to `unit/test_core_*.py`
2. **For HA integration**: Add to `integration/test_*.py`
3. **For platform features**: Add to `platforms/test_<platform>.py`
4. **For config flow**: Add to `config_flow/test_config_flow_*.py`
5. **For structure verification**: Add to `snapshots/test_snapshots_*.py`

All tests automatically have access to global fixtures via the root `conftest.py`.

## Import Patterns

Tests use absolute imports from the root tests package:

```python
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import init_integration
from tests.mocks import MockLight
```

Fixtures from parent conftest.py are automatically available to all subdirectory tests.

## Notes

- Snapshot files are auto-generated in `__snapshots__/` directories
- All imports use absolute paths (from `tests.*`) for consistency
- Root-level conftest.py provides fixtures to all subdirectories
- Python path includes the repository root for easy imports of custom_components
