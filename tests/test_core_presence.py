"""Tests for core presence helpers."""

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID

from custom_components.magic_areas.config_keys import (
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
)
from custom_components.magic_areas.core.presence import build_presence_sensors
from custom_components.magic_areas.features import (
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_WASP_IN_A_BOX,
)
from custom_components.magic_areas.ha_domains import (
    BINARY_SENSOR_DOMAIN,
    SWITCH_DOMAIN,
)


def test_build_presence_sensors_filters_devices() -> None:
    """Filter presence sensors by domain and device class."""
    entities_by_domain = {
        BINARY_SENSOR_DOMAIN: [
            {
                ATTR_ENTITY_ID: "binary_sensor.motion_one",
                ATTR_DEVICE_CLASS: "motion",
            },
            {
                ATTR_ENTITY_ID: "binary_sensor.door_one",
                ATTR_DEVICE_CLASS: "door",
            },
        ],
        "device_tracker": [
            {ATTR_ENTITY_ID: "device_tracker.phone"},
        ],
    }

    config = {
        CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN, "device_tracker"],
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
    }

    sensors = build_presence_sensors(
        entities_by_domain=entities_by_domain,
        config=config,
        slug="kitchen",
        enabled_features=set(),
    )

    assert sensors == [
        "binary_sensor.motion_one",
        "device_tracker.phone",
    ]


def test_build_presence_sensors_adds_feature_entities() -> None:
    """Append feature-driven presence entities."""
    entities_by_domain = {}
    config = {
        CONF_PRESENCE_DEVICE_PLATFORMS: [BINARY_SENSOR_DOMAIN],
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: ["motion"],
    }

    sensors = build_presence_sensors(
        entities_by_domain=entities_by_domain,
        config=config,
        slug="kitchen",
        enabled_features={
            CONF_FEATURE_PRESENCE_HOLD,
            CONF_FEATURE_BLE_TRACKERS,
            CONF_FEATURE_WASP_IN_A_BOX,
            CONF_FEATURE_AGGREGATION,
        },
    )

    assert sensors == [
        f"{SWITCH_DOMAIN}.magic_areas_presence_hold_kitchen",
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_ble_trackers_kitchen_ble_tracker_monitor",
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_kitchen",
    ]
