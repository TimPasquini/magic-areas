"""Switch platform tests for media-player and light control switches."""

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
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

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import MagicAreasEvents
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.assertions import assert_state
from tests.helpers.waits import wait_for_state
from tests.helpers import (
    async_mock_service,
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockMediaPlayer
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.platforms.switch_testkit",)


async def test_media_player_control_switch(
    hass: HomeAssistant,
    entities_media_player: list[MockMediaPlayer],
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_media_player_group: None,
) -> None:
    """Test media player control switch."""
    switch_id = f"{SWITCH_DOMAIN}.magic_areas_media_player_groups_{DEFAULT_MOCK_AREA}_media_player_control"
    mp_entity = entities_media_player[0]
    assert_state(hass.states.get(switch_id), STATE_OFF)

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(switch_id), STATE_ON)

    calls = async_mock_service(
        hass=hass,
        domain=MEDIA_PLAYER_DOMAIN,
        service=SERVICE_TURN_OFF,
    )

    mp_entity.play_media("music", "test")
    await hass.async_block_till_done()
    assert_state(hass.states.get(mp_entity.entity_id), STATE_PLAYING)

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        ([AreaStates.CLEAR], [], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data[ATTR_ENTITY_ID] == (
        f"{MEDIA_PLAYER_DOMAIN}.magic_areas_media_player_groups_{DEFAULT_MOCK_AREA}_media_player_group"
    )


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
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_ON)

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_OFF)

    await shutdown_integration(hass, [light_control_config_entry])
