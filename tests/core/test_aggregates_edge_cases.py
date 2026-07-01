"""Test aggregates core logic edge cases."""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.core.aggregates.selection import (
    BinarySensorAggregateSpec,
    SensorAggregateSpec,
    build_binary_sensor_aggregates,
    build_sensor_aggregates,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN


def test_build_aggregates_with_no_entities() -> None:
    """Test aggregates when entities dict is empty."""
    aggregates = build_sensor_aggregates(
        entities_by_domain={},
        feature_configs={},
        enabled_features=set(),
    )
    assert aggregates == []


def test_build_aggregates_with_empty_feature_config() -> None:
    """Test aggregates when feature config is missing defaults."""
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                "entity_id": "sensor.temp_1",
                "device_class": SensorDeviceClass.TEMPERATURE,
                "unit_of_measurement": "°C",
            },
        ]
    }
    aggregates = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs={},
        enabled_features={MagicAreasFeatures.AGGREGATES},
    )
    # Should return empty list when config is missing
    assert aggregates == []


def test_build_aggregates_minimum_entities_enforcement() -> None:
    """Test that minimum entity count is enforced."""
    entities_by_domain = {
        SENSOR_DOMAIN: [
            # Only one sensor but minimum is 2
            {
                "entity_id": "sensor.temp_1",
                "device_class": SensorDeviceClass.TEMPERATURE,
                "unit_of_measurement": "°C",
            },
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 2,  # Requires 2, but only 1 exists
        }
    }
    aggregates = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES},
    )

    assert aggregates == []


def test_build_aggregates_with_custom_device_classes() -> None:
    """Test aggregates with custom device class configuration."""
    entities_by_domain = {
        SENSOR_DOMAIN: [
            {
                "entity_id": "sensor.temp_1",
                "device_class": SensorDeviceClass.TEMPERATURE,
                "unit_of_measurement": "°C",
            },
            {"entity_id": "sensor.humid_1", "device_class": SensorDeviceClass.HUMIDITY},
            {
                "entity_id": "sensor.illumin_1",
                "device_class": SensorDeviceClass.ILLUMINANCE,
            },
        ]
    }
    feature_configs = {
        MagicAreasFeatures.AGGREGATES.value: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: [
                SensorDeviceClass.TEMPERATURE,  # Only temperature
            ],
        }
    }
    aggregates = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=feature_configs,
        enabled_features={MagicAreasFeatures.AGGREGATES},
    )

    assert aggregates == [
        SensorAggregateSpec(
            device_class=SensorDeviceClass.TEMPERATURE,
            entity_ids=["sensor.temp_1"],
            unit_of_measurement="°C",
        )
    ]


def test_build_aggregates_respects_sensor_domain_check() -> None:
    """Test that aggregates requires sensor domain to exist."""
    entities_by_domain = {
        "light": [  # Only light, no sensor domain
            {"entity_id": "light.lamp_1", "device_class": "light"},
        ]
    }
    aggregates = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs={
            MagicAreasFeatures.AGGREGATES.value: {
                CONF_AGGREGATES_MIN_ENTITIES: 1,
            }
        },
        enabled_features={MagicAreasFeatures.AGGREGATES},
    )
    # No sensor domain = no aggregates
    assert aggregates == []


def test_build_binary_aggregates_with_multiple_device_classes() -> None:
    """Test binary sensor aggregates with multiple device classes."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {"entity_id": "binary_sensor.motion_1", "device_class": "motion"},
            {"entity_id": "binary_sensor.motion_2", "device_class": "motion"},
            {"entity_id": "binary_sensor.door_1", "device_class": "door"},
        ]
    }

    aggregates = build_binary_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs={},
        enabled_features={MagicAreasFeatures.AGGREGATES},
    )

    assert aggregates == [
        BinarySensorAggregateSpec(
            device_class="motion",
            entity_ids=["binary_sensor.motion_1", "binary_sensor.motion_2"],
        )
    ]
