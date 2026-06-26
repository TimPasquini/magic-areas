"""Climate-control behavior tests for normal area-state transitions."""


from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_AWAY,
    PRESET_NONE,
)
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import MagicAreasEvents
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.waits import wait_for_attribute
from tests.mocks import MockClimate

pytest_plugins = ("tests.platforms.climate_control_testkit",)

MOCK_CLIMATE_ENTITY_ID = f"{CLIMATE_DOMAIN}.mock_climate"
CLIMATE_SWITCH_ID = f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"


async def _enable_control_switch(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: CLIMATE_SWITCH_ID},
        blocking=True,
    )


async def test_area_sensor_off_applies_clear_preset(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    entities_climate_one: list[MockClimate],
    _setup_integration_climate_control: None,
) -> None:
    """CLEAR transition applies configured clear preset."""
    await _enable_control_switch(hass)

    area_id = climate_control_config_entry.runtime_data.coordinator.data.area_config.id
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_id,
        ([AreaStates.CLEAR], [AreaStates.OCCUPIED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    await wait_for_attribute(
        hass, MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE, PRESET_AWAY, timeout=2.0
    )


async def test_area_sensor_on_applies_occupied_preset(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    entities_climate_one: list[MockClimate],
    _setup_integration_climate_control: None,
) -> None:
    """OCCUPIED transition applies configured occupied preset."""
    await _enable_control_switch(hass)

    area_id = climate_control_config_entry.runtime_data.coordinator.data.area_config.id
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_id,
        ([AreaStates.OCCUPIED], [AreaStates.CLEAR], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    await wait_for_attribute(
        hass, MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE, PRESET_NONE, timeout=2.0
    )
