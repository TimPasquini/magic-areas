"""Feature-owned configuration readers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from custom_components.magic_areas.config_keys.area import (
    CLIMATE_CONTROL_PRESET_KEY_BY_STATE,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_CLIMATE_CONTROL_ENTITY_ID,
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
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.core.config import (
    coerce_float,
    coerce_int,
    string_list,
)
from custom_components.magic_areas.option_defaults import feature_option_default


type FeatureConfigValue = object
type FeatureConfig = Mapping[str, FeatureConfigValue]
type FeatureConfigDict = dict[str, FeatureConfigValue]
type FeatureConfigMap = Mapping[str, FeatureConfigValue]
type RawFeatureList = list[FeatureConfigValue]
TDefault = TypeVar("TDefault", int, float)


def _int_default(feature: MagicAreasFeatures, key: str) -> int:
    """Return integer default value for one feature option."""
    default = feature_option_default(feature, key)
    if isinstance(default, int):
        return default
    msg = f"Expected int default for {feature}:{key}"
    raise TypeError(msg)


def _float_default(feature: MagicAreasFeatures, key: str) -> float:
    """Return float default value for one feature option."""
    default = feature_option_default(feature, key)
    if isinstance(default, (int, float)):
        return float(default)
    msg = f"Expected float default for {feature}:{key}"
    raise TypeError(msg)

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
HEALTH_OPTION_KEYS: tuple[str, ...] = (CONF_HEALTH_SENSOR_DEVICE_CLASSES,)
PRESENCE_HOLD_OPTION_KEYS: tuple[str, ...] = (CONF_PRESENCE_HOLD_TIMEOUT,)
WASP_IN_A_BOX_OPTION_KEYS: tuple[str, ...] = (
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)


@dataclass(frozen=True, slots=True)
class FeatureOptions:
    """Feature-scoped accessor for normalized option values."""

    feature_config: FeatureConfig
    feature: MagicAreasFeatures

    def value(self, key: str) -> FeatureConfigValue:
        """Return one feature option value with configured default fallback."""
        return self.feature_config.get(key, feature_option_default(self.feature, key))

    def list_value(self, key: str, *, default: list[str] | None = None) -> list[str]:
        """Return one feature option as normalized list[str]."""
        return string_list(self.value(key), default=default)

    def int_value(self, key: str) -> int:
        """Return one feature option coerced to int."""
        default = _int_default(self.feature, key)
        return coerce_int(self.value(key), default=default)

    def float_value(self, key: str) -> float:
        """Return one feature option coerced to float."""
        default = _float_default(self.feature, key)
        return coerce_float(self.value(key), default=default)

    def str_value(self, key: str) -> str:
        """Return one feature option coerced to str."""
        return str(self.value(key))

    def optional_entity_id(self, key: str) -> str | None:
        """Return a configured entity id if it is a non-empty string."""
        value = self.feature_config.get(key)
        return value if isinstance(value, str) and value else None

    def raw_list_value(self, key: str) -> RawFeatureList:
        """Return one feature option as list[object] preserving element types."""
        value = self.value(key)
        if isinstance(value, list):
            return list(value)
        return []


def _options_from_slice(
    feature_config: FeatureConfig, feature: MagicAreasFeatures
) -> FeatureOptions:
    """Return feature-scoped options from one feature config slice."""
    return FeatureOptions(feature_config=feature_config, feature=feature)


def options_for_feature(
    feature_configs: FeatureConfig,
    feature: MagicAreasFeatures,
) -> FeatureOptions:
    """Return options for a feature from either full map or one feature slice."""
    feature_key = str(feature.value) if isinstance(feature, Enum) else str(feature)
    feature_config = feature_configs.get(feature_key)
    if isinstance(feature_config, Mapping):
        return _options_from_slice(feature_config, feature)
    return _options_from_slice(feature_configs, feature)


@dataclass(frozen=True, slots=True)
class AggregatesConfig:
    """Normalized aggregates feature configuration."""

    min_entities: int
    sensor_device_classes: RawFeatureList
    binary_sensor_device_classes: RawFeatureList
    illuminance_threshold: float
    illuminance_threshold_hysteresis_percentage: float


def aggregates_config(feature_configs: FeatureConfig) -> AggregatesConfig:
    """Return normalized aggregates feature configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.AGGREGATES)
    return AggregatesConfig(
        min_entities=options.int_value(CONF_AGGREGATES_MIN_ENTITIES),
        sensor_device_classes=options.raw_list_value(CONF_AGGREGATES_SENSOR_DEVICE_CLASSES),
        binary_sensor_device_classes=options.raw_list_value(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES
        ),
        illuminance_threshold=options.float_value(CONF_AGGREGATES_ILLUMINANCE_THRESHOLD),
        illuminance_threshold_hysteresis_percentage=options.float_value(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS
        ),
    )


@dataclass(frozen=True, slots=True)
class HealthConfig:
    """Normalized health feature configuration."""

    sensor_device_classes: FeatureConfigValue


def health_config(feature_configs: FeatureConfig) -> HealthConfig:
    """Return normalized health feature configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.HEALTH)
    return HealthConfig(
        sensor_device_classes=options.value(CONF_HEALTH_SENSOR_DEVICE_CLASSES)
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
