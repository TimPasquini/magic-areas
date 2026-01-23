# Test coverage differences

This document outlines how the test suite differs from the fork baseline
(commit `d7b5779`) and how it supports the HA Bronze tier requirements.

## Bronze alignment

The Bronze tier requires:

- UI setup support with automated tests for config flow
- baseline coding standards
- stable, documented behavior for new users

The suite validates UI setup paths, configuration options, and runtime
behavior so baseline requirements are demonstrably met.

## Current test scope (delta summary)

Compared to the fork baseline, the suite now covers:

- coordinator snapshot creation and platform gating
- config flow and options flow for all feature steps
- core helper logic for config normalization, presence selection, and entity
  grouping
- platform snapshot usage across all supported domains
- availability behavior driven by coordinator refresh
- expanded edge cases for lights, presence, and control switches

## Coverage by area

### Core integration setup and lifecycle

- `tests/test_component_init.py`: entry setup, reload behavior, and coordinator
  setup/teardown paths.
- `tests/test_init.py`: migration and entry setup expectations.
- `tests/test_cleanup.py`: unload paths and teardown stability.
- `tests/test_area_reload.py`: reload behavior when registry changes occur.
- `tests/test_helpers_area.py`: area helper behavior and runtime data access.
- `tests/test_availability.py`: coordinator-driven availability behavior.

### Config flow and options flow

- `tests/test_config_flow.py`: full options flow coverage, error paths,
  selectors, and feature configuration steps.
- `tests/test_exceptions.py`: config flow and setup exceptions.
- `tests/AGENTS.md`: testing guidelines reinforced to avoid HA API drift.

### Coordinator and snapshot behavior

- `tests/test_coordinator.py`: snapshot creation and update failure handling.
- `tests/test_core_config.py`: core feature config normalization.
- `tests/test_core_presence.py`: core presence sensor selection.
- `tests/test_core_entities.py`: core entity grouping and normalization.

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

- `tests/test_media_player.py`: area-aware media player behavior and
  notifications.

### Switches and controls

- `tests/test_switch.py`: switch behavior for control features.
- `tests/test_switch_setup.py`: setup error handling and cleanup.
- `tests/test_switch_media_player_control.py`: media player control switch logic.
- `tests/test_fan_setup.py`, `tests/test_cover_setup.py`: platform setup error
  handling.
- `tests/test_climate_control.py`: climate control behaviors.
- `tests/test_cover.py`, `tests/test_fan.py`: platform feature behavior.

### Supporting fixtures and utilities

- `tests/conftest.py`: shared fixtures and integration setup helpers.
- `tests/helpers.py`: integration and registry setup helpers.
- `tests/mocks.py`: updated mocks for stable entity behavior.
- `tests/const.py`: test constants and mock area definitions.
- `tests/test_diagnostics.py`: diagnostics output and redaction.
- `tests/test_icons.py`: icon handling.
- `tests/test_restore.py`: restore behaviors.
- `tests/test_timer.py`: timer behavior.
- `tests/test_magic.py`: core integration behaviors.

## Delta map (tests to changes)

This map ties key deltas to the tests that now cover them.

- Coordinator snapshot gating and availability:
  - `tests/test_coordinator.py`
  - `tests/test_availability.py`
- Core helper extraction:
  - `tests/test_core_config.py`
  - `tests/test_core_presence.py`
  - `tests/test_core_entities.py`
- Platform snapshot usage:
  - `tests/test_cover.py`
  - `tests/test_fan.py`
  - `tests/test_media_player.py`
  - `tests/test_switch.py`
  - `tests/test_threshold.py`
- Event payload updates and state-change handling:
  - `tests/test_light_complex.py`
  - `tests/test_light_edge_cases.py`
  - `tests/test_switch.py`
- Identity and migration changes:
  - `tests/test_init.py`
  - `tests/test_magic.py`

## Guidance for future tests

- Prefer behavior-based assertions over internal helper calls.
- Use coordinator snapshot data rather than raw registry reads where possible.
- Ensure new features include config flow tests and a setup path test.
