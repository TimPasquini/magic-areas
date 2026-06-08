"""Shared fixtures for switch platform tests."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXTENDED_TIMEOUT,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.entities import setup_mock_entities
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockFan, MockMediaPlayer, MockSensor


@pytest.fixture(name="media_player_group_config_entry")
def mock_config_entry_media_player_group() -> MockConfigEntry:
    """Fixture for media-player group config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {MagicAreasFeatures.MEDIA_PLAYER_GROUPS: {}},
            CONF_SECONDARY_STATES: {CONF_EXTENDED_TIMEOUT: 0},
            CONF_CLEAR_TIMEOUT: 0,
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_media_player_group")
async def setup_integration_media_player_group(
    hass: HomeAssistant,
    media_player_group_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration for media-player group tests."""
    await init_integration_helper(hass, [media_player_group_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    yield
    await shutdown_integration(hass, [media_player_group_config_entry])


@pytest.fixture(name="presence_hold_config_entry")
def mock_config_entry_presence_hold() -> MockConfigEntry:
    """Fixture for presence-hold config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.PRESENCE_HOLD: {CONF_PRESENCE_HOLD_TIMEOUT: 1},
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_presence_hold")
async def setup_integration_presence_hold(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration for presence-hold tests."""
    await init_integration_helper(hass, [presence_hold_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    yield
    await shutdown_integration(hass, [presence_hold_config_entry])


@pytest.fixture(name="entities_media_player")
async def setup_entities_media_player(hass: HomeAssistant) -> list[MockMediaPlayer]:
    """Create mock media player."""
    mock_entities = [MockMediaPlayer(name="media_player_1", unique_id="media_player_1")]
    await setup_mock_entities(
        hass, MEDIA_PLAYER_DOMAIN, {DEFAULT_MOCK_AREA: mock_entities}
    )
    return mock_entities


@pytest.fixture(name="light_control_config_entry")
def mock_config_entry_light_control() -> MockConfigEntry:
    """Fixture for light-control config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.LIGHT_GROUPS: {},
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="fan_control_config_entry")
def mock_config_entry_fan_control() -> MockConfigEntry:
    """Fixture for fan-control config."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 1},
                MagicAreasFeatures.FAN_GROUPS: {
                    CONF_FAN_GROUPS_REQUIRED_STATE: AreaStates.OCCUPIED,
                    CONF_FAN_GROUPS_SETPOINT: 25.0,
                    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="entities_fan_control")
async def setup_entities_fan_control(hass: HomeAssistant) -> tuple[MockFan, MockSensor]:
    """Create mock fan and sensor."""
    mock_fan = MockFan(name="fan_1", unique_id="fan_1")
    mock_sensor = MockSensor(
        name="temp_sensor_1",
        unique_id="temp_sensor_1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_value=20.0,
        native_unit_of_measurement="°C",
    )
    await setup_mock_entities(hass, FAN_DOMAIN, {DEFAULT_MOCK_AREA: [mock_fan]})
    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [mock_sensor]})
    return mock_fan, mock_sensor
