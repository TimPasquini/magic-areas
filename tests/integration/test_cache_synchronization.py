"""Test cache synchronization in presence tracking and area state."""

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import ATTR_STATES
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.const import DOMAIN

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_in_attribute,
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor

_LOGGER = logging.getLogger(__name__)


async def test_attr_is_on_and_states_stay_in_sync(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
) -> None:
    """Test that _attr_is_on and _current_states stay synchronized.

    When area state changes via event, both the entity's is_on property
    (which determines binary_sensor state) and the states attribute
    must be updated together to avoid stale reads.
    """

    config_entry = MockConfigEntry(domain=DOMAIN, data=get_basic_config_entry_data(DEFAULT_MOCK_AREA))
    await init_integration_helper(hass, [config_entry])

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )

    # Initial state: OFF with CLEAR
    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_OFF)
    assert_in_attribute(area_state, ATTR_STATES, AreaStates.CLEAR)

    # Turn on motion: should be ON with OCCUPIED
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_ON)
    assert_in_attribute(area_state, ATTR_STATES, AreaStates.OCCUPIED)

    # Critical: When is_on is ON, states must contain OCCUPIED
    # (not CLEAR or some stale value)
    occupied_state = AreaStates.OCCUPIED.value
    assert area_state is not None
    states_attr = area_state.attributes.get(ATTR_STATES, [])
    assert occupied_state in states_attr, (
        f"Stale states detected! Entity is ON but OCCUPIED not in states. "
        f"is_on={area_state.state}, states={states_attr}"
    )

    # Turn off motion: should be OFF with CLEAR
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_OFF)
    assert_in_attribute(area_state, ATTR_STATES, AreaStates.CLEAR)

    # Critical: When is_on is OFF, states must contain CLEAR
    # (not OCCUPIED or some stale value)
    clear_state = AreaStates.CLEAR.value
    assert area_state is not None
    states_attr = area_state.attributes.get(ATTR_STATES, [])
    assert clear_state in states_attr, (
        f"Stale states detected! Entity is OFF but CLEAR not in states. "
        f"is_on={area_state.state}, states={states_attr}"
    )

    await shutdown_integration(hass, [config_entry])


async def test_event_payload_prevents_stale_reads(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
) -> None:
    """Test that event payloads provide fresh state snapshots.

    When AREA_STATE_CHANGED event is dispatched, handlers receive
    (new_states, lost_states, current_states) snapshot. This prevents
    stale reads where a handler might read area.states from HA state
    machine between event dispatch and entity update.
    """

    config_entry = MockConfigEntry(domain=DOMAIN, data=get_basic_config_entry_data(DEFAULT_MOCK_AREA))
    await init_integration_helper(hass, [config_entry])

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id

    received_states = []

    def capture_event(
        area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Capture the event payload states."""
        new_states, lost_states, current_states = states_tuple
        received_states.append({
            "area_id": area_id,
            "new": new_states,
            "lost": lost_states,
            "current": current_states,
        })

    from homeassistant.helpers.dispatcher import async_dispatcher_connect
    from custom_components.magic_areas.enums import MagicAreasEvents

    remove = async_dispatcher_connect(
        hass, MagicAreasEvents.AREA_STATE_CHANGED, capture_event
    )

    try:
        # Turn motion on
        hass.states.async_set(motion_sensor_entity_id, STATE_ON)
        await hass.async_block_till_done()

        # Event should have OCCUPIED in current_states
        assert len(received_states) > 0
        last_event = received_states[-1]
        assert AreaStates.OCCUPIED.value in last_event["current"], (
            f"Event payload missing OCCUPIED in current_states. "
            f"Handlers might get stale state. Got: {last_event}"
        )

        received_states.clear()

        # Turn motion off
        hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
        await hass.async_block_till_done()

        # Event should have CLEAR in current_states
        assert len(received_states) > 0
        last_event = received_states[-1]
        assert AreaStates.CLEAR.value in last_event["current"], (
            f"Event payload missing CLEAR in current_states. "
            f"Handlers might get stale state. Got: {last_event}"
        )

    finally:
        remove()
        await shutdown_integration(hass, [config_entry])
