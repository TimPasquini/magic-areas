# Test coverage differences

This document outlines how the current test suite differs from the original
fork baseline and how it supports the HA Bronze tier requirements.

## Bronze alignment

The Bronze tier requires:

- UI setup support with automated tests for config flow
- baseline coding standards
- stable, documented behavior for new users

The current suite validates UI setup paths, configuration options, and runtime
behavior so baseline requirements are demonstrably met.

## Current test scope

Compared to the original baseline, the current suite covers more of the
integration surface area. The list below reflects the present scope and how it
maps to runtime behavior.

### Core integration setup and lifecycle

- `tests/test_component_init.py`: entry setup, reload behavior, and coordinator setup/teardown paths.
- `tests/test_init.py`: migration and entry setup expectations.
- `tests/test_cleanup.py`: unload paths and teardown stability.
- `tests/test_area_reload.py`: reload behavior when registry changes occur.
- `tests/test_helpers_area.py`: area helper behavior and runtime data access.

### Config flow and options flow

- `tests/test_config_flow.py`: full options flow coverage, error paths, selectors, and feature configuration steps.
- `tests/test_exceptions.py`: config flow and setup exceptions.
- `tests/AGENTS.md`: testing guidelines reinforced to avoid HA API drift.

### Coordinator and snapshot behavior

- `tests/test_coordinator.py`: snapshot creation and update failure handling.

### Sensor and aggregate behavior

- `tests/test_sensor.py`: aggregate sensor creation and error handling.
- `tests/test_aggregates.py`: aggregate logic for multiple sensors and filters.
- `tests/test_meta_aggregates.py`: meta-area aggregate behavior.
- `tests/test_threshold.py`: threshold sensors and edge cases.

### Binary sensor and presence tracking

- `tests/test_area_state.py`: presence and secondary state behavior.
- `tests/test_presence_timeouts.py`: clear/extended timeout behavior.
- `tests/test_binary_sensor_coverage.py`: binary sensor coverage gaps.
- `tests/test_ble_tracker_monitor.py`: BLE tracker monitor behavior.
- `tests/test_health.py`: health binary sensor aggregation.
- `tests/test_wasp_in_a_box.py`: wasp-in-a-box behavior and edge cases.

### Lights, light groups, and meta areas

- `tests/test_light.py`: light group setup and service forwarding.
- `tests/test_light_complex.py`: multi-group and feature combinations.
- `tests/test_light_edge_cases.py`: edge cases and restoration behavior.
- `tests/test_light_meta.py`: meta-area light behavior.
- `tests/test_meta_area_state.py`: meta-area state aggregation.

### Media player and audio features

- `tests/test_media_player.py`: area-aware media player behavior and notifications.

### Switches and controls

- `tests/test_switch.py`: switch behavior for control features.
- `tests/test_switch_setup.py`: setup error handling and cleanup.
- `tests/test_switch_media_player_control.py`: media player control switch logic.
- `tests/test_fan_setup.py`, `tests/test_cover_setup.py`: platform setup error handling.

### Supporting fixtures and utilities

- `tests/conftest.py`: shared fixtures and integration setup helpers.
- `tests/helpers.py`: integration and registry setup helpers.
- `tests/mocks.py`: updated mocks for stable entity behavior.
- `tests/const.py`: test constants and mock area definitions.

## Why this improves Bronze readiness

- UI setup paths and options flow are comprehensively tested.
- Platform setup logic is exercised through integration-level tests.
- Coordinator snapshots are validated so runtime behavior is deterministic.
- Tests confirm stable, user-visible behavior rather than internal details.

## Guidance for future tests

- Prefer behavior-based assertions over internal helper calls.
- Use coordinator snapshot data rather than raw registry reads where possible.
- Ensure new features include config flow tests and a setup path test.
