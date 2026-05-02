"""Fan-group policy/behavior tests."""


from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_DEVICE_CLASS,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import assert_state, wait_for_state
from tests.mocks import MockBinarySensor, MockFan, MockSensor

pytest_plugins = ("tests.platforms.fan_testkit",)

SETPOINT_VALUE = 30.0
SENSOR_INITIAL_VALUE = 25


def _assert_state_with_context(
    hass: HomeAssistant,
    entity_id: str,
    expected_value: str,
    *,
    context: str,
    motion_sensor_entity_id: str,
    area_sensor_entity_id: str,
    fan_control_entity_id: str,
    temperature_sensor_entity_id: str,
    tracked_entity_id: str,
) -> None:
    """Assert entity state with context dump for debugging failures."""
    entity_state = hass.states.get(entity_id)
    if not entity_state:
        raise AssertionError(f"{context}: missing state for {entity_id}")

    if entity_state.state != expected_value:
        motion_state = hass.states.get(motion_sensor_entity_id)
        area_state = hass.states.get(area_sensor_entity_id)
        switch_state = hass.states.get(fan_control_entity_id)
        temperature_state = hass.states.get(temperature_sensor_entity_id)
        tracked_state = hass.states.get(tracked_entity_id)
        debug_details = (
            f"{context}: {entity_id} expected={expected_value} actual={entity_state.state}; "
            f"motion_state={getattr(motion_state, 'state', None)}; "
            f"area_state={getattr(area_state, 'state', None)}; "
            f"switch_state={getattr(switch_state, 'state', None)}; "
            f"temperature_state={getattr(temperature_state, 'state', None)}; "
            f"tracked_state={getattr(tracked_state, 'state', None)}; "
            f"area_attrs={getattr(area_state, 'attributes', None)}"
        )
        raise AssertionError(debug_details)


async def test_fan_group_logic(
    hass: HomeAssistant,
    entities_fan_multiple: list[MockFan],
    entities_sensor_temperature_one: MockSensor,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_fan_groups: None,
) -> None:
    """Test Fan groups logic."""
    fan_group_entity_id = (
        f"{FAN_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_group"
    )
    fan_control_entity_id = (
        f"{SWITCH_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_control"
    )
    tracked_entity_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_temperature"
    )
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    temperature_sensor_entity_id = entities_sensor_temperature_one.entity_id

    assert_state(hass.states.get(fan_group_entity_id), STATE_OFF)
    assert_state(hass.states.get(fan_control_entity_id), STATE_OFF)
    assert_state(hass.states.get(temperature_sensor_entity_id), str(int(SENSOR_INITIAL_VALUE)))
    assert_state(hass.states.get(tracked_entity_id), str(float(SENSOR_INITIAL_VALUE)))
    assert_state(hass.states.get(motion_sensor_entity_id), STATE_OFF)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(fan_group_entity_id), STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    _assert_state_with_context(
        hass,
        fan_group_entity_id,
        STATE_OFF,
        context="fan control on, reset after occupancy clear",
        motion_sensor_entity_id=motion_sensor_entity_id,
        area_sensor_entity_id=area_sensor_entity_id,
        fan_control_entity_id=fan_control_entity_id,
        temperature_sensor_entity_id=temperature_sensor_entity_id,
        tracked_entity_id=tracked_entity_id,
    )

    hass.states.async_set(
        temperature_sensor_entity_id,
        str(int(SETPOINT_VALUE * 2)),
        attributes={
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            "unit_of_measurement": UnitOfTemperature.CELSIUS,
        },
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(temperature_sensor_entity_id), str(int(SETPOINT_VALUE * 2)))
    assert_state(hass.states.get(tracked_entity_id), str(SETPOINT_VALUE * 2))

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(fan_group_entity_id), STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    _assert_state_with_context(
        hass,
        fan_group_entity_id,
        STATE_OFF,
        context="fan control on, reset after occupancy clear (second cycle)",
        motion_sensor_entity_id=motion_sensor_entity_id,
        area_sensor_entity_id=area_sensor_entity_id,
        fan_control_entity_id=fan_control_entity_id,
        temperature_sensor_entity_id=temperature_sensor_entity_id,
        tracked_entity_id=tracked_entity_id,
    )

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_control_entity_id}
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(fan_control_entity_id), STATE_ON)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(fan_group_entity_id), STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    _assert_state_with_context(
        hass,
        fan_group_entity_id,
        STATE_OFF,
        context="fan control on, reset after occupancy clear (third cycle)",
        motion_sensor_entity_id=motion_sensor_entity_id,
        area_sensor_entity_id=area_sensor_entity_id,
        fan_control_entity_id=fan_control_entity_id,
        temperature_sensor_entity_id=temperature_sensor_entity_id,
        tracked_entity_id=tracked_entity_id,
    )

    hass.states.async_set(
        temperature_sensor_entity_id,
        str(SENSOR_INITIAL_VALUE),
        attributes={
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            "unit_of_measurement": UnitOfTemperature.CELSIUS,
        },
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(temperature_sensor_entity_id), str(SENSOR_INITIAL_VALUE))
    assert_state(hass.states.get(tracked_entity_id), str(float(SENSOR_INITIAL_VALUE)))
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_state(hass.states.get(fan_group_entity_id), STATE_OFF)

    hass.states.async_set(
        temperature_sensor_entity_id,
        str(int(SETPOINT_VALUE * 2)),
        attributes={
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            "unit_of_measurement": UnitOfTemperature.CELSIUS,
        },
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(temperature_sensor_entity_id), str(int(SETPOINT_VALUE * 2)))
    assert_state(hass.states.get(tracked_entity_id), str(SETPOINT_VALUE * 2))
    await wait_for_state(hass, fan_group_entity_id, STATE_ON)

    hass.states.async_set(
        temperature_sensor_entity_id,
        str(SENSOR_INITIAL_VALUE),
        attributes={
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
            "unit_of_measurement": UnitOfTemperature.CELSIUS,
        },
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(temperature_sensor_entity_id), str(SENSOR_INITIAL_VALUE))
    assert_state(hass.states.get(tracked_entity_id), str(float(SENSOR_INITIAL_VALUE)))
    await wait_for_state(hass, fan_group_entity_id, STATE_OFF)
