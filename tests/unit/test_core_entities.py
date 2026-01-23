"""Tests for core entity helpers."""

from homeassistant.const import ATTR_ENTITY_ID

from custom_components.magic_areas.core.entities import (
    EntitySnapshot,
    build_entity_dict,
    group_entities,
)


def test_build_entity_dict_filters_entity_id() -> None:
    """Ensure entity_id is not duplicated in attributes."""
    attributes = {
        ATTR_ENTITY_ID: "sensor.should_not_copy",
        "unit_of_measurement": "lx",
        "device_class": "illuminance",
    }

    entity_dict = build_entity_dict("sensor.illuminance", attributes)

    assert entity_dict[ATTR_ENTITY_ID] == "sensor.illuminance"
    assert entity_dict["unit_of_measurement"] == "lx"
    assert entity_dict["device_class"] == "illuminance"
    assert "sensor.should_not_copy" not in entity_dict.values()


def test_group_entities_by_domain() -> None:
    """Group entity snapshots by domain."""
    entities = [
        EntitySnapshot(
            entity_id="sensor.temp", domain="sensor", attributes={"state": 1}
        ),
        EntitySnapshot(
            entity_id="sensor.humidity",
            domain="sensor",
            attributes={"state": 2},
        ),
        EntitySnapshot(
            entity_id="binary_sensor.motion",
            domain="binary_sensor",
            attributes={"device_class": "motion"},
        ),
    ]

    grouped = group_entities(entities)

    assert set(grouped.keys()) == {"sensor", "binary_sensor"}
    assert [item[ATTR_ENTITY_ID] for item in grouped["sensor"]] == [
        "sensor.temp",
        "sensor.humidity",
    ]
    assert grouped["binary_sensor"][0][ATTR_ENTITY_ID] == "binary_sensor.motion"
