"""Control-state edge-case tests for light groups."""

from unittest.mock import MagicMock

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.const import ATTR_STATES
from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.light_groups import turn_off
from custom_components.magic_areas.light_groups import turn_on
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockLight

pytest_plugins = ("tests.platforms.light_edge_cases_testkit",)


async def test_manual_control_detection(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Manual group state change clears controlling flag."""
    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()
    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(light_group_id)
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )

    event = MagicMock()
    event.context.origin_event.event_type = "state_changed"
    event.context.origin_event.data = {
        "old_state": State(light_group_id, STATE_OFF),
        "new_state": State(light_group_id, STATE_ON),
    }
    target_group.group_state_changed(event)
    await hass.async_block_till_done()

    group_state = hass.states.get(light_group_id)
    assert group_state is not None
    assert group_state.attributes.get("controlling") is False
    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])


async def test_native_helper_manual_control_releases_hidden_policy_entity(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Manual native-helper control should still release the hidden policy entity."""
    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()
    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(light_group_id)
    assert target_group is not None

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )
    target_group._last_known_area_states = [AreaStates.OCCUPIED.value]

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: target_group._control_target_entity_id()},
        blocking=True,
    )
    await hass.async_block_till_done()

    group_state = hass.states.get(light_group_id)
    assert group_state is not None
    assert group_state.attributes.get("controlling") is False
    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])


async def test_owned_echo_completes_without_releasing_control(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Owned state-change echo clears awaiting flag and keeps control."""
    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()
    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(light_group_id)
    assert target_group is not None

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )
    target_group._last_known_area_states = [AreaStates.OCCUPIED.value]

    assert turn_on(target_group) is True
    assert target_group._echo_state.awaiting_echo is True
    assert target_group._echo_state.owner_id == target_group.unique_id

    event = MagicMock()
    event.context.origin_event.event_type = "state_changed"
    event.context.origin_event.data = {
        "old_state": State(light_group_id, STATE_OFF),
        "new_state": State(light_group_id, STATE_ON),
    }
    target_group.group_state_changed(event)

    assert target_group._echo_state.controlling is True
    assert target_group._echo_state.awaiting_echo is False
    assert target_group._echo_state.owner_id == target_group.unique_id
    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])


async def test_external_change_releases_control_owner(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Manual changes while not awaiting echo release ownership."""
    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()
    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(light_group_id)
    assert target_group is not None

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )
    target_group._last_known_area_states = [AreaStates.OCCUPIED.value]
    target_group._set_echo_state(
        CommandEchoState(
            owner_id=target_group.unique_id,
            controlling=True,
            awaiting_echo=False,
        )
    )

    event = MagicMock()
    event.context.origin_event.event_type = "state_changed"
    event.context.origin_event.data = {
        "old_state": State(light_group_id, STATE_OFF),
        "new_state": State(light_group_id, STATE_ON),
    }
    target_group.group_state_changed(event)

    assert target_group._echo_state.controlling is False
    assert target_group._echo_state.awaiting_echo is False
    assert target_group._echo_state.owner_id is None
    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])


async def test_owned_turn_off_echo_completes_without_releasing_control(
    hass: HomeAssistant,
    light_edge_cases_config_entry_limited: MockConfigEntry,
    entities_light_edge_cases: list[MockLight],
) -> None:
    """Owned off-echo should clear awaiting flag and keep control."""
    await init_integration_helper(hass, [light_edge_cases_config_entry_limited])
    await hass.async_start()
    await hass.async_block_till_done()
    light_group_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_overhead_lights"
    )
    target_group = hass.data["entity_components"][LIGHT_DOMAIN].get_entity(light_group_id)
    assert target_group is not None

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(
        area_sensor_entity_id, STATE_ON, {ATTR_STATES: [AreaStates.OCCUPIED]}
    )
    target_group._last_known_area_states = [AreaStates.OCCUPIED.value]
    hass.states.async_set(target_group._control_target_entity_id(), STATE_ON)
    await hass.async_block_till_done()

    assert turn_off(target_group) is True
    assert target_group._echo_state.awaiting_echo is True
    assert target_group._echo_state.owner_id == target_group.unique_id

    event = MagicMock()
    event.context.origin_event.event_type = "state_changed"
    event.context.origin_event.data = {
        "old_state": State(light_group_id, STATE_ON),
        "new_state": State(light_group_id, STATE_OFF),
    }
    target_group.group_state_changed(event)

    assert target_group._echo_state.controlling is True
    assert target_group._echo_state.awaiting_echo is False
    assert target_group._echo_state.owner_id == target_group.unique_id
    await shutdown_integration(hass, [light_edge_cases_config_entry_limited])
