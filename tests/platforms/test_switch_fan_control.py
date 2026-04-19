"""Switch platform tests for fan-control behavior."""

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import MagicAreasEvents
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    init_integration as init_integration_helper,
    shutdown_integration,
    wait_for_state,
)
from tests.mocks import MockFan, MockSensor

pytest_plugins = ("tests.platforms.switch_testkit",)


async def test_fan_control_switch(
    hass: HomeAssistant,
    fan_control_config_entry: MockConfigEntry,
    entities_fan_control: tuple[MockFan, MockSensor],
) -> None:
    """Test fan control switch logic."""
    mock_fan, _mock_sensor = entities_fan_control
    aggregate_sensor_id = f"{SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_{SensorDeviceClass.TEMPERATURE}"

    await init_integration_helper(hass, [fan_control_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_control"
    )
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_id}
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, switch_id, STATE_ON)

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        ([AreaStates.CLEAR], [], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, mock_fan.entity_id, STATE_OFF)

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA.value,
        ([AreaStates.OCCUPIED], [AreaStates.CLEAR], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    await wait_for_state(hass, mock_fan.entity_id, STATE_OFF)

    hass.states.async_set(aggregate_sensor_id, "30.0")
    await hass.async_block_till_done()
    await wait_for_state(hass, mock_fan.entity_id, STATE_ON)

    await shutdown_integration(hass, [fan_control_config_entry])
