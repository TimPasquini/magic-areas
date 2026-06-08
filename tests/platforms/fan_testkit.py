"""Shared fixtures/helpers for fan platform tests."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
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
from tests.mocks import MockFan, MockSensor

SETPOINT_VALUE = 30.0
SENSOR_INITIAL_VALUE = 25


@pytest.fixture(name="fan_groups_config_entry")
def mock_config_entry_fan_groups() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 1},
                MagicAreasFeatures.FAN_GROUPS: {
                    CONF_FAN_GROUPS_REQUIRED_STATE: AreaStates.OCCUPIED,
                    CONF_FAN_GROUPS_SETPOINT: SETPOINT_VALUE,
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_fan_groups")
async def setup_integration_fan_groups(
    hass: HomeAssistant,
    fan_groups_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration with Fan groups config."""
    await init_integration_helper(hass, [fan_groups_config_entry])
    yield
    await shutdown_integration(hass, [fan_groups_config_entry])


@pytest.fixture(name="entities_fan_multiple")
async def setup_entities_fan_multiple(hass: HomeAssistant) -> list[MockFan]:
    """Create multiple mock fans and set up the system with them."""
    mock_fan_entities = [MockFan(name=f"mock_fan_{i}", unique_id=f"unique_fan_{i}") for i in range(3)]
    await setup_mock_entities(hass, FAN_DOMAIN, {DEFAULT_MOCK_AREA: mock_fan_entities})
    return mock_fan_entities


@pytest.fixture(name="entities_sensor_temperature_one")
async def setup_entities_sensor_temperature_one(hass: HomeAssistant) -> MockSensor:
    """Create one mock temperature sensor and set up the system with it."""
    mock_temperature_sensor = MockSensor(
        name="mock_temperature_sensor",
        unique_id="unique_temperature_sensor",
        native_value=int(SENSOR_INITIAL_VALUE),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        unit_of_measurement=UnitOfTemperature.CELSIUS,
        extra_state_attributes={"unit_of_measurement": UnitOfTemperature.CELSIUS},
    )
    await setup_mock_entities(
        hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [mock_temperature_sensor]}
    )
    return mock_temperature_sensor
