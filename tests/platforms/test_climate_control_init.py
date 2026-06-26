"""Initialization contract tests for climate-control platform behavior."""


from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_ECO,
    SERVICE_SET_PRESET_MODE,
    HVACMode,
)
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF
from homeassistant.core import HomeAssistant

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.assertions import (
    assert_attribute,
    assert_state,
)
from tests.mocks import MockClimate

pytest_plugins = ("tests.platforms.climate_control_testkit",)

MOCK_CLIMATE_ENTITY_ID = f"{CLIMATE_DOMAIN}.mock_climate"
CLIMATE_CONTROL_SWITCH_ENTITY_ID = (
    f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
)
AREA_SENSOR_ENTITY_ID = (
    f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
)


async def test_climate_control_init(
    hass: HomeAssistant,
    entities_climate_one: list[MockClimate],
    _setup_integration_climate_control: None,
) -> None:
    """Test climate control initialization behavior."""
    area_sensor_state = hass.states.get(AREA_SENSOR_ENTITY_ID)
    assert_state(area_sensor_state, STATE_OFF)
    climate_control_switch_state = hass.states.get(CLIMATE_CONTROL_SWITCH_ENTITY_ID)
    assert_state(climate_control_switch_state, STATE_OFF)
    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert_state(climate_state, STATE_OFF)

    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID}
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(MOCK_CLIMATE_ENTITY_ID), HVACMode.AUTO)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE: PRESET_ECO},
    )
    await hass.async_block_till_done()
    assert_attribute(hass.states.get(MOCK_CLIMATE_ENTITY_ID), ATTR_PRESET_MODE, PRESET_ECO)
