"""Aggregate platform edge-case coverage."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.entities import setup_mock_entities
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.platforms.sensor_aggregates_testkit",)


async def test_aggregates_not_enough_entities(
    hass: HomeAssistant,
) -> None:
    """Aggregates should not be created if min entity threshold is unmet."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 2}
            }
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    mock_entity = MockBinarySensor(
        name="motion_sensor_1",
        unique_id="motion_sensor_1",
        device_class=BinarySensorDeviceClass.MOTION,
    )
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [mock_entity]})

    await init_integration_helper(hass, [config_entry])

    aggregate_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_motion"
    )
    assert hass.states.get(aggregate_sensor_id) is None

    await shutdown_integration(hass, [config_entry])


async def test_aggregates_no_entities(
    hass: HomeAssistant,
    aggregates_filtered_config_entry: MockConfigEntry,
) -> None:
    """No aggregate should be created when no binary sensors are present."""
    await init_integration_helper(hass, [aggregates_filtered_config_entry])
    await hass.async_block_till_done()

    aggregate_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_motion"
    )
    assert hass.states.get(aggregate_sensor_id) is None

    await shutdown_integration(hass, [aggregates_filtered_config_entry])


async def test_aggregates_missing_attributes(
    hass: HomeAssistant,
    aggregates_filtered_config_entry: MockConfigEntry,
) -> None:
    """Entities missing device_class should be ignored safely."""
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        "test",
        "no_device_class",
        suggested_object_id="no_device_class",
    )
    registry.async_update_entity(entry.entity_id, area_id=DEFAULT_MOCK_AREA.value)
    hass.states.async_set(entry.entity_id, "off", {})

    await init_integration_helper(hass, [aggregates_filtered_config_entry])
    await hass.async_block_till_done()

    aggregate_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_motion"
    )
    assert hass.states.get(aggregate_sensor_id) is None

    await shutdown_integration(hass, [aggregates_filtered_config_entry])


async def test_aggregates_filtered_device_class(
    hass: HomeAssistant,
    aggregates_filtered_config_entry: MockConfigEntry,
) -> None:
    """Excluded device classes should not produce aggregate or health entities."""
    mock_motion = MockBinarySensor(
        name="motion_sensor",
        unique_id="motion_sensor",
        device_class=BinarySensorDeviceClass.MOTION,
    )

    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [mock_motion]})

    await init_integration_helper(hass, [aggregates_filtered_config_entry])
    await hass.async_block_till_done()

    aggregate_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_motion"
    )
    assert hass.states.get(aggregate_id) is None

    health_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_health_{DEFAULT_MOCK_AREA}_health_problem"
    )
    assert hass.states.get(health_id) is None

    await shutdown_integration(hass, [aggregates_filtered_config_entry])
