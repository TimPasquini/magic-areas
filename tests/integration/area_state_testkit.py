"""Shared fixtures for area-state integration tests."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_ACCENT_ENTITY,
    CONF_CLEAR_TIMEOUT,
    CONF_DARK_ENTITY,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
)
from custom_components.magic_areas.const import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.entities import setup_mock_entities
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor


@pytest.fixture(name="secondary_states_config_entry")
def mock_config_entry_secondary_states() -> MockConfigEntry:
    """Fixture for secondary-states config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_SECONDARY_STATES: {
                CONF_ACCENT_ENTITY: "binary_sensor.accent_sensor",
                CONF_DARK_ENTITY: "binary_sensor.area_light_sensor",
                CONF_SLEEP_ENTITY: "binary_sensor.sleep_sensor",
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="keep_only_sensor_config_entry")
def mock_config_entry_keep_only_sensor() -> MockConfigEntry:
    """Fixture for keep-only-sensors config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update({CONF_KEEP_ONLY_ENTITIES: ["binary_sensor.motion_sensor_1"]})
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="timeout_config_entry")
def mock_config_entry_timeout() -> MockConfigEntry:
    """Fixture for timeout config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_CLEAR_TIMEOUT] = 1
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_secondary_states")
async def setup_integration_secondary_states(
    hass: HomeAssistant,
    secondary_states_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration with secondary-state config."""
    await init_integration_helper(hass, [secondary_states_config_entry])
    yield
    await shutdown_integration(hass, [secondary_states_config_entry])


@pytest.fixture(name="_setup_integration_keep_only_sensor")
async def setup_integration_keep_only_sensor(
    hass: HomeAssistant,
    keep_only_sensor_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration with keep-only-sensor config."""
    await init_integration_helper(hass, [keep_only_sensor_config_entry])
    yield
    await shutdown_integration(hass, [keep_only_sensor_config_entry])


@pytest.fixture(name="secondary_states_sensors")
async def setup_secondary_state_sensors(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create binary sensors for secondary states."""
    sensors = [
        MockBinarySensor(name="sleep_sensor", unique_id="sleep_sensor", device_class=None),
        MockBinarySensor(
            name="area_light_sensor",
            unique_id="area_light_sensor",
            device_class=BinarySensorDeviceClass.LIGHT,
        ),
        MockBinarySensor(name="accent_sensor", unique_id="accent_sensor", device_class=None),
    ]
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: sensors})
    return sensors
