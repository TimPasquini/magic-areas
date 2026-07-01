"""Tests for core aggregate selection helpers."""

from homeassistant.components.sensor import SensorDeviceClass
from custom_components.magic_areas.core.aggregates.selection import (
    build_binary_sensor_aggregates,
    build_health_sensor_spec,
    build_sensor_aggregates,
)
from custom_components.magic_areas.core.aggregates.selection import (
    BinarySensorAggregateSpec,
    SensorAggregateSpec,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
)


def test_build_sensor_aggregates_basic() -> None:
    """Select sensor aggregates with most common unit."""
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "sensor.one",
                ATTR_DEVICE_CLASS: "temperature",
                ATTR_UNIT_OF_MEASUREMENT: "C",
            },
            {
                ATTR_ENTITY_ID: "sensor.two",
                ATTR_DEVICE_CLASS: "temperature",
                ATTR_UNIT_OF_MEASUREMENT: "C",
            },
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: ["temperature"],
        }
    }

    specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES.value},
    )

    assert specs == [
        SensorAggregateSpec(
            device_class="temperature",
            entity_ids=["sensor.one", "sensor.two"],
            unit_of_measurement="C",
        )
    ]


def test_build_sensor_aggregates_selects_configured_battery_class() -> None:
    """Select explicitly configured battery sensor aggregates."""
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "sensor.device_battery",
                ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY.value,
                ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
            }
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [SensorDeviceClass.BATTERY.value],
        }
    }

    specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES.value},
    )

    assert specs == [
        SensorAggregateSpec(
            device_class=SensorDeviceClass.BATTERY.value,
            entity_ids=["sensor.device_battery"],
            unit_of_measurement=PERCENTAGE,
        )
    ]


def test_build_sensor_aggregates_selects_voc_parts_by_default() -> None:
    """VOC-parts sensors should be included in the default aggregate set."""
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "sensor.room_voc_parts",
                ATTR_DEVICE_CLASS: (
                    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS.value
                ),
                ATTR_UNIT_OF_MEASUREMENT: "ppm",
            }
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
        }
    }

    specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES.value},
    )

    assert specs == [
        SensorAggregateSpec(
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS.value,
            entity_ids=["sensor.room_voc_parts"],
            unit_of_measurement="ppm",
        )
    ]


def test_build_sensor_aggregates_filters_missing_data() -> None:
    """Skip sensors missing unit or device class or below minimum."""
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {ATTR_ENTITY_ID: "sensor.one", ATTR_DEVICE_CLASS: "temperature"},
            {
                ATTR_ENTITY_ID: "sensor.two",
                ATTR_UNIT_OF_MEASUREMENT: "C",
            },
            {
                ATTR_ENTITY_ID: "sensor.three",
                ATTR_DEVICE_CLASS: "temperature",
                ATTR_UNIT_OF_MEASUREMENT: "C",
            },
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: ["temperature"],
        }
    }

    specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES.value},
    )

    assert specs == []


def test_build_binary_sensor_aggregates_basic() -> None:
    """Select binary sensor aggregates by device class."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "binary_sensor.a",
                ATTR_DEVICE_CLASS: "motion",
            },
            {
                ATTR_ENTITY_ID: "binary_sensor.b",
                ATTR_DEVICE_CLASS: "motion",
            },
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
        }
    }

    specs = build_binary_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES.value},
    )

    assert specs == [
        BinarySensorAggregateSpec(
            device_class="motion",
            entity_ids=["binary_sensor.a", "binary_sensor.b"],
        )
    ]


def test_build_binary_sensor_aggregates_filters_minimum() -> None:
    """Skip binary sensor aggregates when minimum not met."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "binary_sensor.a",
                ATTR_DEVICE_CLASS: "motion",
            }
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
        }
    }

    specs = build_binary_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES.value},
    )

    assert specs == []


def test_build_health_sensor_spec_basic() -> None:
    """Return a problem aggregate for matching device classes."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {ATTR_ENTITY_ID: "binary_sensor.smoke", ATTR_DEVICE_CLASS: "smoke"},
            {ATTR_ENTITY_ID: "binary_sensor.gas", ATTR_DEVICE_CLASS: "gas"},
            {ATTR_ENTITY_ID: "binary_sensor.motion", ATTR_DEVICE_CLASS: "motion"},
        ]
    }
    feature_configs = {
        MagicAreasFeatures.HEALTH.value: {
            CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["smoke", "gas"],
        }
    }

    spec = build_health_sensor_spec(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.HEALTH.value},
    )

    assert spec is not None
    assert spec.device_class == "problem"
    assert set(spec.entity_ids) == {"binary_sensor.smoke", "binary_sensor.gas"}


def test_build_health_sensor_spec_none_when_no_matches() -> None:
    """Return None when no entities match health device classes."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {ATTR_ENTITY_ID: "binary_sensor.motion", ATTR_DEVICE_CLASS: "motion"},
        ]
    }
    feature_configs = {
        MagicAreasFeatures.HEALTH.value: {
            CONF_HEALTH_SENSOR_DEVICE_CLASSES: ["smoke", "gas"],
        }
    }

    spec = build_health_sensor_spec(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.HEALTH.value},
    )

    assert spec is None


def test_build_health_sensor_spec_none_when_feature_disabled() -> None:
    """Return None when health feature is not enabled."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {ATTR_ENTITY_ID: "binary_sensor.smoke", ATTR_DEVICE_CLASS: "smoke"},
        ]
    }

    spec = build_health_sensor_spec(
        entities_by_domain=entities_by_domain,
        feature_configs={},
        enabled_features=set(),  # HEALTH not enabled
    )

    assert spec is None
