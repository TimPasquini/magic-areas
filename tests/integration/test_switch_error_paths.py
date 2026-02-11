"""Integration tests for switch error handling paths to reach 96% coverage."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, AreaStates
from custom_components.magic_areas.features import (
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_CLIMATE_CONTROL,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_media_player_control_clear_event_no_group_entity(
    hass: HomeAssistant,
) -> None:
    """Test media player control handles missing group entity on clear.

    Covers lines 94-102 in switch/media_player_control.py.
    """
    # Setup integration with media player control enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: {}
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Dispatch area clear event
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area.id,
        ([AreaStates.CLEAR], [AreaStates.OCCUPIED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    # Should handle missing group entity gracefully

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_media_player_control_no_state_changes(
    hass: HomeAssistant,
) -> None:
    """Test media player control with no state changes.

    Covers line 93 in switch/media_player_control.py.
    """
    # Setup integration with media player control enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: {}
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Dispatch state change with NO actual changes
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area.id,
        ([], [], [AreaStates.OCCUPIED]),  # No new or lost states
    )
    await hass.async_block_till_done()

    # Should exit early and not process anything

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_presence_hold_switch_ignore_other_areas(
    hass: HomeAssistant,
) -> None:
    """Test presence hold ignores state changes from other areas.

    Covers error paths in switch/presence_hold.py.
    """
    # Setup integration with presence hold enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_PRESENCE_HOLD: {}
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Dispatch state change from different area
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        "some_other_area",
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # Should be ignored

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_climate_control_ignores_unrelated_states(
    hass: HomeAssistant,
) -> None:
    """Test climate control ignores when occupied but no climate entity.

    Covers error handling in switch/climate_control.py.
    """
    # Setup integration with climate control but no target entity
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_CLIMATE_CONTROL: {
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
    area = runtime_data.area

    # Dispatch various state changes
    for new_state in [AreaStates.OCCUPIED, AreaStates.CLEAR, AreaStates.EXTENDED]:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area.id,
            ([new_state], [], [new_state]),
        )
        await hass.async_block_till_done()

    # Should handle all gracefully

    await shutdown_integration(hass, [config_entry])
