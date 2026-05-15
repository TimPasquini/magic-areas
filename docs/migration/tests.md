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
- managed HA helper/label reconciliation and stale cleanup
- control-intent target modeling and member-level light suppression
- Adaptive Lighting switch-set discovery, intent generation, execution, and
  managed config reconciliation

## Coverage by area

### Core integration setup and lifecycle

- `tests/integration/test_component_init.py`: entry setup, reload behavior, and coordinator
  setup/teardown paths.
- `tests/integration/test_init.py`: migration and entry setup expectations.
- `tests/integration/test_cleanup.py`: unload paths and teardown stability.
- `tests/integration/test_area_reload.py`: reload behavior when registry changes occur.
- `tests/integration/test_helpers_area.py`: area helper behavior and runtime data access.
- `tests/integration/test_availability.py`: coordinator-driven availability behavior.
- `tests/integration/test_platform_initialization.py`: platform startup parity and
  setup sequencing.
- `tests/integration/test_cache_synchronization.py`: coordinator/cache lifecycle
  synchronization.
- `tests/integration/test_error_recovery_paths.py`: setup/runtime recovery behavior.

### Config flow and options flow

- `tests/config_flow/test_config_flow_basic.py`: base config flow paths.
- `tests/config_flow/test_config_flow_options.py`: options flow behavior.
- `tests/config_flow/test_config_flow_features.py`: feature-specific options.
- `tests/config_flow/test_config_flow_errors.py`: error and validation paths.
- `tests/config_flow/test_options_flow_integration.py`,
  `tests/config_flow/test_options_flow_routing.py`: dynamic routing and step wiring.
- `tests/config_flow/test_feature_config.py`,
  `tests/config_flow/test_feature_config_climate.py`,
  `tests/config_flow/test_feature_helpers.py`: feature-step routing and schemas.
- `tests/integration/test_exceptions.py`: config flow and setup exceptions.
- `tests/AGENTS.md`: testing guidelines reinforced to avoid HA API drift.

### Coordinator and snapshot behavior

- `tests/integration/test_coordinator.py`: snapshot creation and update failure handling.
- `tests/unit/test_entity_ingestion_contract.py`: entity-ingestion package
  contracts (include/exclude precedence, diagnostic toggle parity, meta-area
  shape parity, API surface, snapshot-builder integration).
- `tests/unit/test_core_entity_loading.py`: loader behavior and registry wiring.
- `tests/unit/test_core_entity_loader.py`: exclusion/filter helpers.
- `tests/unit/test_core_entities.py`: grouped snapshot normalization helpers.
- `tests/unit/test_core_config.py`: core feature config normalization.
- `tests/unit/test_core_presence.py`: core presence sensor selection.

### Sensor and aggregate behavior

- `tests/platforms/test_sensor.py`: aggregate sensor creation and error handling.
- `tests/unit/test_core_aggregates.py`: aggregate logic for multiple sensors and filters.
- `tests/platforms/test_meta_aggregates.py`: meta-area aggregate behavior.
- `tests/integration/test_native_group_helper_lifecycle.py`: managed aggregate,
  threshold, signal-helper, label, area assignment, stale cleanup, and repair
  lifecycle behavior.

### Binary sensor and presence tracking

- `tests/integration/test_area_state.py`: presence and secondary state behavior.
- `tests/integration/test_presence_timeouts.py`: clear/extended timeout behavior.
- `tests/platforms/test_binary_sensor_setup.py`: binary sensor setup coverage.
- `tests/platforms/test_ble_tracker_monitor.py`: BLE tracker monitor behavior.
- `tests/platforms/test_health.py`: health binary sensor aggregation.
- `tests/platforms/test_wasp_in_a_box.py`: wasp-in-a-box behavior and edge cases.

### Lights, light groups, and meta areas

- `tests/platforms/test_light.py`: light group setup and service forwarding.
- `tests/platforms/test_light_complex.py`: multi-group and feature combinations.
- `tests/platforms/test_light_edge_cases.py`: edge cases and restoration behavior.
- `tests/platforms/test_light_meta.py`: meta-area light behavior.
- `tests/integration/test_meta_area_state.py`: meta-area state aggregation.
- `tests/unit/test_light_control_intent_adapter.py`: member-level suppression
  and target-subset behavior.
- `tests/unit/test_light_group_runtime.py`: native helper target dispatch,
  label-backed suppression membership, Adaptive Lighting coordination, and
  manual-control restoration hooks.
- `tests/unit/test_light_group_runtime_adaptive_guards.py`: adaptive switching
  guard derivation and managed ambient-rise fallback behavior.
- `tests/unit/test_light_group_runtime_state_change_observability.py`: debug
  attributes for policy/intent/guard decisions.

### Control intents, managed surfaces, and Adaptive Lighting

- `tests/unit/test_control_intent_engine.py`: pure intent arbitration.
- `tests/unit/test_control_intent_targets.py`: label/helper/entity target
  resolution and fallback records.
- `tests/unit/test_managed_surface_registry.py`: managed helper lookup and
  ownership filtering.
- `tests/unit/test_signal_helper_surfaces.py`: managed signal-helper desired
  surface construction.
- `tests/unit/test_adaptive_lighting_contracts.py`: Adaptive Lighting switch-set
  models, config reconciliation plans, and service payload contracts.
- `tests/unit/test_adaptive_lighting_registry.py`: Adaptive Lighting switch-set
  registry discovery and ambiguity handling.
- `tests/unit/test_adaptive_lighting_executor.py`: service execution adapter
  behavior.
- `tests/unit/test_adaptive_lighting_harness.py`: mocked Adaptive Lighting test
  harness coverage.
- `tests/unit/test_managed_adaptive_lighting_reconciler.py`: managed Adaptive
  Lighting config-entry create/update/delete behavior.

### Media player and audio features

- `tests/platforms/test_media_player.py`: area-aware media player behavior and
  notifications.

### Switches and controls

- `tests/platforms/test_switch.py`: switch behavior for control features.
- `tests/platforms/test_setup_failures.py`: platform setup error handling and cleanup.
- `tests/platforms/test_switch_media_player_control.py`: media player control switch logic.
- `tests/platforms/test_fan_setup.py`, `tests/platforms/test_fan_control_setup.py`,
  `tests/platforms/test_media_player_setup.py`: setup coverage.
- `tests/platforms/test_climate_control.py`: climate control behaviors.
- `tests/platforms/test_climate_control_behaviors.py`: expanded climate state behavior.
- `tests/platforms/test_cover.py`, `tests/platforms/test_fan.py`: platform feature behavior.

### Supporting fixtures and utilities

- `tests/conftest.py`: shared fixtures and integration setup helpers.
- `tests/helpers.py`: integration and registry setup helpers.
- `tests/mocks.py`: updated mocks for stable entity behavior.
- `tests/const.py`: test constants and mock area definitions.
- `tests/integration/test_diagnostics.py`: diagnostics output and redaction.
- `tests/unit/test_icons.py`: icon handling.
- `tests/integration/test_restore.py`: restore behaviors.
- `tests/unit/test_timer.py`: timer behavior.
- `tests/integration/test_area_lifecycle.py`: core integration lifecycle behaviors.
- `tests/snapshots/*.py`: snapshot contract coverage for config flow/coordinator/entities.

## Delta map (tests to changes)

This map ties key deltas to the tests that now cover them.

- Coordinator snapshot gating and availability:
  - `tests/integration/test_coordinator.py`
  - `tests/integration/test_availability.py`
- Core helper extraction:
  - `tests/unit/test_core_config.py`
  - `tests/unit/test_core_presence.py`
  - `tests/unit/test_core_entities.py`
  - `tests/unit/test_core_entity_loading.py`
  - `tests/unit/test_core_entity_loader.py`
  - `tests/unit/test_entity_ingestion_contract.py`
- Platform snapshot usage:
  - `tests/platforms/test_cover.py`
  - `tests/platforms/test_fan.py`
  - `tests/platforms/test_media_player.py`
  - `tests/platforms/test_switch.py`
- Managed native helper/label surfaces:
  - `tests/integration/test_native_group_helper_lifecycle.py`
  - `tests/unit/test_managed_surface_registry.py`
  - `tests/unit/test_signal_helper_surfaces.py`
- Event payload updates and state-change handling:
  - `tests/platforms/test_light_complex.py`
  - `tests/platforms/test_light_edge_cases.py`
  - `tests/platforms/test_switch.py`
- Light intent and Adaptive Lighting coordination:
  - `tests/unit/test_control_intent_engine.py`
  - `tests/unit/test_control_intent_targets.py`
  - `tests/unit/test_light_control_intent_adapter.py`
  - `tests/unit/test_adaptive_lighting_contracts.py`
  - `tests/unit/test_managed_adaptive_lighting_reconciler.py`
- Identity and migration changes:
  - `tests/integration/test_init.py`
  - `tests/integration/test_area_lifecycle.py`

## Guidance for future tests

- Prefer behavior-based assertions over internal helper calls.
- Use coordinator snapshot data rather than raw registry reads where possible.
- Ensure new features include config flow tests and a setup path test.
