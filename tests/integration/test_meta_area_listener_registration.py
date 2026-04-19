"""Test meta-area listener registration and updates."""

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


from tests.const import MockAreaIds
from tests.helpers import (
    assert_state,
)
from tests.mocks import MockBinarySensor

_LOGGER = logging.getLogger(__name__)


async def test_meta_area_listeners_track_child_presence_sensors(
    hass: HomeAssistant,
    entities_binary_sensor_motion_all_areas_with_meta: dict[MockAreaIds, list[MockBinarySensor]],
    init_integration_all_areas: list[MockConfigEntry],
) -> None:
    """Test that meta areas properly track child presence sensors.

    When a meta area is created, it should listen to its child areas'
    presence sensors. When those child sensors change state, the meta
    area should update its state accordingly.

    This test verifies that the listeners are properly registered and
    functional for state changes.
    """

    # Get the global meta area
    global_area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_global_area_state"
    )

    # Initially all areas are clear, so global should be OFF
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_OFF)

    # Turn on kitchen motion
    kitchen_motion_id = entities_binary_sensor_motion_all_areas_with_meta[
        MockAreaIds.KITCHEN
    ][0].entity_id
    hass.states.async_set(kitchen_motion_id, STATE_ON)
    await hass.async_block_till_done()

    # Kitchen area should be occupied
    kitchen_area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )
    kitchen_state = hass.states.get(kitchen_area_sensor_entity_id)
    assert_state(kitchen_state, STATE_ON)

    # Global meta area should now be occupied (listening to kitchen)
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_ON)

    # Turn off kitchen motion
    hass.states.async_set(kitchen_motion_id, STATE_OFF)
    await hass.async_block_till_done()

    # Kitchen area should now be clear
    kitchen_state = hass.states.get(kitchen_area_sensor_entity_id)
    assert_state(kitchen_state, STATE_OFF)

    # Global meta area should now be clear (listener tracking worked)
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_OFF)


async def test_meta_area_handles_multiple_child_state_changes(
    hass: HomeAssistant,
    entities_binary_sensor_motion_all_areas_with_meta: dict[MockAreaIds, list[MockBinarySensor]],
    init_integration_all_areas: list[MockConfigEntry],
) -> None:
    """Test that meta areas correctly aggregate multiple child areas.

    When multiple child areas have presence sensors firing in sequence,
    the meta area should properly track which children are occupied and
    only clear when all children are clear.
    """

    global_area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_global_area_state"
    )
    interior_area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_interior_area_state"
    )
    exterior_area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_exterior_area_state"
    )

    # Get sensor IDs
    kitchen_motion_id = entities_binary_sensor_motion_all_areas_with_meta[
        MockAreaIds.KITCHEN
    ][0].entity_id
    backyard_motion_id = entities_binary_sensor_motion_all_areas_with_meta[
        MockAreaIds.BACKYARD
    ][0].entity_id

    # Initially all clear
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_OFF)

    # Turn on kitchen (interior)
    hass.states.async_set(kitchen_motion_id, STATE_ON)
    await hass.async_block_till_done()

    interior_state = hass.states.get(interior_area_sensor_entity_id)
    assert_state(interior_state, STATE_ON)
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_ON)

    # Turn on backyard (exterior)
    hass.states.async_set(backyard_motion_id, STATE_ON)
    await hass.async_block_till_done()

    exterior_state = hass.states.get(exterior_area_sensor_entity_id)
    assert_state(exterior_state, STATE_ON)
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_ON)

    # Turn off kitchen
    hass.states.async_set(kitchen_motion_id, STATE_OFF)
    await hass.async_block_till_done()

    interior_state = hass.states.get(interior_area_sensor_entity_id)
    assert_state(interior_state, STATE_OFF)
    # Global should still be ON because backyard is still occupied
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_ON)

    # Turn off backyard
    hass.states.async_set(backyard_motion_id, STATE_OFF)
    await hass.async_block_till_done()

    exterior_state = hass.states.get(exterior_area_sensor_entity_id)
    assert_state(exterior_state, STATE_OFF)
    # Now global should finally clear
    global_state = hass.states.get(global_area_sensor_entity_id)
    assert_state(global_state, STATE_OFF)
