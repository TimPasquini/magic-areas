"""Tests for core aggregate selection helpers."""

from custom_components.magic_areas.core.aggregates import (
    BinarySensorAggregateSpec,
    SensorAggregateSpec,
    build_binary_sensor_aggregates,
    build_sensor_aggregates,
)
from custom_components.magic_areas.features import CONF_FEATURE_AGGREGATION
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
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
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: ["temperature"],
        }
    }

    specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={CONF_FEATURE_AGGREGATION},
    )

    assert specs == [
        SensorAggregateSpec(
            device_class="temperature",
            entity_ids=["sensor.one", "sensor.two"],
            unit_of_measurement="C",
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
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: ["temperature"],
        }
    }

    specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={CONF_FEATURE_AGGREGATION},
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
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
        }
    }

    specs = build_binary_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={CONF_FEATURE_AGGREGATION},
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
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: ["motion"],
        }
    }

    specs = build_binary_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={CONF_FEATURE_AGGREGATION},
    )

    assert specs == []
