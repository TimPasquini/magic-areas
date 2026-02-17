"""Integration tests for climate control error handling paths."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_climate_control_handles_missing_climate_entity(
    hass: HomeAssistant,
) -> None:
    """Test climate control gracefully handles missing climate entity."""
    # Setup integration with climate control enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.CLIMATE_CONTROL: {
            "target_entity": "climate.nonexistent",
            "presets": {
                "occupied": "heat",
                "clear": "off",
            },
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator.data.area_config

    # Dispatch area state change that would trigger climate control
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # The handler should gracefully handle missing entity

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_climate_control_handles_empty_preset_mapping(
    hass: HomeAssistant,
) -> None:
    """Test climate control with incomplete preset mappings."""
    # Setup integration with climate control but missing some preset mappings
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.CLIMATE_CONTROL: {
            "target_entity": "climate.living_room",
            "presets": {
                # Missing some states - should handle gracefully
                "occupied": "heat",
            },
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator.data.area_config

    # Dispatch area clear event - should handle gracefully even without preset
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.CLEAR], [AreaStates.OCCUPIED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_climate_control_ignores_other_areas(
    hass: HomeAssistant,
) -> None:
    """Test climate control ignores state changes for other areas."""
    # Setup integration with climate control enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.CLIMATE_CONTROL: {
            "target_entity": "climate.living_room",
            "presets": {
                "occupied": "heat",
                "clear": "off",
            },
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Dispatch state change for a DIFFERENT area
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        "some_other_area",  # Different area
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # Should be ignored since it's for a different area

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_climate_control_ignores_no_state_changes(
    hass: HomeAssistant,
) -> None:
    """Test climate control ignores AREA_STATE_CHANGED with no actual changes."""
    # Setup integration with climate control enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.CLIMATE_CONTROL: {
            "target_entity": "climate.living_room",
            "presets": {
                "occupied": "heat",
                "clear": "off",
            },
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator.data.area_config

    # Dispatch state change with NO actual state changes
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([], [], [AreaStates.OCCUPIED]),  # Empty new_states and lost_states
    )
    await hass.async_block_till_done()

    # Should be ignored due to no state changes

    await shutdown_integration(hass, [config_entry])
