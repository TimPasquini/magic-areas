"""Unit tests for core config helper normalization/accessors."""

from enum import Enum

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CUSTOM_CONTROL_GROUPS,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_COVER_GROUPS_ACCENT_ACTION,
    CONF_COVER_GROUPS_ACCENT_STATES,
    CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES,
    CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_IGNORE_DIAGNOSTIC_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_RELOAD_ON_REGISTRY_CHANGE,
    CONF_SECONDARY_STATES,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_SLEEP_ENTITY,
    CONF_TYPE,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.core.controls.policies.cover import (
    DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES,
    CoverPresetAction,
    CoverPresetRole,
)
from custom_components.magic_areas.core.config import (
    area_type,
    exclude_entities,
    feature_config_slice,
    has_configured_state,
    ignore_diagnostic_entities,
    include_entities,
    keep_only_entities,
    normalize_custom_control_groups,
    normalize_feature_config,
    presence_device_platforms,
    presence_sensor_device_classes,
    reload_on_registry_change,
    secondary_states_calculation_mode,
    secondary_states_config,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    DEFAULT_NOTIFY_STATES,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_RELOAD_ON_REGISTRY_CHANGE,
    DEFAULT_SECONDARY_STATES_CALCULATION_MODE,
    DEFAULT_WASP_IN_A_BOX_DELAY,
    DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.features.config.readers import (
    area_aware_media_player_config,
    ble_tracker_config,
    climate_control_config,
    cover_groups_config,
    fan_groups_config,
    presence_hold_config,
    wasp_in_a_box_config,
)


class FeatureEnum(Enum):
    """Example enum for feature normalization."""

    TEST = "test_feature"


def test_normalize_feature_config_list() -> None:
    """Normalize list-based feature config."""
    enabled, feature_configs = normalize_feature_config(
        {CONF_ENABLED_FEATURES: [FeatureEnum.TEST, "plain"]}
    )
    assert enabled == {"test_feature", "plain"}
    assert feature_configs == {"test_feature": {}, "plain": {}}


def test_normalize_feature_config_dict() -> None:
    """Normalize dict-based feature config."""
    enabled, feature_configs = normalize_feature_config(
        {
            CONF_ENABLED_FEATURES: {
                FeatureEnum.TEST: {"flag": True},
                "plain": {"value": 10},
            }
        }
    )
    assert enabled == {"test_feature", "plain"}
    assert feature_configs == {"test_feature": {"flag": True}, "plain": {"value": 10}}


def test_has_configured_state() -> None:
    """Report configured secondary states from config."""
    config = {CONF_SECONDARY_STATES: {CONF_SLEEP_ENTITY: "light.bedroom"}}
    assert has_configured_state(config, AreaStates.SLEEP) is True
    assert has_configured_state(config, AreaStates.CLEAR) is False


def test_feature_config_slice_with_enum_key() -> None:
    """Feature config slice resolves enum feature keys."""
    assert feature_config_slice({"test_feature": {"flag": True}}, FeatureEnum.TEST) == {
        "flag": True
    }


def test_feature_config_slice_returns_empty_for_missing_or_invalid() -> None:
    """Feature config slice should be resilient to missing/invalid values."""
    feature_configs = {"plain": {"enabled": True}, "broken": "not-a-dict"}
    assert feature_config_slice(feature_configs, "plain") == {"enabled": True}
    assert feature_config_slice(feature_configs, "missing") == {}
    assert feature_config_slice(feature_configs, "broken") == {}


def test_climate_control_entity_id_normalization() -> None:
    """Climate entity id helper should normalize invalid values to None."""
    assert climate_control_config(
        {CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.office"}
    ).entity_id == "climate.office"
    assert climate_control_config({CONF_CLIMATE_CONTROL_ENTITY_ID: ""}).entity_id is None
    assert climate_control_config({CONF_CLIMATE_CONTROL_ENTITY_ID: 123}).entity_id is None


def test_climate_preset_helpers_return_string_defaults() -> None:
    """Climate preset helpers should always return string values."""
    assert climate_control_config({}).preset_map == {
        str(AreaStates.CLEAR): "",
        str(AreaStates.OCCUPIED): "",
        str(AreaStates.SLEEP): "",
        str(AreaStates.EXTENDED): "",
    }


def test_fan_groups_config_uses_defaults() -> None:
    """Fan groups config should normalize defaults and configured values."""
    assert (
        fan_groups_config({}).tracked_device_class
        == DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS
    )
    assert fan_groups_config(
        {CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS: "humidity"}
    ).tracked_device_class == "humidity"


def test_cover_groups_config_uses_preset_defaults_and_overrides() -> None:
    """Cover config should normalize eligible classes, presets, and manual hold."""
    default_config = cover_groups_config({})
    assert default_config.automation_device_classes == (
        DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES
    )
    assert "awning" not in default_config.automation_device_classes
    assert "garage" not in default_config.automation_device_classes
    assert "gate" not in default_config.automation_device_classes
    assert "door" not in default_config.automation_device_classes
    assert "damper" not in default_config.automation_device_classes
    assert default_config.manual_hold_seconds == 900
    presets = {preset.role: preset for preset in default_config.presets}
    assert presets[CoverPresetRole.DAYLIGHT].action is CoverPresetAction.OPEN
    assert presets[CoverPresetRole.PRIVACY].states == (AreaStates.SLEEP.value,)
    assert presets[CoverPresetRole.ACCENT].action is CoverPresetAction.CLOSE

    custom_config = cover_groups_config(
        {
            CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES: ["blind"],
            CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS: 120,
            CONF_COVER_GROUPS_ACCENT_ACTION: "none",
            CONF_COVER_GROUPS_ACCENT_STATES: [AreaStates.ACCENT.value, "sleep"],
        }
    )
    custom_presets = {preset.role: preset for preset in custom_config.presets}
    assert custom_config.automation_device_classes == ("blind",)
    assert custom_config.manual_hold_seconds == 120
    assert custom_presets[CoverPresetRole.ACCENT].action is CoverPresetAction.NONE
    assert custom_presets[CoverPresetRole.ACCENT].states == ("accented", "sleep")


def test_presence_hold_config_helper() -> None:
    """Presence hold config should normalize timeout value."""
    assert presence_hold_config({}).timeout == int(DEFAULT_PRESENCE_HOLD_TIMEOUT)
    assert presence_hold_config({CONF_PRESENCE_HOLD_TIMEOUT: 5}).timeout == 5


def test_reload_on_registry_change_helper() -> None:
    """Registry reload helper should use configured value or default."""
    assert reload_on_registry_change({}) is bool(DEFAULT_RELOAD_ON_REGISTRY_CHANGE)
    assert reload_on_registry_change({CONF_RELOAD_ON_REGISTRY_CHANGE: False}) is False


def test_ble_tracker_config_helper() -> None:
    """BLE tracker config should return a normalized list."""
    assert ble_tracker_config({}).entities == []
    assert ble_tracker_config({CONF_BLE_TRACKER_ENTITIES: ["sensor.a", "sensor.b"]}).entities == [
        "sensor.a",
        "sensor.b",
    ]
    assert ble_tracker_config({CONF_BLE_TRACKER_ENTITIES: "sensor.a"}).entities == []


def test_notify_helpers() -> None:
    """Notification helpers should return normalized values."""
    assert area_aware_media_player_config({}).notify_devices == []
    assert area_aware_media_player_config(
        {CONF_NOTIFICATION_DEVICES: ["media_player.living_room"]}
    ).notify_devices == ["media_player.living_room"]
    assert area_aware_media_player_config(
        {CONF_NOTIFICATION_DEVICES: "media_player.living_room"}
    ).notify_devices == []
    assert area_aware_media_player_config({}).notify_states == [
        str(state) for state in DEFAULT_NOTIFY_STATES
    ]
    assert area_aware_media_player_config({CONF_NOTIFY_STATES: ["occupied"]}).notify_states == [
        "occupied"
    ]


def test_wasp_helpers() -> None:
    """WASP helpers should parse configured values with defaults."""
    default_config = wasp_in_a_box_config({})
    assert default_config.delay_seconds == int(DEFAULT_WASP_IN_A_BOX_DELAY)
    assert default_config.timeout_minutes == int(DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT)
    assert default_config.device_classes == list(DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES)
    assert wasp_in_a_box_config({CONF_WASP_IN_A_BOX_DELAY: "30"}).delay_seconds == 30
    assert wasp_in_a_box_config({CONF_WASP_IN_A_BOX_WASP_TIMEOUT: "4"}).timeout_minutes == 4
    assert wasp_in_a_box_config(
        {CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES: ["motion"]}
    ).device_classes == ["motion"]


def test_entity_include_exclude_helpers() -> None:
    """Entity include/exclude helpers should normalize list values."""
    assert include_entities({}) == []
    assert exclude_entities({}) == []
    assert include_entities({CONF_INCLUDE_ENTITIES: ["sensor.a"]}) == ["sensor.a"]
    assert exclude_entities({CONF_EXCLUDE_ENTITIES: ["sensor.b"]}) == ["sensor.b"]
    assert include_entities({CONF_INCLUDE_ENTITIES: "sensor.a"}) == []
    assert exclude_entities({CONF_EXCLUDE_ENTITIES: "sensor.b"}) == []


def test_ignore_diagnostic_entities_helper() -> None:
    """Ignore-diagnostic helper should preserve explicit bools and default to None."""
    assert ignore_diagnostic_entities({}) is None
    assert ignore_diagnostic_entities({CONF_IGNORE_DIAGNOSTIC_ENTITIES: True}) is True


def test_presence_platform_and_device_class_helpers() -> None:
    """Presence helpers should normalize platforms and sensor classes."""
    assert presence_device_platforms({}) == [
        str(platform) for platform in DEFAULT_PRESENCE_DEVICE_PLATFORMS
    ]
    assert presence_device_platforms({CONF_PRESENCE_DEVICE_PLATFORMS: ["binary_sensor"]}) == [
        "binary_sensor"
    ]
    assert presence_sensor_device_classes({}) == []
    assert presence_sensor_device_classes({CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"]}) == [
        "motion"
    ]


def test_secondary_state_helpers() -> None:
    """Secondary-state helper accessors should return normalized values."""
    assert secondary_states_config({}) == {}
    assert secondary_states_config({CONF_SECONDARY_STATES: {"sleep_entity": "light.bed"}}) == {
        "sleep_entity": "light.bed"
    }
    assert keep_only_entities({}) == []
    assert keep_only_entities({CONF_KEEP_ONLY_ENTITIES: ["light.a"]}) == ["light.a"]
    assert area_type({}) is None
    assert area_type({CONF_TYPE: "interior"}) == "interior"
    assert secondary_states_calculation_mode({}) == str(
        DEFAULT_SECONDARY_STATES_CALCULATION_MODE
    )
    assert secondary_states_calculation_mode(
        {CONF_SECONDARY_STATES: {CONF_SECONDARY_STATES_CALCULATION_MODE: "last"}}
    ) == "last"


def test_normalize_custom_control_groups() -> None:
    """Custom control-group config should normalize to definitions."""
    groups = normalize_custom_control_groups(
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {
                    "group_id": "control.task",
                    "members": ["light.task", "switch.vent"],
                    "trigger_states": ["occupied"],
                    "policy_id": "custom_task",
                    "metadata": {"label": "Task Group"},
                }
            ]
        }
    )
    assert len(groups) == 1
    assert groups[0].group_id == "control.task"
    assert groups[0].members == ("light.task", "switch.vent")
    assert groups[0].trigger_states == ("occupied",)
    assert groups[0].policy_id == "custom_task"
    assert groups[0].metadata == {"label": "Task Group"}


def test_normalize_custom_control_groups_ignores_invalid() -> None:
    """Invalid custom group payloads should be ignored."""
    groups = normalize_custom_control_groups(
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {"group_id": "missing_members"},
                "invalid",
                {"members": ["light.task"]},
            ]
        }
    )
    assert groups == []


def test_normalize_custom_control_groups_ignores_reserved_policy_ids() -> None:
    """Custom groups should reject reserved built-in policy IDs."""
    groups = normalize_custom_control_groups(
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {
                    "group_id": "control.invalid",
                    "members": ["light.task"],
                    "policy_id": "fan_groups",
                },
                {
                    "group_id": "control.valid",
                    "members": ["light.task"],
                    "policy_id": "custom_control_group",
                },
            ]
        }
    )
    assert len(groups) == 1
    assert groups[0].group_id == "control.valid"


def test_normalize_custom_control_groups_ignores_duplicate_ids() -> None:
    """Custom groups should keep first unique group_id and ignore duplicates."""
    groups = normalize_custom_control_groups(
        {
            CONF_CUSTOM_CONTROL_GROUPS: [
                {
                    "group_id": "control.task",
                    "members": ["light.a"],
                    "policy_id": "custom_control_group",
                },
                {
                    "group_id": "control.task",
                    "members": ["light.b"],
                    "policy_id": "custom_control_group",
                },
            ]
        }
    )
    assert len(groups) == 1
    assert groups[0].members == ("light.a",)
