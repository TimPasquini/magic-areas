"""Scenario tests for cover automation behavior."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.const import (
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
)
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.area_state import AreaStates
from tests.scenarios.cover_scenario_testkit import (
    CoverLightScenario,
    OneRoomCoverScenario,
    setup_cover_light_scenario,
    setup_one_room_cover_scenario,
)


@pytest.fixture(name="cover_light_scenario")
async def cover_light_scenario_fixture(
    hass: HomeAssistant,
) -> AsyncGenerator[CoverLightScenario]:
    """Set up one room with cover automation and adaptive light control."""
    scenario = await setup_cover_light_scenario(hass)
    yield scenario
    await scenario.shutdown()


@pytest.fixture(name="cover_scenario")
async def cover_scenario_fixture(
    hass: HomeAssistant,
) -> AsyncGenerator[OneRoomCoverScenario]:
    """Set up one room with one blind cover."""
    scenario = await setup_one_room_cover_scenario(hass)
    yield scenario
    await scenario.shutdown()


async def test_cover_privacy_closes_and_daylight_release_reopens(
    cover_scenario: OneRoomCoverScenario,
) -> None:
    """Sleep/privacy should close covers and release back to daylight when cleared."""
    await cover_scenario.enable_cover_control()

    await cover_scenario.emit_area_state_transition(
        new_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
    )
    await cover_scenario.wait_for_cover_state(STATE_CLOSED)

    await cover_scenario.emit_area_state_transition(
        new_states=[],
        lost_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED],
    )
    await cover_scenario.wait_for_cover_state(STATE_OPEN)


async def test_manual_cover_movement_is_not_immediately_reversed(
    cover_scenario: OneRoomCoverScenario,
) -> None:
    """Manual cover movement should hold automation instead of reopening immediately."""
    await cover_scenario.enable_cover_control()

    cover_scenario.blind.close_cover()
    await cover_scenario.wait_for_cover_state(STATE_CLOSED)

    await cover_scenario.emit_area_state_transition(
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
    )

    cover_group_state = cover_scenario.hass.states.get(
        cover_scenario.cover_group_entity_id
    )
    assert cover_group_state is not None
    assert cover_group_state.state == STATE_CLOSED


async def test_dark_context_blocks_daylight_cover_open(
    cover_scenario: OneRoomCoverScenario,
) -> None:
    """Occupied dark/night context should not open covers through Daylight."""
    await cover_scenario.enable_cover_control()

    await cover_scenario.emit_area_state_transition(
        new_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
    )
    await cover_scenario.wait_for_cover_state(STATE_CLOSED)

    await cover_scenario.emit_area_state_transition(
        new_states=[AreaStates.DARK],
        lost_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
    )

    cover_group_state = cover_scenario.hass.states.get(
        cover_scenario.cover_group_entity_id
    )
    assert cover_group_state is not None
    assert cover_group_state.state == STATE_CLOSED


async def test_cover_opening_can_support_adaptive_light_off(
    cover_light_scenario: CoverLightScenario,
) -> None:
    """Opening covers should feed brightness context that light policy can consume."""
    cover_light_scenario.hass.states.async_set("sun.sun", "above_horizon")
    cover_light_scenario.inside_bright.turn_off()
    cover_light_scenario.occupancy.turn_on()
    await cover_light_scenario.hass.async_block_till_done()
    await cover_light_scenario.enable_light_control()
    await cover_light_scenario.enable_cover_control()

    await cover_light_scenario.emit_light_area_state_transition(
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
    )
    await cover_light_scenario.wait_for_overhead_state(STATE_ON)

    await cover_light_scenario.emit_area_state_transition(
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
    )
    await cover_light_scenario.wait_for_cover_state(STATE_OPEN)

    cover_light_scenario.inside_bright.turn_on()
    await cover_light_scenario.hass.async_block_till_done()
    await cover_light_scenario.emit_light_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
    )

    await cover_light_scenario.wait_for_overhead_state(STATE_OFF)


async def test_cover_closing_can_support_occupied_dark_light_on(
    cover_light_scenario: CoverLightScenario,
) -> None:
    """Closing covers should feed dark context that light policy can consume."""
    cover_light_scenario.hass.states.async_set("sun.sun", "above_horizon")
    cover_light_scenario.inside_bright.turn_on()
    cover_light_scenario.occupancy.turn_on()
    await cover_light_scenario.hass.async_block_till_done()
    await cover_light_scenario.enable_light_control()

    await cover_light_scenario.emit_light_area_state_transition(
        new_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
    )
    overhead_state = cover_light_scenario.hass.states.get(
        cover_light_scenario.overhead_light_entity_id
    )
    assert overhead_state is not None
    assert overhead_state.state == STATE_OFF

    cover_light_scenario.blind.close_cover()
    await cover_light_scenario.wait_for_cover_state(STATE_CLOSED)
    cover_light_scenario.inside_bright.turn_off()
    await cover_light_scenario.hass.async_block_till_done()
    await cover_light_scenario.emit_light_area_state_transition(
        new_states=[AreaStates.DARK],
        lost_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
    )

    await cover_light_scenario.wait_for_overhead_state(STATE_ON)
