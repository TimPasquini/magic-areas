# Phase 7 CRG Dead-Code Audit

## Scope

This document records the complete Phase 7 review of Code Review Graph (CRG)
dead-code candidates. CRG output is a candidate generator, not deletion proof.
Every deletion also requires direct-reference, serialized/string-reference,
registry, callback, fixture, protocol, and Home Assistant convention review.

Audit date: 2026-06-11

CRG version: 2.3.2

Initial graph result: 298 candidates (259 functions and 39 classes).

Post-removal rebuilt result: 287 candidates.

The count fell by 11 graph nodes: eight removed symbols plus the three methods
owned by the removed `VirtualClock` class.

## Reproduction

Build the graph from the repository root:

```bash
uv run code-review-graph build --repo .
```

Query `.code-review-graph/graph.db` with
`code_review_graph.refactor.find_dead_code(GraphStore(...))`. For every
candidate, search its exact identifier and string form with `rg`, inspect its
AST decorators and parent class, and inspect registration, callback return, and
framework entry paths before assigning a disposition.

## Removed Symbols

The audit proved these symbols had no active contract:

| Symbol | Location | Reason |
| --- | --- | --- |
| `VirtualClock` | `tests/helpers_timing.py` | No import, fixture, caller, callback, or framework role; its three methods were reachable only through the unused class. |
| `ConfigBase._errors_from_validation` | `custom_components/magic_areas/config_flows/base.py` | Unused wrapper around the live module-level `errors_from_validation`. |
| `LightGroupRuntimeController.state_change_primary` | `custom_components/magic_areas/light_groups/controller.py` | Unused compatibility method duplicating the live area-state runtime path. |
| `LightGroupRuntimeController.state_change_secondary` | `custom_components/magic_areas/light_groups/controller.py` | Unused compatibility method duplicating the live area-state runtime path. |
| `_managed_ambient_rise_met` | `custom_components/magic_areas/light_groups/runtime.py` | Unused wrapper; `_ambient_rise_met` directly consumes `_managed_ambient_rise_state`. |
| `OneRoomLightScenario.light_group_state` | `tests/scenarios/light_scenario_testkit.py` | No scenario or test caller. |
| `group_ids_for_area` | `tests/unit/feature_module_contracts_testkit.py` | No caller, fixture registration, or dynamic role. |
| `MockToggleEntity.last_call` | `tests/mocks.py` | No caller and not part of a Home Assistant entity interface. |

## Retention Rules

The remaining 287 candidates are retained under these reviewed mechanisms:

- Home Assistant entry points and entity interfaces: `async_step_*`, setup and
  unload hooks, entity properties, service methods, and lifecycle callbacks are
  invoked by Home Assistant rather than ordinary Python callers.
- Registry and protocol dispatch: feature modules, feature methods, control
  contracts, runtime host protocol members, and migration handlers are loaded
  through records, registries, protocols, or version tables.
- Callback contracts: listener handlers, timer callbacks, cancellation
  callbacks, schema validators, and builder callbacks are passed as values.
- Pytest contracts: fixtures in `conftest.py` and imported testkits are
  discovered by pytest; mock entity methods implement Home Assistant test
  surfaces.
- Data and property contracts: enums, dataclass fields, view properties, and
  serialized identifiers are commonly consumed through member access that CRG
  does not consistently attribute to the defining class node.
- Simulator contracts: room properties, room factories, scenario callbacks,
  and timing properties are consumed by generated room/scenario definitions or
  callback registration.

Compatibility exports in `core.controls` and `features.control_builders` remain
intentional facades. Their underlying builder definitions are live through
those aliases and feature-module callers; removal belongs to an incremental
facade migration, not dead-code deletion.

## Coverage Review

No retained mechanism lacked behavioral or contract coverage requiring a new
test in this phase. Representative coverage includes:

- Config-flow dynamic dispatch: `tests/config_flow/`.
- Feature catalog and registry dispatch:
  `tests/unit/test_feature_catalog_contract.py` and feature-module contract
  tests.
- Light-group callbacks and runtime protocol behavior:
  `tests/unit/test_light_group_runtime.py` and
  `tests/unit/test_light_group_runtime_state_change_observability.py`.
- Migration record dispatch: `tests/integration/test_config_migrations.py`.
- Home Assistant entity and mock interfaces: platform, integration, and
  scenario suites using the entity classes.
- Pytest fixture discovery: the full suite, which exercises imported fixtures
  from `conftest.py` and the testkits.
- Simulator timing and scenario contracts: simulator unit tests and the
  previously validated real-time control-matrix runs recorded in the roadmap.

## Validation Evidence

The first removal batch (`VirtualClock`) passed `./scripts/validate.sh` with
Ruff clean, mypy clean across 376 source files, 26 snapshots passing, and 1441
pytest tests passing in 40.31 seconds.

The completed removal batch passed focused behavioral validation with 261 tests
in 7.92 seconds, followed by `./scripts/validate.sh`: Ruff clean, mypy clean
across 376 source files, 26 snapshots passing, and 1441 pytest tests passing in
36.02 seconds.

The graph was then rebuilt from 388 files (3609 nodes and 28226 edges). The
refreshed query returned 287 candidates and none of the eight removed symbols.

Final phase-exit `./scripts/validate.sh` passed with Ruff clean, mypy clean
across 376 source files, 26 snapshots passing, and 1441 pytest tests passing in
42.37 seconds.

## Complete Retained Inventory

The table below accounts for every candidate in the post-removal graph. Symbols
are grouped by defining file; the disposition column identifies the reviewed
mechanism that makes the group live. Mixed files call out their specific
contract rather than relying on the path alone.

| Count | File | Disposition | Candidate symbols |
| ---: | --- | --- | --- |
| 2 | `custom_components/magic_areas/__init__.py` | Directly reviewed property, callback, schema, or registry contract | `async_update_options`, `async_unload_entry` |
| 2 | `custom_components/magic_areas/area_state.py` | Enum, view, or serialized data contract | `AreaType`, `MetaAreaType` |
| 1 | `custom_components/magic_areas/binary_sensor/__init__.py` | Home Assistant entity property or callback contract | `_build_platform_base_entities` |
| 1 | `custom_components/magic_areas/binary_sensor/ble_tracker.py` | Home Assistant entity property or callback contract | `_sensor_state_change` |
| 4 | `custom_components/magic_areas/binary_sensor/presence.py` | Home Assistant entity property or callback contract | `_secondary_state_change`, `_sensor_state_change`, `_update_state`, `_get_secondary_states` |
| 4 | `custom_components/magic_areas/binary_sensor/wasp_in_a_box.py` | Home Assistant entity property or callback contract | `forget_wasp`, `_async_wasp_sensor_state_change`, `_async_box_sensor_state_change`, `_on_box_delay_complete` |
| 2 | `custom_components/magic_areas/components.py` | Enum, view, or serialized data contract | `MetaAreaIcons`, `FeatureIcons` |
| 3 | `custom_components/magic_areas/config_flow.py` | Home Assistant config-flow dispatch | `ConfigFlow`, `async_step_user`, `async_get_options_flow` |
| 10 | `custom_components/magic_areas/config_flows/options_flow.py` | Home Assistant config-flow dispatch | `_dynamic_step`, `async_step_area_config`, `async_step_area_config_settings`, `async_step_presence_tracking`, `async_step_presence_tracking_settings`, `async_step_secondary_states`, `async_step_secondary_states_settings`, `async_step_custom_control_groups`, `async_step_custom_control_groups_settings`, `async_step_finish` |
| 1 | `custom_components/magic_areas/coordinator/__init__.py` | Coordinator property, registry filter, or lifecycle callback | `lifecycle` |
| 13 | `custom_components/magic_areas/coordinator/pipeline/lifecycle.py` | Coordinator property, registry filter, or lifecycle callback | `MetaReloadAction`, `MetaSnapshotRetryAction`, `ReloadScheduleAction`, `ReadinessRequestAction`, `ReadinessGateAction`, `reloading`, `pending_reload_handle`, `meta_data_retry_attempts`, `_clear_reloading_guard`, `_entity_registry_filter`, `_device_registry_filter`, `_auto_reload_enabled`, `_handle_registry` |
| 1 | `custom_components/magic_areas/core/aggregates/policy.py` | Directly reviewed property, callback, schema, or registry contract | `AggregateKind` |
| 8 | `custom_components/magic_areas/core/control_intents/adaptive_lighting.py` | Control/intent data contract or facade export | `ManagedAdaptiveLightingReconcileAction`, `AdaptiveLightingCoordinationReason`, `entity_ids`, `data`, `switch_refs`, `name`, `area_id`, `role` |
| 2 | `custom_components/magic_areas/core/control_intents/engine.py` | Control/intent data contract or facade export | `IntentReason`, `is_noop` |
| 5 | `custom_components/magic_areas/core/control_intents/models.py` | Control/intent data contract or facade export | `ControlTargetKind`, `ControlTargetPrecision`, `target_entity_ids`, `is_executable`, `uses_broad_label_target` |
| 2 | `custom_components/magic_areas/core/controls/builders.py` | Control/intent data contract or facade export | `build_primary_group_entities`, `build_partitioned_group_entities` |
| 2 | `custom_components/magic_areas/core/controls/control_group.py` | Control/intent data contract or facade export | `ControlActionType`, `ControlRuntimeEffectType` |
| 2 | `custom_components/magic_areas/core/controls/policies/fan.py` | Control/intent data contract or facade export | `FanControllerRole`, `off_threshold` |
| 1 | `custom_components/magic_areas/core/meta_reload.py` | Directly reviewed property, callback, schema, or registry contract | `MetaAreaAutoReloadSettings` |
| 5 | `custom_components/magic_areas/core/occupancy/tracker.py` | Directly reviewed property, callback, schema, or registry contract | `states`, `is_occupied`, `last_changed`, `active_sensors`, `last_active_sensors` |
| 1 | `custom_components/magic_areas/core/presence_tracker.py` | Directly reviewed property, callback, schema, or registry contract | `tracker` |
| 7 | `custom_components/magic_areas/core/runtime_model/groups.py` | Enum, view, or serialized data contract | `ControlGroupPolicyId`, `GroupMetadataKey`, `group_id`, `policy_id`, `members`, `metadata`, `definition` |
| 2 | `custom_components/magic_areas/core/wasp_state_machine.py` | Directly reviewed property, callback, schema, or registry contract | `is_present`, `wasp_active` |
| 5 | `custom_components/magic_areas/entity.py` | Home Assistant entity property or callback contract | `should_poll`, `available`, `device_info`, `feature_info`, `member_entity_ids` |
| 3 | `custom_components/magic_areas/enums.py` | Enum, view, or serialized data contract | `LightGroupCategory`, `MagicConfigEntryVersion`, `SelectorTranslationKeys` |
| 6 | `custom_components/magic_areas/features/base.py` | Feature registry/protocol dispatch | `default_feature_options`, `schema_from_default_options`, `option_steps`, `validate_config`, `option_steps`, `validate_config` |
| 1 | `custom_components/magic_areas/features/catalog.py` | Control/intent data contract or facade export | `FeatureRegistration` |
| 3 | `custom_components/magic_areas/features/modules/aggregates.py` | Feature registry/protocol dispatch | `AggregatesFeatureModule`, `build_entities`, `desired_managed_surfaces` |
| 2 | `custom_components/magic_areas/features/modules/area_aware_media_player.py` | Feature registry/protocol dispatch | `AreaAwareMediaPlayerFeatureModule`, `build_entities` |
| 2 | `custom_components/magic_areas/features/modules/ble_trackers.py` | Feature registry/protocol dispatch | `BLETrackersFeatureModule`, `build_entities` |
| 2 | `custom_components/magic_areas/features/modules/climate_control.py` | Feature registry/protocol dispatch | `ClimateControlFeatureModule`, `build_entities` |
| 3 | `custom_components/magic_areas/features/modules/cover_groups.py` | Feature registry/protocol dispatch | `CoverGroupsFeatureModule`, `build_entities`, `desired_managed_surfaces` |
| 3 | `custom_components/magic_areas/features/modules/fan_groups.py` | Feature registry/protocol dispatch | `FanGroupsFeatureModule`, `build_entities`, `desired_managed_surfaces` |
| 3 | `custom_components/magic_areas/features/modules/health.py` | Feature registry/protocol dispatch | `HealthFeatureModule`, `build_entities`, `desired_managed_surfaces` |
| 4 | `custom_components/magic_areas/features/modules/light_groups.py` | Feature registry/protocol dispatch | `build_entities`, `desired_managed_surfaces`, `desired_managed_adaptive_lighting_configs`, `build_runtime_controllers` |
| 3 | `custom_components/magic_areas/features/modules/media_player_groups.py` | Feature registry/protocol dispatch | `MediaPlayerGroupsFeatureModule`, `build_entities`, `desired_managed_surfaces` |
| 2 | `custom_components/magic_areas/features/modules/presence_hold.py` | Feature registry/protocol dispatch | `PresenceHoldFeatureModule`, `build_entities` |
| 2 | `custom_components/magic_areas/features/modules/wasp_in_a_box.py` | Feature registry/protocol dispatch | `WaspInABoxFeatureModule`, `build_entities` |
| 1 | `custom_components/magic_areas/helpers/__init__.py` | Directly reviewed property, callback, schema, or registry contract | `_scheduled` |
| 1 | `custom_components/magic_areas/light_groups/config.py` | Directly reviewed property, callback, schema, or registry contract | `build_light_group_feature_schema` |
| 10 | `custom_components/magic_areas/light_groups/controller.py` | Runtime host property/callback contract | `name`, `unique_id`, `entity_id`, `is_on`, `controlling`, `_echo_state`, `async_get_last_state`, `track_group_listener`, `async_write_ha_state`, `area_state_changed` |
| 1 | `custom_components/magic_areas/light_groups/entities.py` | Home Assistant entity property or callback contract | `async_turn_on` |
| 1 | `custom_components/magic_areas/light_groups/policy.py` | Directly reviewed property, callback, schema, or registry contract | `ActOnMode` |
| 7 | `custom_components/magic_areas/light_groups/runtime.py` | Runtime host protocol or scheduled callback | `_echo_state`, `controlling`, `is_on`, `entity_id`, `unique_id`, `name`, `recheck` |
| 3 | `custom_components/magic_areas/media_player/area_aware_media_player.py` | Home Assistant entity property or callback contract | `state`, `supported_features`, `async_play_media` |
| 2 | `custom_components/magic_areas/migrations.py` | Migration record dispatch | `_migrate_1_0_to_2_0`, `_migrate_2_2_to_2_3` |
| 1 | `custom_components/magic_areas/schemas/control_groups.py` | Directly reviewed property, callback, schema, or registry contract | `_validate_custom_control_groups_payload` |
| 2 | `custom_components/magic_areas/switch/base.py` | Home Assistant entity property or callback contract | `_clear_timers`, `_timeout_turn_off` |
| 1 | `custom_components/magic_areas/switch/cover_control.py` | Home Assistant entity property or callback contract | `_manual_hold_expiry_check` |
| 1 | `custom_components/magic_areas/switch/fan_control.py` | Home Assistant entity property or callback contract | `_hold_expiry_check` |
| 13 | `scripts/ha_dev_bootstrap.py` | Simulator room, timing, or callback contract | `occupancy_entity`, `sleep_entity`, `accent_entity`, `light_entity`, `illuminance_entity`, `overhead_light`, `second_light`, `resolved_dark_entity`, `_room_dev_area`, `_room_magic_area`, `_fan_room_magic_area`, `_cover_room_magic_area`, `_initial_service_calls` |
| 1 | `scripts/ha_dev_simulation/scenarios/lights.py` | Simulator room, timing, or callback contract | `clear_room` |
| 2 | `scripts/ha_dev_simulation/timing.py` | Simulator room, timing, or callback contract | `seeded_minute_seconds`, `runtime_poll_seconds` |
| 13 | `tests/conftest.py` | Pytest fixture discovery | `auto_enable_custom_integrations`, `mock_http_start_server`, `patch_reload_settings`, `patch_async_call_later`, `mock_config_entry_all_areas_with_meta_config_entry`, `setup_entities_binary_sensor_motion_one`, `setup_entities_binary_sensor_motion_multiple`, `setup_entities_binary_sensor_motion_all_areas_with_meta`, `setup_entities_light_one`, `init_integration_fixture`, `setup_integration`, `init_integration_all_areas`, `init_integration` |
| 1 | `tests/const.py` | Test data/property contract | `MockFloorIds` |
| 3 | `tests/helpers/platforms.py` | Test callback or helper contract | `_async_setup_platform`, `_async_setup_entry`, `mock_import_platform` |
| 1 | `tests/helpers/services.py` | Test callback or helper contract | `mock_service_log` |
| 1 | `tests/helpers/waits.py` | Test callback or helper contract | `_on_state_change` |
| 2 | `tests/helpers_timing.py` | Test callback or helper contract | `immediate_call`, `cancel` |
| 6 | `tests/integration/area_state_testkit.py` | Imported fixture or test-harness contract | `mock_config_entry_secondary_states`, `mock_config_entry_keep_only_sensor`, `mock_config_entry_timeout`, `setup_integration_secondary_states`, `setup_integration_keep_only_sensor`, `setup_secondary_state_sensors` |
| 42 | `tests/mocks.py` | Home Assistant mock entity interface | `available`, `device_info`, `entity_category`, `extra_state_attributes`, `has_entity_name`, `entity_registry_enabled_default`, `entity_registry_visible_default`, `icon`, `name`, `should_poll`, `translation_key`, `unique_id`, `name`, `is_on`, `is_on`, `device_class`, `async_added_to_hass`, `is_on`, `async_added_to_hass`, `device_class`, `last_reset`, `suggested_display_precision`, `native_unit_of_measurement`, `native_value`, `options`, `state_class`, `suggested_unit_of_measurement`, `async_added_to_hass`, `device_class`, `supported_features`, `is_closed`, `is_opening`, `is_closing`, `stop_cover`, `async_added_to_hass`, `state`, `is_on`, `supported_features`, `media_stop`, `async_added_to_hass`, `set_preset_mode`, `async_added_to_hass` |
| 3 | `tests/platforms/climate_control_testkit.py` | Imported fixture or test-harness contract | `mock_config_entry_climate_control`, `setup_integration_climate_control`, `setup_entities_climate_one` |
| 4 | `tests/platforms/fan_testkit.py` | Imported fixture or test-harness contract | `mock_config_entry_fan_groups`, `setup_integration_fan_groups`, `setup_entities_fan_multiple`, `setup_entities_sensor_temperature_one` |
| 4 | `tests/platforms/light_edge_cases_testkit.py` | Imported fixture or test-harness contract | `mock_config_entry_light_edge_cases`, `mock_config_entry_light_edge_cases_limited`, `setup_entities_light_edge_cases`, `setup_entities_binary_sensor_edge_cases` |
| 6 | `tests/platforms/sensor_aggregates_testkit.py` | Imported fixture or test-harness contract | `mock_config_entry_aggregates`, `mock_config_entry_aggregates_filtered`, `setup_integration_aggregates`, `setup_entities_binary_sensor_connectivity_multiple`, `setup_entities_sensor_temperature_multiple`, `setup_entities_sensor_current_multiple` |
| 8 | `tests/platforms/switch_testkit.py` | Imported fixture or test-harness contract | `mock_config_entry_media_player_group`, `setup_integration_media_player_group`, `mock_config_entry_presence_hold`, `setup_integration_presence_hold`, `setup_entities_media_player`, `mock_config_entry_light_control`, `mock_config_entry_fan_control`, `setup_entities_fan_control` |
| 3 | `tests/platforms/wasp_in_a_box_testkit.py` | Imported fixture or test-harness contract | `mock_config_entry_wasp_in_a_box`, `setup_integration_wasp_in_a_box`, `setup_entities_wasp_in_a_box` |
| 4 | `tests/scenarios/cover_scenario_testkit.py` | Imported fixture or test-harness contract | `cover_group_entity_id`, `cover_control_entity_id`, `light_control_entity_id`, `overhead_light_entity_id` |
| 7 | `tests/scenarios/light_scenario_testkit.py` | Imported fixture or test-harness contract | `occupancy_entity_id`, `inside_bright_entity_id`, `target_light_entity_id`, `secondary_light_entity_id`, `area_state_entity_id`, `light_group_entity_id`, `light_control_entity_id` |
| 2 | `tests/snapshots/conftest.py` | Pytest fixture discovery | `snapshot_integration_fixture`, `snapshot_integration_all_areas_fixture` |
| 5 | `tests/unit/adaptive_lighting_testkit.py` | Imported fixture or test-harness contract | `switch_entity_ids`, `switch_set`, `_capture`, `_record_manual_control_event`, `_set_switch_states` |
