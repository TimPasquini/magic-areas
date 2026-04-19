"""Contract tests for Wasp-in-a-Box behavior and presence integration."""


from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    ATTR_BOX,
    ATTR_WASP,
)
from custom_components.magic_areas.const import (
    ATTR_ACTIVE_SENSORS,
    ATTR_PRESENCE_SENSORS,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_attribute,
    assert_in_attribute,
    assert_state,
    wait_for_state,
    wait_for_attribute,
)
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.platforms.wasp_in_a_box_testkit",)


async def test_wasp_in_a_box_logic(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
    _setup_integration_wasp_in_a_box: None,
) -> None:
    """Test the Wasp in a box sensor logic."""
    motion_sensor_entity_id = entities_wasp_in_a_box[0].entity_id
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id
    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )
    motion_aggregate_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_motion"
    door_aggregate_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_door"
    )

    motion_sensor_state = hass.states.get(motion_sensor_entity_id)
    assert_state(motion_sensor_state, STATE_OFF)
    door_sensor_state = hass.states.get(door_sensor_entity_id)
    assert_state(door_sensor_state, STATE_OFF)

    motion_aggregate_state = hass.states.get(motion_aggregate_entity_id)
    assert_state(motion_aggregate_state, STATE_OFF)
    door_aggregate_state = hass.states.get(door_aggregate_entity_id)
    assert_state(door_aggregate_state, STATE_OFF)

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_OFF)

    hass.states.async_set(door_sensor_entity_id, STATE_ON)
    await wait_for_attribute(hass, wasp_in_a_box_entity_id, ATTR_BOX, STATE_ON)
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await wait_for_state(hass, wasp_in_a_box_entity_id, STATE_ON)
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_ON)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_ON)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await wait_for_state(hass, wasp_in_a_box_entity_id, STATE_OFF)
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_ON)

    hass.states.async_set(door_sensor_entity_id, STATE_OFF)
    await wait_for_attribute(hass, wasp_in_a_box_entity_id, ATTR_BOX, STATE_OFF)
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await wait_for_state(hass, wasp_in_a_box_entity_id, STATE_ON)
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_ON)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_ON)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await wait_for_attribute(hass, wasp_in_a_box_entity_id, ATTR_WASP, STATE_OFF)
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_ON)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_OFF)

    hass.states.async_set(door_sensor_entity_id, STATE_ON)
    await wait_for_attribute(hass, wasp_in_a_box_entity_id, ATTR_BOX, STATE_ON)
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_WASP, STATE_OFF)
    assert_attribute(wasp_in_a_box_state, ATTR_BOX, STATE_ON)


async def test_wasp_in_a_box_as_presence(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
    _setup_integration_wasp_in_a_box: None,
) -> None:
    """Test the Wasp in a box sensor triggers area presence."""
    motion_sensor_entity_id = entities_wasp_in_a_box[0].entity_id
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id
    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )
    area_state_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    hass.states.async_set(door_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    assert_state(hass.states.get(door_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(motion_sensor_entity_id), STATE_OFF)
    assert_state(hass.states.get(wasp_in_a_box_entity_id), STATE_OFF)

    area_sensor_state = hass.states.get(area_state_entity_id)
    assert_state(area_sensor_state, STATE_OFF)
    assert_in_attribute(
        area_sensor_state, ATTR_PRESENCE_SENSORS, wasp_in_a_box_entity_id
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await wait_for_state(hass, wasp_in_a_box_entity_id, STATE_ON)
    assert_state(hass.states.get(wasp_in_a_box_entity_id), STATE_ON)
    area_sensor_state = hass.states.get(area_state_entity_id)
    assert_state(area_sensor_state, STATE_ON)
    assert_in_attribute(area_sensor_state, ATTR_ACTIVE_SENSORS, wasp_in_a_box_entity_id)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await wait_for_state(hass, wasp_in_a_box_entity_id, STATE_OFF)
    await wait_for_state(hass, area_state_entity_id, STATE_OFF)
    assert_state(hass.states.get(wasp_in_a_box_entity_id), STATE_OFF)
    assert_state(hass.states.get(area_state_entity_id), STATE_OFF)
