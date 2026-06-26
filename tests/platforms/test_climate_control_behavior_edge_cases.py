"""Climate-control behavior tests for routing and error edge cases."""

from unittest.mock import patch

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    PRESET_AWAY,
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


async def test_area_id_mismatch_skips_handler(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    entities_climate_one: list[MockClimate],
    _setup_integration_climate_control: None,
) -> None:
    """Events from non-owning areas do not mutate preset."""
    await _enable_control_switch(hass)

    runtime_data = climate_control_config_entry.runtime_data
    area_id = runtime_data.coordinator.data.area_config.id
    hass.states.async_set(
        MOCK_CLIMATE_ENTITY_ID,
        "heat",
        attributes={ATTR_PRESET_MODE: PRESET_AWAY},
    )
    await hass.async_block_till_done()

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        "different_area_id",
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert climate_state is not None
    assert climate_state.attributes.get(ATTR_PRESET_MODE) == PRESET_AWAY

    # Sanity: matching area still applies changes.
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_id,
        ([AreaStates.CLEAR], [], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()
    await wait_for_attribute(
        hass, MOCK_CLIMATE_ENTITY_ID, ATTR_PRESET_MODE, PRESET_AWAY, timeout=2.0
    )


async def test_empty_state_tuple_skips_processing(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    entities_climate_one: list[MockClimate],
    _setup_integration_climate_control: None,
) -> None:
    """Empty area-state tuple should be ignored safely."""
    await _enable_control_switch(hass)

    area_id = climate_control_config_entry.runtime_data.coordinator.data.area_config.id
    hass.states.async_set(
        MOCK_CLIMATE_ENTITY_ID,
        "heat",
        attributes={ATTR_PRESET_MODE: PRESET_AWAY},
    )
    await hass.async_block_till_done()

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_id,
        ([], [], []),
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert climate_state is not None
    assert climate_state.attributes.get(ATTR_PRESET_MODE) == PRESET_AWAY


async def test_exception_in_preset_application_is_handled(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    entities_climate_one: list[MockClimate],
    _setup_integration_climate_control: None,
) -> None:
    """Exceptions during preset application are contained."""
    await _enable_control_switch(hass)

    area_id = climate_control_config_entry.runtime_data.coordinator.data.area_config.id
    switch_entity = hass.data["entity_components"]["switch"].get_entity(CLIMATE_SWITCH_ID)
    assert switch_entity is not None

    with patch.object(switch_entity, "apply_preset", side_effect=ValueError("boom")):
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area_id,
            ([AreaStates.CLEAR], [], [AreaStates.CLEAR]),
        )
        await hass.async_block_till_done()

    climate_state = hass.states.get(MOCK_CLIMATE_ENTITY_ID)
    assert climate_state is not None
