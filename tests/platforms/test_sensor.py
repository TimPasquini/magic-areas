"""Test for sensor platform."""

import pytest
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import shutdown_integration
from tests.helpers.lifecycle import init_integration as init_integration_helper


@pytest.fixture(name="sensor_config_entry")
def mock_config_entry_sensor() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 1}
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


async def test_sensor_setup_missing_attributes(
    hass: HomeAssistant, sensor_config_entry: MockConfigEntry
) -> None:
    """Test sensor setup with entities missing attributes."""

    # Create sensors with missing attributes
    registry = er.async_get(hass)

    # 1. Missing device_class
    entry_no_dc = registry.async_get_or_create(
        SENSOR_DOMAIN, "test", "no_dc", suggested_object_id="no_dc"
    )
    registry.async_update_entity(entry_no_dc.entity_id, area_id=DEFAULT_MOCK_AREA.value)
    hass.states.async_set(
        entry_no_dc.entity_id,
        "10",
        {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS},
    )

    # 2. Missing unit_of_measurement
    entry_no_uom = registry.async_get_or_create(
        SENSOR_DOMAIN, "test", "no_uom", suggested_object_id="no_uom"
    )
    registry.async_update_entity(
        entry_no_uom.entity_id, area_id=DEFAULT_MOCK_AREA.value
    )
    hass.states.async_set(
        entry_no_uom.entity_id, "10", {ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE}
    )

    # 3. Valid sensor
    entry_valid = registry.async_get_or_create(
        SENSOR_DOMAIN, "test", "valid", suggested_object_id="valid"
    )
    registry.async_update_entity(entry_valid.entity_id, area_id=DEFAULT_MOCK_AREA.value)
    hass.states.async_set(
        entry_valid.entity_id,
        "10",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
        },
    )

    await init_integration_helper(hass, [sensor_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    # Verify aggregate created for valid sensor
    aggregate_id = f"{SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_temperature"
    assert hass.states.get(aggregate_id) is not None

    # Verify no other aggregates (implicit by ID check above, but logic ensures skipped entities don't crash)

    await shutdown_integration(hass, [sensor_config_entry])
