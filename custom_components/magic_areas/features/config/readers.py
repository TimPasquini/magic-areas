"""Feature-owned configuration readers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from custom_components.magic_areas.config_keys.area import (
    CLIMATE_CONTROL_PRESET_KEY_BY_STATE,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_COVER_GROUPS_ACCENT_ACTION,
    CONF_COVER_GROUPS_ACCENT_STATES,
    CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES,
    CONF_COVER_GROUPS_DAYLIGHT_ACTION,
    CONF_COVER_GROUPS_DAYLIGHT_STATES,
    CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS,
    CONF_COVER_GROUPS_PRIVACY_ACTION,
    CONF_COVER_GROUPS_PRIVACY_STATES,
    CONF_FAN_GROUPS_CONTROLLERS,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.core.controls.policies.cover import (
    COVER_PRESET_CONFIG_KEYS,
    DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES,
    DEFAULT_COVER_PRESETS,
    CoverGroupsConfig,
    CoverPresetAction,
    CoverPresetConfig,
    CoverPresetRole,
)
from custom_components.magic_areas.feature_reader_common import (
    FeatureConfig,
    FeatureConfigValue,
    FeatureOptions,
    RawFeatureList,
    options_for_feature,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

type FeatureConfigDict = dict[str, FeatureConfigValue]
type FeatureConfigMap = Mapping[str, FeatureConfigValue]

AGGREGATES_OPTION_KEYS: tuple[str, ...] = (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
)
AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS: tuple[str, ...] = (
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
)
BLE_TRACKER_OPTION_KEYS: tuple[str, ...] = (CONF_BLE_TRACKER_ENTITIES,)
CLIMATE_CONTROL_ENTITY_KEY: str = CONF_CLIMATE_CONTROL_ENTITY_ID
CLIMATE_CONTROL_PRESET_OPTION_KEYS: tuple[str, ...] = tuple(
    CLIMATE_CONTROL_PRESET_KEY_BY_STATE.values()
)
FAN_GROUPS_OPTION_KEYS: tuple[str, ...] = (
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_FAN_GROUPS_SETPOINT,
)
COVER_GROUPS_OPTION_KEYS: tuple[str, ...] = (
    CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES,
    CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS,
    CONF_COVER_GROUPS_DAYLIGHT_ACTION,
    CONF_COVER_GROUPS_DAYLIGHT_STATES,
    CONF_COVER_GROUPS_PRIVACY_ACTION,
    CONF_COVER_GROUPS_PRIVACY_STATES,
    CONF_COVER_GROUPS_ACCENT_ACTION,
    CONF_COVER_GROUPS_ACCENT_STATES,
)
COVER_GROUPS_AUTOMATION_DEVICE_CLASSES_KEY: str = (
    CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES
)
COVER_GROUPS_MANUAL_HOLD_SECONDS_KEY: str = CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS
COVER_GROUPS_DAYLIGHT_ACTION_KEY: str = CONF_COVER_GROUPS_DAYLIGHT_ACTION
COVER_GROUPS_DAYLIGHT_STATES_KEY: str = CONF_COVER_GROUPS_DAYLIGHT_STATES
COVER_GROUPS_PRIVACY_ACTION_KEY: str = CONF_COVER_GROUPS_PRIVACY_ACTION
COVER_GROUPS_PRIVACY_STATES_KEY: str = CONF_COVER_GROUPS_PRIVACY_STATES
COVER_GROUPS_ACCENT_ACTION_KEY: str = CONF_COVER_GROUPS_ACCENT_ACTION
COVER_GROUPS_ACCENT_STATES_KEY: str = CONF_COVER_GROUPS_ACCENT_STATES
COVER_GROUPS_DEFAULT_AUTOMATION_DEVICE_CLASSES: tuple[str, ...] = (
    DEFAULT_COVER_AUTOMATION_DEVICE_CLASSES
)
COVER_GROUPS_ACTION_VALUES: tuple[str, ...] = tuple(
    action.value for action in CoverPresetAction
)
FAN_GROUPS_CONTROLLERS_KEY: str = CONF_FAN_GROUPS_CONTROLLERS
HEALTH_OPTION_KEYS: tuple[str, ...] = (CONF_HEALTH_SENSOR_DEVICE_CLASSES,)
PRESENCE_HOLD_OPTION_KEYS: tuple[str, ...] = (CONF_PRESENCE_HOLD_TIMEOUT,)
WASP_IN_A_BOX_OPTION_KEYS: tuple[str, ...] = (
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)

@dataclass(frozen=True, slots=True)
class ClimateControlConfig:
    """Normalized climate-control feature configuration."""

    entity_id: str | None
    preset_map: dict[str, str]


def climate_control_config(feature_configs: FeatureConfig) -> ClimateControlConfig:
    """Return normalized climate-control feature configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.CLIMATE_CONTROL)
    return ClimateControlConfig(
        entity_id=options.optional_entity_id(CONF_CLIMATE_CONTROL_ENTITY_ID),
        preset_map={
            state: options.str_value(key)
            for state, key in CLIMATE_CONTROL_PRESET_KEY_BY_STATE.items()
        },
    )


@dataclass(frozen=True, slots=True)
class FanGroupsConfig:
    """Normalized fan-groups feature configuration."""

    required_state: str
    setpoint: float
    tracked_device_class: FeatureConfigValue


def fan_groups_config(feature_configs: FeatureConfig) -> FanGroupsConfig:
    """Return normalized fan-groups feature configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.FAN_GROUPS)
    return FanGroupsConfig(
        required_state=options.str_value(CONF_FAN_GROUPS_REQUIRED_STATE),
        setpoint=options.float_value(CONF_FAN_GROUPS_SETPOINT),
        tracked_device_class=options.value(CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS),
    )


def cover_groups_config(feature_configs: FeatureConfig) -> CoverGroupsConfig:
    """Return normalized cover-groups automation configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.COVER_GROUPS)
    return CoverGroupsConfig(
        automation_device_classes=tuple(
            options.list_value(CONF_COVER_GROUPS_AUTOMATION_DEVICE_CLASSES)
        ),
        manual_hold_seconds=max(
            0,
            options.int_value(CONF_COVER_GROUPS_MANUAL_HOLD_SECONDS),
        ),
        presets=tuple(_cover_preset_config(options, role) for role in CoverPresetRole),
    )


def _cover_preset_config(
    options: FeatureOptions,
    role: CoverPresetRole,
) -> CoverPresetConfig:
    """Return normalized config for one cover preset role."""
    action_key, states_key = COVER_PRESET_CONFIG_KEYS[role]
    default = DEFAULT_COVER_PRESETS[role]
    raw_action = options.str_value(action_key)
    try:
        action = CoverPresetAction(raw_action)
    except ValueError:
        action = default.action

    states = tuple(options.list_value(states_key, default=list(default.states)))
    return CoverPresetConfig(role=role, action=action, states=states)


@dataclass(frozen=True, slots=True)
class BleTrackerConfig:
    """Normalized BLE tracker feature configuration."""

    entities: list[str]


def ble_tracker_config(feature_configs: FeatureConfig) -> BleTrackerConfig:
    """Return normalized BLE tracker feature configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.BLE_TRACKER)
    return BleTrackerConfig(
        entities=options.list_value(CONF_BLE_TRACKER_ENTITIES)
    )


@dataclass(frozen=True, slots=True)
class AreaAwareMediaPlayerConfig:
    """Normalized area-aware media-player feature configuration."""

    notify_devices: list[str]
    notify_states: list[str]


def area_aware_media_player_config(
    feature_configs: FeatureConfig,
) -> AreaAwareMediaPlayerConfig:
    """Return normalized area-aware media-player configuration."""
    options = options_for_feature(
        feature_configs, MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
    )
    return AreaAwareMediaPlayerConfig(
        notify_devices=options.list_value(CONF_NOTIFICATION_DEVICES),
        notify_states=options.list_value(CONF_NOTIFY_STATES),
    )


@dataclass(frozen=True, slots=True)
class PresenceHoldConfig:
    """Normalized presence-hold feature configuration."""

    timeout: int


def presence_hold_config(feature_configs: FeatureConfig) -> PresenceHoldConfig:
    """Return normalized presence-hold feature configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.PRESENCE_HOLD)
    return PresenceHoldConfig(
        timeout=options.int_value(CONF_PRESENCE_HOLD_TIMEOUT)
    )


@dataclass(frozen=True, slots=True)
class WaspInABoxConfig:
    """Normalized Wasp-in-a-box feature configuration."""

    delay_seconds: int
    timeout_minutes: int
    device_classes: RawFeatureList


def wasp_in_a_box_config(feature_configs: FeatureConfig) -> WaspInABoxConfig:
    """Return normalized Wasp-in-a-box feature configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.WASP_IN_A_BOX)
    return WaspInABoxConfig(
        delay_seconds=options.int_value(CONF_WASP_IN_A_BOX_DELAY),
        timeout_minutes=options.int_value(CONF_WASP_IN_A_BOX_WASP_TIMEOUT),
        device_classes=options.raw_list_value(CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES),
    )
