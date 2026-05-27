"""Scenario tests for cover automation behavior."""

from collections.abc import AsyncGenerator

import pytest
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_CLOSED, STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
    shutdown_integration,
    wait_for_state,
)
from tests.mocks import MockCover


@pytest.fixture(name="cover_scenario_entry")
def cover_scenario_entry_fixture() -> MockConfigEntry:
    """Return a Magic Areas entry with cover automation enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update({CONF_ENABLED_FEATURES: {MagicAreasFeatures.COVER_GROUPS: {}}})
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="cover_scenario")
async def cover_scenario_fixture(
    hass: HomeAssistant,
    cover_scenario_entry: MockConfigEntry,
) -> AsyncGenerator[MockCover]:
    """Set up one room with one blind cover."""
    blind = MockCover(
        name="scenario_blind",
        unique_id="scenario_blind",
        device_class=CoverDeviceClass.BLIND,
        state=STATE_OPEN,
    )
    await setup_mock_entities(hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: [blind]})
    await init_integration(hass, [cover_scenario_entry])
    yield blind
    await shutdown_integration(hass, [cover_scenario_entry])


def _cover_group_entity_id() -> str:
    """Return the scenario blind helper entity id."""
    return (
        f"{COVER_DOMAIN}.magic_areas_cover_groups_"
        f"{DEFAULT_MOCK_AREA}_cover_group_blind"
    )


def _cover_control_entity_id() -> str:
    """Return the scenario cover control switch entity id."""
    return (
        f"{SWITCH_DOMAIN}.magic_areas_cover_groups_"
        f"{DEFAULT_MOCK_AREA}_cover_control"
    )


async def _enable_cover_control(hass: HomeAssistant) -> None:
    """Enable cover automation for the scenario room."""
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: _cover_control_entity_id()},
        blocking=True,
    )
    await hass.async_block_till_done()


async def _emit_area_state_transition(
    hass: HomeAssistant,
    *,
    new_states: list[AreaStates],
    lost_states: list[AreaStates] | None = None,
    current_states: list[AreaStates] | None = None,
) -> None:
    """Emit a Magic Areas area-state transition."""
    dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        (
            [state.value for state in new_states],
            [state.value for state in (lost_states or [])],
            [state.value for state in (current_states or new_states)],
        ),
    )
    await hass.async_block_till_done()


async def test_cover_privacy_closes_and_daylight_release_reopens(
    hass: HomeAssistant,
    cover_scenario: MockCover,
) -> None:
    """Sleep/privacy should close covers and release back to daylight when cleared."""
    await _enable_cover_control(hass)

    await _emit_area_state_transition(
        hass,
        new_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
    )
    await wait_for_state(hass, _cover_group_entity_id(), STATE_CLOSED)

    await _emit_area_state_transition(
        hass,
        new_states=[],
        lost_states=[AreaStates.SLEEP],
        current_states=[AreaStates.OCCUPIED],
    )
    await wait_for_state(hass, _cover_group_entity_id(), STATE_OPEN)


async def test_manual_cover_movement_is_not_immediately_reversed(
    hass: HomeAssistant,
    cover_scenario: MockCover,
) -> None:
    """Manual cover movement should hold automation instead of reopening immediately."""
    await _enable_cover_control(hass)

    cover_scenario.close_cover()
    await wait_for_state(hass, _cover_group_entity_id(), STATE_CLOSED)

    await _emit_area_state_transition(
        hass,
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
    )
    await hass.async_block_till_done()

    cover_group_state = hass.states.get(_cover_group_entity_id())
    assert cover_group_state is not None
    assert cover_group_state.state == STATE_CLOSED
