"""Core-owned feature configuration readers for policy/runtime code."""

from __future__ import annotations

from dataclasses import dataclass

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.feature_reader_common import (
    FeatureConfig,
    FeatureConfigValue,
    RawFeatureList,
    options_for_feature,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


@dataclass(frozen=True, slots=True)
class AggregatesConfig:
    """Normalized aggregates feature configuration."""

    min_entities: int
    sensor_device_classes: RawFeatureList
    binary_sensor_device_classes: RawFeatureList
    illuminance_threshold: float
    illuminance_threshold_hysteresis_percentage: float


def aggregates_config(feature_configs: FeatureConfig) -> AggregatesConfig:
    """Return normalized aggregates configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.AGGREGATES)
    return AggregatesConfig(
        min_entities=options.int_value(CONF_AGGREGATES_MIN_ENTITIES),
        sensor_device_classes=options.raw_list_value(
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES
        ),
        binary_sensor_device_classes=options.raw_list_value(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES
        ),
        illuminance_threshold=options.float_value(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD
        ),
        illuminance_threshold_hysteresis_percentage=options.float_value(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS
        ),
    )


@dataclass(frozen=True, slots=True)
class HealthConfig:
    """Normalized health feature configuration."""

    sensor_device_classes: FeatureConfigValue


def health_config(feature_configs: FeatureConfig) -> HealthConfig:
    """Return normalized health configuration."""
    options = options_for_feature(feature_configs, MagicAreasFeatures.HEALTH)
    return HealthConfig(
        sensor_device_classes=options.value(CONF_HEALTH_SENSOR_DEVICE_CLASSES)
    )
