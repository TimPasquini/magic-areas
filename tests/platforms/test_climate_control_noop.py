"""No-op behavior tests for climate-control."""


from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_ECO,
    SERVICE_SET_PRESET_MODE,
)
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.waits import wait_for_state
from tests.mocks import MockBinarySensor, MockClimate

pytest_plugins = ("tests.platforms.climate_control_testkit",)

MOCK_CLIMATE_ENTITY_ID = f"{CLIMATE_DOMAIN}.mock_climate"
CLIMATE_CONTROL_SWITCH_ENTITY_ID = (
    f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
)
AREA_SENSOR_ENTITY_ID = (
    f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
)


def _assert_preset(
    hass: HomeAssistant,
    expected_value: str,
    *,
    context: str,
) -> None:
    """Assert preset mode with context for failures."""
    entity_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    if not entity_state:
        raise AssertionError(f"{context}: missing state for {MOCK_CLIMATE_ENTITY_ID}")
    actual_value = str(entity_state.attributes.get(ATTR_PRESET_MODE))
    if actual_value != expected_value:
        raise AssertionError(
            f"{context}: expected preset={expected_value}, actual={actual_value}"
        )


async def test_climate_control_logic_noop_when_control_switch_off(
    hass: HomeAssistant,
    entities_climate_one: list[MockClimate],
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_climate_control: None,
) -> None:
    """Climate presets should not change while climate control switch is off."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id

    await wait_for_state(hass, CLIMATE_CONTROL_SWITCH_ENTITY_ID, STATE_OFF)
    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID}
    )
    await hass.async_block_till_done()
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE: PRESET_ECO},
    )
    await hass.async_block_till_done()

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    _assert_preset(hass, PRESET_ECO, context="control switch off transition")
