"""Contract tests for health and BLE tracker feature modules."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID

from custom_components.magic_areas.config_keys.area import CONF_BLE_TRACKER_ENTITIES
from custom_components.magic_areas.enums import MagicAreasFeatures

from .feature_module_contracts_testkit import get_module, make_area_config, make_coordinator, make_snapshot


def test_health_module_builds_health_sensor() -> None:
    """Health module should declare a native health helper surface."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.HEALTH},
        feature_configs={},
        entities={
            BINARY_SENSOR_DOMAIN: [
                {
                    ATTR_ENTITY_ID: "binary_sensor.smoke_1",
                    ATTR_DEVICE_CLASS: BinarySensorDeviceClass.SMOKE.value,
                }
            ]
        },
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("health")
    entities = module.build_entities(area_config, coordinator, snapshot)
    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    assert entities == []
    assert len(surfaces) == 1
    assert surfaces[0].unique_id == (
        "magic_areas:entry-1:area-1:health:config_entry_helper:health_problem"
    )
    assert surfaces[0].domain == "group"
    assert surfaces[0].options["group_type"] == BINARY_SENSOR_DOMAIN
    assert surfaces[0].options["entities"] == ["binary_sensor.smoke_1"]
    assert surfaces[0].device_class == BinarySensorDeviceClass.PROBLEM


def test_ble_tracker_module_builds_monitor_sensor() -> None:
    """BLE tracker module should build the tracker monitor sensor."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.BLE_TRACKER},
        feature_configs={
            MagicAreasFeatures.BLE_TRACKER: {
                CONF_BLE_TRACKER_ENTITIES: ["sensor.ble_1"],
            }
        },
        entities={},
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("ble_trackers")
    entities = module.build_entities(area_config, coordinator, snapshot)

    assert [entity.entity_id for entity in entities] == [
        "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor"
    ]
