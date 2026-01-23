"""Tests for the Switch entities."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import (
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXTENDED_TIMEOUT,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.enums import AreaStates, MagicAreasEvents
from custom_components.magic_areas.features import (
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_MEDIA_PLAYER_GROUPS,
    CONF_FEATURE_PRESENCE_HOLD,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_state,
    async_mock_service,
    get_basic_config_entry_data,
    setup_mock_entities,
    shutdown_integration,
    wait_for_state,
)
from tests.helpers import (
    init_integration as init_integration_helper,
)
from tests.mocks import MockFan, MockMediaPlayer, MockSensor

_LOGGER = logging.getLogger(__name__)

# Fixtures


@pytest.fixture(name="media_player_group_config_entry")
def mock_config_entry_media_player_group() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {CONF_FEATURE_MEDIA_PLAYER_GROUPS: {}},
            CONF_SECONDARY_STATES: {
                CONF_EXTENDED_TIMEOUT: 0,
            },
            CONF_CLEAR_TIMEOUT: 0,
        }
    )

    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_media_player_group")
async def setup_integration_media_player_group(
    hass: HomeAssistant,
    media_player_group_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration."""
    await init_integration_helper(hass, [media_player_group_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    yield
    await shutdown_integration(hass, [media_player_group_config_entry])


@pytest.fixture(name="presence_hold_config_entry")
def mock_config_entry_presence_hold() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_PRESENCE_HOLD: {CONF_PRESENCE_HOLD_TIMEOUT: 1},  # 1 minute
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_presence_hold")
async def setup_integration_presence_hold(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration."""
    await init_integration_helper(hass, [presence_hold_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    yield
    await shutdown_integration(hass, [presence_hold_config_entry])


@pytest.fixture(name="entities_media_player")
async def setup_entities_media_player(
    hass: HomeAssistant,
) -> list[MockMediaPlayer]:
    """Create mock media player."""
    mock_entities = [MockMediaPlayer(name="media_player_1", unique_id="media_player_1")]
    await setup_mock_entities(
        hass, MEDIA_PLAYER_DOMAIN, {DEFAULT_MOCK_AREA: mock_entities}
    )
    return mock_entities


@pytest.fixture(name="light_control_config_entry")
def mock_config_entry_light_control() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_LIGHT_GROUPS: {},
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="fan_control_config_entry")
def mock_config_entry_fan_control() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_FAN_GROUPS: {
                    CONF_FAN_GROUPS_REQUIRED_STATE: AreaStates.OCCUPIED,
                    CONF_FAN_GROUPS_SETPOINT: 25.0,
                    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
                }
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="entities_fan_control")
async def setup_entities_fan_control(
    hass: HomeAssistant,
) -> tuple[MockFan, MockSensor]:
    """Create mock fan and sensor."""
    mock_fan = MockFan(name="fan_1", unique_id="fan_1")
    mock_sensor = MockSensor(
        name="temp_sensor_1",
        unique_id="temp_sensor_1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_value=20.0,
    )

    await setup_mock_entities(hass, FAN_DOMAIN, {DEFAULT_MOCK_AREA: [mock_fan]})
    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [mock_sensor]})

    return mock_fan, mock_sensor


# Tests


async def test_media_player_control_switch(
    hass: HomeAssistant,
    entities_media_player: list[MockMediaPlayer],
    entities_binary_sensor_motion_one,
    _setup_integration_media_player_group,
) -> None:
    """Test media player control switch."""

    switch_id = f"{SWITCH_DOMAIN}.magic_areas_media_player_groups_{DEFAULT_MOCK_AREA}_media_player_control"
    mp_entity = entities_media_player[0]

    switch_state = hass.states.get(switch_id)
    assert_state(switch_state, STATE_OFF)

    # Turn switch ON
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    switch_state = hass.states.get(switch_id)
    assert_state(switch_state, STATE_ON)

    calls = async_mock_service(
        hass=hass,
        domain=MEDIA_PLAYER_DOMAIN,
        service=SERVICE_TURN_OFF,
    )

    # Set media player to PLAYING
    mp_entity.play_media("music", "test")
    await hass.async_block_till_done()
    assert_state(hass.states.get(mp_entity.entity_id), STATE_PLAYING)

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,  # area_id
        ([AreaStates.CLEAR], []),  # (new_states, lost_states)
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data[ATTR_ENTITY_ID] == (
        f"{MEDIA_PLAYER_DOMAIN}.magic_areas_media_player_groups_{DEFAULT_MOCK_AREA}_media_player_group"
    )


async def test_switch_snapshot_fields_presence_hold(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> None:
    """Test switch snapshot fields used by the platform."""
    await init_integration_helper(hass, [presence_hold_config_entry])

    data = presence_hold_config_entry.runtime_data.coordinator.data
    assert data is not None
    assert CONF_FEATURE_PRESENCE_HOLD in data.enabled_features

    feature_config = data.feature_configs.get(CONF_FEATURE_PRESENCE_HOLD)
    assert feature_config is not None
    assert feature_config[CONF_PRESENCE_HOLD_TIMEOUT] == 1

    await shutdown_integration(hass, [presence_hold_config_entry])


async def test_presence_hold_switch_timeout(
    hass: HomeAssistant,
    _setup_integration_presence_hold,
    patch_async_call_later,
) -> None:
    """Test presence hold switch timeout."""
    switch_id = f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"

    # Turn ON
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()

    # Should be OFF because of timeout (patched to immediate)
    await wait_for_state(hass, switch_id, STATE_OFF)


async def test_presence_hold_switch_unload_with_timer(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> None:
    """Test presence hold switch unload with active timer."""
    await init_integration_helper(hass, [presence_hold_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    switch_id = f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"

    # Turn ON to start timer
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()

    # Unload integration while timer is active
    await shutdown_integration(hass, [presence_hold_config_entry])


async def test_presence_hold_switch_unload_no_timer(
    hass: HomeAssistant,
    presence_hold_config_entry: MockConfigEntry,
) -> None:
    """Test presence hold switch unload without active timer."""
    await init_integration_helper(hass, [presence_hold_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    # Unload integration without turning on (no timer)
    await shutdown_integration(hass, [presence_hold_config_entry])


async def test_light_control_switch(
    hass: HomeAssistant,
    light_control_config_entry: MockConfigEntry,
) -> None:
    """Test light control switch (SwitchBase coverage)."""
    await init_integration_helper(hass, [light_control_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )

    # Turn ON
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_ON)

    # Turn OFF
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_OFF)

    await shutdown_integration(hass, [light_control_config_entry])


async def test_fan_control_switch(
    hass: HomeAssistant,
    fan_control_config_entry: MockConfigEntry,
    entities_fan_control: tuple[MockFan, MockSensor],
) -> None:
    """Test fan control switch logic."""
    mock_fan, mock_sensor = entities_fan_control

    # Setup aggregate sensor that the switch tracks
    aggregate_sensor_id = f"{SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_{SensorDeviceClass.TEMPERATURE}"

    # Pre-create the aggregate sensor state so the switch finds it on init
    hass.states.async_set(aggregate_sensor_id, "20.0")

    await init_integration_helper(hass, [fan_control_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_control"
    )
    fan_group_id = f"{FAN_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_group"

    # Get area object to manipulate state
    entry = hass.config_entries.async_get_entry(fan_control_config_entry.entry_id)
    area = entry.runtime_data.area

    # Turn ON the control switch
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_ON)

    # 1. Area Clear (default) -> Fan should be OFF
    # Trigger logic by updating area state (simulated via dispatcher or just state update if logic listens to it)
    # The switch listens to AREA_STATE_CHANGED.

    area.states = [AreaStates.CLEAR]
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        ([AreaStates.CLEAR], []),
    )
    await hass.async_block_till_done()

    # Verify Fan Group is OFF (mock service call or state check if group updates)
    # Since we don't have a real fan group logic running fully without the group entity being fully functional,
    # we check if the service was called. But MockFan updates state on service call.
    await wait_for_state(hass, mock_fan.entity_id, STATE_OFF)

    # 2. Area Occupied (Required State) + Temp < Setpoint (20 < 25) -> Fan OFF
    area.states = [AreaStates.OCCUPIED]
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        ([AreaStates.OCCUPIED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, mock_fan.entity_id, STATE_OFF)

    # 3. Temp increases > Setpoint (30 > 25) -> Fan ON
    # Update aggregate sensor
    hass.states.async_set(aggregate_sensor_id, "30.0")
    await hass.async_block_till_done()
    await wait_for_state(hass, mock_fan.entity_id, STATE_ON)

    await shutdown_integration(hass, [fan_control_config_entry])
