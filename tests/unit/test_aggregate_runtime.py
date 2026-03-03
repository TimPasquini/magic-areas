"""Tests for aggregate runtime group-registry integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.aggregate_policy import (
    AggregateDefinition,
    AggregateKind,
)
from custom_components.magic_areas.core.aggregate_runtime import (
    register_aggregate_definitions,
    resolve_aggregate_entity_id,
    resolve_aggregate_entity_ids_by_device_class,
)


def test_register_and_resolve_aggregate_entity_ids_by_domain(
    hass: HomeAssistant,
) -> None:
    """Aggregate runtime should resolve IDs using registered aggregate metadata."""
    area_id = "runtime-area"
    register_aggregate_definitions(
        area_id=area_id,
        definitions=[
            AggregateDefinition(
                domain="sensor",
                device_class="temperature",
                entity_ids=("sensor.temp_1", "sensor.temp_2"),
            ),
            AggregateDefinition(
                domain="binary_sensor",
                device_class="motion",
                entity_ids=("binary_sensor.motion_1", "binary_sensor.motion_2"),
            ),
            AggregateDefinition(
                domain="binary_sensor",
                device_class="problem",
                entity_ids=("binary_sensor.smoke_1",),
                kind=AggregateKind.HEALTH,
            ),
        ],
    )

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"aggregates_{area_id}_aggregate_temperature",
        suggested_object_id="magic_areas_aggregates_runtime_area_aggregate_temperature",
    )
    entity_registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        f"aggregates_{area_id}_aggregate_motion",
        suggested_object_id="magic_areas_aggregates_runtime_area_aggregate_motion",
    )
    entity_registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        f"aggregates_{area_id}_aggregate_problem",
        suggested_object_id="magic_areas_aggregates_runtime_area_aggregate_problem",
    )

    sensor_map = resolve_aggregate_entity_ids_by_device_class(
        hass, area_id=area_id, domain="sensor"
    )
    assert sensor_map == {
        "temperature": "sensor.magic_areas_aggregates_runtime_area_aggregate_temperature"
    }

    binary_map = resolve_aggregate_entity_ids_by_device_class(
        hass, area_id=area_id, domain="binary_sensor"
    )
    assert binary_map == {
        "motion": "binary_sensor.magic_areas_aggregates_runtime_area_aggregate_motion",
        "problem": "binary_sensor.magic_areas_aggregates_runtime_area_aggregate_problem",
    }

    assert (
        resolve_aggregate_entity_id(
            hass,
            area_id=area_id,
            domain="sensor",
            device_class="motion",
        )
        is None
    )


def test_register_aggregate_definitions_replaces_old_area_defaults(
    hass: HomeAssistant,
) -> None:
    """Re-registering an area should replace old aggregate defaults."""
    area_id = "replace-area"
    register_aggregate_definitions(
        area_id=area_id,
        definitions=[
            AggregateDefinition(
                domain="sensor",
                device_class="temperature",
                entity_ids=("sensor.temp_1", "sensor.temp_2"),
            )
        ],
    )

    register_aggregate_definitions(
        area_id=area_id,
        definitions=[
            AggregateDefinition(
                domain="sensor",
                device_class="humidity",
                entity_ids=("sensor.humidity_1", "sensor.humidity_2"),
            )
        ],
    )

    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"aggregates_{area_id}_aggregate_temperature",
        suggested_object_id="magic_areas_aggregates_replace_area_aggregate_temperature",
    )
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"aggregates_{area_id}_aggregate_humidity",
        suggested_object_id="magic_areas_aggregates_replace_area_aggregate_humidity",
    )

    sensor_map = resolve_aggregate_entity_ids_by_device_class(
        hass, area_id=area_id, domain="sensor"
    )
    assert "temperature" not in sensor_map
    assert sensor_map["humidity"] == "sensor.magic_areas_aggregates_replace_area_aggregate_humidity"
