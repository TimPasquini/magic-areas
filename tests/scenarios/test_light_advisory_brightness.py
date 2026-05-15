"""Scenario tests for advisory light-group brightness behavior."""

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from tests.helpers import wait_for_state
from tests.scenarios.light_scenario_testkit import (
    OneRoomLightScenario,
    setup_one_room_advisory_light_scenario,
)


async def _ready_advisory_room(hass: HomeAssistant, inside_bright: str) -> OneRoomLightScenario:
    """Set up an advisory room with light control enabled and a brightness state."""
    scenario = await setup_one_room_advisory_light_scenario(hass)
    await scenario.enable_light_control()
    await scenario.set_inside_bright(inside_bright)
    return scenario


async def test_advisory_not_bright_allows_occupied_light_on(
    hass: HomeAssistant,
) -> None:
    """A valid not-bright room should turn configured lights on when occupied."""
    scenario = await _ready_advisory_room(hass, STATE_OFF)

    await scenario.set_occupied(True)

    await wait_for_state(hass, scenario.target_light_entity_id, STATE_ON)
    scenario.snapshot("assert overhead turned on")
    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace


async def test_advisory_bright_inhibits_occupied_light_on(
    hass: HomeAssistant,
) -> None:
    """A valid bright room should not turn configured lights on on occupancy."""
    scenario = await _ready_advisory_room(hass, STATE_ON)

    await scenario.set_occupied(True)
    await hass.async_block_till_done()

    scenario.snapshot("assert overhead stayed off")
    assert scenario.trace[-1].target_light == STATE_OFF, scenario.trace


async def test_advisory_unknown_brightness_falls_back_to_room_cues(
    hass: HomeAssistant,
) -> None:
    """Unknown startup brightness should not inhibit normal room-state cues."""
    scenario = await _ready_advisory_room(hass, STATE_UNKNOWN)

    await scenario.set_occupied(True)
    await hass.async_block_till_done()

    await wait_for_state(hass, scenario.target_light_entity_id, STATE_ON)
    scenario.snapshot("assert unknown brightness followed occupancy")
    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace


async def test_advisory_unavailable_brightness_falls_back_to_room_cues(
    hass: HomeAssistant,
) -> None:
    """Unavailable startup brightness should not inhibit normal room-state cues."""
    scenario = await _ready_advisory_room(hass, STATE_UNAVAILABLE)

    await scenario.set_occupied(True)
    await hass.async_block_till_done()

    await wait_for_state(hass, scenario.target_light_entity_id, STATE_ON)
    scenario.snapshot("assert unavailable brightness followed occupancy")
    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace


async def test_advisory_recovered_not_bright_resumes_normal_control(
    hass: HomeAssistant,
) -> None:
    """Invalid brightness should already follow cues, and recovery should keep working."""
    scenario = await _ready_advisory_room(hass, STATE_UNKNOWN)

    await scenario.set_occupied(True)
    await hass.async_block_till_done()
    await wait_for_state(hass, scenario.target_light_entity_id, STATE_ON)
    scenario.snapshot("assert startup state followed occupancy")
    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace

    await scenario.set_occupied(False)
    await wait_for_state(hass, scenario.target_light_entity_id, STATE_OFF)
    await scenario.set_inside_bright(STATE_OFF)
    await scenario.set_occupied(True)

    await wait_for_state(hass, scenario.target_light_entity_id, STATE_ON)
    scenario.snapshot("assert recovered brightness allowed on")
    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace
