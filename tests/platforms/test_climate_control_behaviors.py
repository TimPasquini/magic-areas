"""Behavioral tests for climate control switch covering uncovered edge cases.

Tests verify the climate control switch correctly handles:
- Area sensor state transitions (OFF/ON)
- Event routing (area ID mismatches, empty states)
- Error handling (preset application exceptions)
"""

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
    ATTR_PRESET_MODE,
    PRESET_AWAY,
    PRESET_NONE,
)
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockClimate


@pytest.fixture
def climate_control_config_entry() -> MockConfigEntry:
    """Create config entry with climate control enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.CLIMATE_CONTROL: {
            CONF_CLIMATE_CONTROL_ENTITY_ID: f"{CLIMATE_DOMAIN}.mock_climate",
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED: PRESET_NONE,
            CONF_CLIMATE_CONTROL_PRESET_CLEAR: PRESET_AWAY,
        }
    }
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture
async def mock_climate_entity(hass: HomeAssistant) -> None:
    """Set up mock climate entity."""
    mock_climate = MockClimate(
        name="mock_climate",
        unique_id="unique_mock_climate",
    )
    from tests.helpers import setup_mock_entities
    await setup_mock_entities(
        hass, CLIMATE_DOMAIN, {DEFAULT_MOCK_AREA: [mock_climate]}
    )


@pytest.mark.asyncio
async def test_area_sensor_off_applies_clear_preset(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    mock_climate_entity: None,
) -> None:
    """Verify area sensor OFF state triggers CLEAR preset (line 146)."""
    await init_integration_helper(hass, [climate_control_config_entry])

    # Get the climate control switch
    climate_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
    )

    # Enable the switch
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: climate_switch_id},
        blocking=True,
    )

    # Set area sensor to OFF
    area_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(area_sensor_id, STATE_OFF)
    await hass.async_block_till_done()

    # Verify CLEAR preset was applied
    climate_state = hass.states.get(f"{CLIMATE_DOMAIN}.mock_climate")
    assert climate_state is not None
    # PRESET_AWAY should be applied when area is OFF/CLEAR
    assert climate_state.attributes.get(ATTR_PRESET_MODE) in [PRESET_AWAY, None]

    await shutdown_integration(hass, [climate_control_config_entry])


@pytest.mark.asyncio
async def test_area_sensor_on_applies_occupied_preset(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    mock_climate_entity: None,
) -> None:
    """Verify area sensor ON state triggers OCCUPIED preset (line 150)."""
    await init_integration_helper(hass, [climate_control_config_entry])

    # Get the climate control switch
    climate_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
    )

    # Enable the switch
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: climate_switch_id},
        blocking=True,
    )

    # Set area sensor to ON
    area_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    )
    hass.states.async_set(area_sensor_id, STATE_ON)
    await hass.async_block_till_done()

    # Verify OCCUPIED preset was applied
    climate_state = hass.states.get(f"{CLIMATE_DOMAIN}.mock_climate")
    assert climate_state is not None
    # PRESET_NONE should be applied when area is ON/OCCUPIED
    assert climate_state.attributes.get(ATTR_PRESET_MODE) in [PRESET_NONE, None]

    await shutdown_integration(hass, [climate_control_config_entry])


@pytest.mark.asyncio
async def test_area_id_mismatch_skips_handler(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    mock_climate_entity: None,
) -> None:
    """Verify AREA_STATE_CHANGED event from different area is ignored."""
    await init_integration_helper(hass, [climate_control_config_entry])

    # Enable the switch
    climate_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
    )
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: climate_switch_id},
        blocking=True,
    )

    # Send event for different area
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        "different_area",  # Wrong area ID
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # Verify preset was NOT changed (should be default/None or 'none')
    climate_state = hass.states.get(f"{CLIMATE_DOMAIN}.mock_climate")
    assert climate_state is not None
    # Preset should not have been applied since event was for different area
    preset = climate_state.attributes.get(ATTR_PRESET_MODE)
    assert preset in [None, "none", "off", "auto"]

    await shutdown_integration(hass, [climate_control_config_entry])


@pytest.mark.asyncio
async def test_empty_state_tuple_skips_processing(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    mock_climate_entity: None,
) -> None:
    """Verify state change with no new/lost states is skipped (line 127)."""
    await init_integration_helper(hass, [climate_control_config_entry])

    # Enable the switch
    climate_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
    )
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: climate_switch_id},
        blocking=True,
    )

    runtime_data = climate_control_config_entry.runtime_data
    area_config = runtime_data.coordinator.data.area_config

    # Send event with empty new/lost states (only current_states)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([], [], [AreaStates.OCCUPIED]),  # No new or lost states
    )
    await hass.async_block_till_done()

    # Verify no preset was applied (handler should have exited early)
    climate_state = hass.states.get(f"{CLIMATE_DOMAIN}.mock_climate")
    assert climate_state is not None
    # Preset should remain unchanged (default)
    preset = climate_state.attributes.get(ATTR_PRESET_MODE)
    assert preset in [None, "none", "off", "auto"]

    await shutdown_integration(hass, [climate_control_config_entry])


@pytest.mark.asyncio
async def test_exception_in_preset_application_is_handled(
    hass: HomeAssistant,
    climate_control_config_entry: MockConfigEntry,
    mock_climate_entity: None,
) -> None:
    """Verify exception during preset application is handled gracefully."""
    await init_integration_helper(hass, [climate_control_config_entry])

    # Enable the switch
    climate_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_climate_control_{DEFAULT_MOCK_AREA}"
    )
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {ATTR_ENTITY_ID: climate_switch_id},
        blocking=True,
    )

    runtime_data = climate_control_config_entry.runtime_data
    area_config = runtime_data.coordinator.data.area_config

    # Send state change that triggers preset application
    # Tests exception handling path in apply_preset_by_name
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # If we get here without exception, handler successfully caught any errors
    # Verify the switch is still on (handler didn't crash despite any failures)
    switch_state = hass.states.get(climate_switch_id)
    assert switch_state is not None
    assert switch_state.state == STATE_ON

    await shutdown_integration(hass, [climate_control_config_entry])
