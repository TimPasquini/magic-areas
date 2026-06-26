"""Integration tests for area-state transitions."""

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.const import ATTR_PRESENCE_SENSORS, ATTR_STATES
from custom_components.magic_areas.enums import MagicAreasEvents
from tests.helpers.assertions import (
    assert_in_attribute,
    assert_state,
)
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.integration.area_state_testkit",)


async def test_area_primary_state_change(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic: None,
) -> None:
    """Primary motion sensor changes should toggle area occupied/clear."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    assert_state(area_binary_sensor, STATE_OFF)
    assert_in_attribute(
        area_binary_sensor, ATTR_PRESENCE_SENSORS, motion_sensor_entity_id
    )
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.CLEAR)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(motion_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.OCCUPIED
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert_state(hass.states.get(motion_sensor_entity_id), STATE_OFF)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.CLEAR
    )


async def test_area_secondary_state_change(
    hass: HomeAssistant,
    secondary_states_sensors: list[MockBinarySensor],
    _setup_integration_secondary_states: None,
) -> None:
    """Secondary state sensors should update area state attributes."""
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )
    secondary_state_map = {
        secondary_states_sensors[0].entity_id: (AreaStates.SLEEP, None),
        secondary_states_sensors[1].entity_id: (AreaStates.BRIGHT, AreaStates.DARK),
        secondary_states_sensors[2].entity_id: (AreaStates.ACCENT, None),
    }

    for entity_id, state_tuples in secondary_state_map.items():
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)
        assert_state(entity_state, STATE_OFF)
        assert_in_attribute(
            area_binary_sensor, ATTR_STATES, state_tuples[0], negate=True
        )
        if state_tuples[1]:
            assert_in_attribute(area_binary_sensor, ATTR_STATES, state_tuples[1])

        hass.states.async_set(entity_id, STATE_ON)
        await hass.async_block_till_done()
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)
        assert_state(entity_state, STATE_ON)
        assert_in_attribute(area_binary_sensor, ATTR_STATES, state_tuples[0])
        if state_tuples[1]:
            assert_in_attribute(
                area_binary_sensor, ATTR_STATES, state_tuples[1], negate=True
            )

        hass.states.async_set(entity_id, STATE_OFF)
        await hass.async_block_till_done()
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)
        assert_state(entity_state, STATE_OFF)
        assert_in_attribute(
            area_binary_sensor, ATTR_STATES, state_tuples[0], negate=True
        )
        if state_tuples[1]:
            assert_in_attribute(area_binary_sensor, ATTR_STATES, state_tuples[1])


async def test_keep_only_sensors(
    hass: HomeAssistant,
    entities_binary_sensor_motion_multiple: list[MockBinarySensor],
    _setup_integration_keep_only_sensor: None,
) -> None:
    """Keep-only list should gate occupancy source sensors."""
    motion_sensor_entity_id = entities_binary_sensor_motion_multiple[0].entity_id
    flappy_sensor_entity_id = entities_binary_sensor_motion_multiple[1].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    assert_state(area_binary_sensor, STATE_OFF)
    assert_in_attribute(
        area_binary_sensor, ATTR_PRESENCE_SENSORS, motion_sensor_entity_id
    )
    assert_in_attribute(
        area_binary_sensor, ATTR_PRESENCE_SENSORS, flappy_sensor_entity_id
    )
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.CLEAR)

    hass.states.async_set(flappy_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(flappy_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.CLEAR
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(motion_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.OCCUPIED
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert_state(hass.states.get(motion_sensor_entity_id), STATE_OFF)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.OCCUPIED
    )

    hass.states.async_set(flappy_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert_state(hass.states.get(flappy_sensor_entity_id), STATE_OFF)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.CLEAR
    )


async def test_event_filtering(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic: None,
) -> None:
    """Area-state events for other areas should be ignored."""
    async_dispatcher_send(
        hass, MagicAreasEvents.AREA_STATE_CHANGED, "other_area", ([], [], [])
    )
    await hass.async_block_till_done()


async def test_presence_does_not_mutate_area_states(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic: None,
) -> None:
    """Presence entity publishes state via HA attributes, not mutable area fields."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.OCCUPIED
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    assert_in_attribute(
        hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.CLEAR
    )
