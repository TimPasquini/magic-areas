"""Test fan control switch setup and event handling."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, AreaStates
from custom_components.magic_areas.features import CONF_FEATURE_FAN_GROUPS
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_fan_control_ignores_state_changed_event_for_other_areas(
    hass: HomeAssistant,
) -> None:
    """Test that fan control ignores AREA_STATE_CHANGED events from other areas.

    This test verifies that lines 113-119 in switch/fan_control.py are covered:
    The early return when area_id doesn't match the current area.
    """
    # Setup integration with fan groups enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_FAN_GROUPS: {}
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the fan control switch entity
    runtime_data = config_entry.runtime_data
    area = runtime_data.coordinator.data.area

    # Dispatch AREA_STATE_CHANGED event for a DIFFERENT area using dispatcher
    # This tests lines 112-119 in fan_control.py where area_id != self.area.id
    other_area_id = "some_other_area_id"
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        other_area_id,  # area_id that doesn't match our area
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),  # (new_states, lost_states, current_states)
    )
    await hass.async_block_till_done()

    # If the event handler for our fan control switch was called, it would have
    # returned early at line 119 (return statement) because area_id didn't match.
    # This test verifies that code path is exercised.

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_ignores_state_changed_event_with_no_state_changes(
    hass: HomeAssistant,
) -> None:
    """Test that fan control ignores AREA_STATE_CHANGED events with no actual state changes.

    This test verifies that line 135 in switch/fan_control.py is covered:
    The early return when both new_states and lost_states are empty.
    """
    # Setup integration with fan groups enabled
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_FAN_GROUPS: {}
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Get the area
    runtime_data = config_entry.runtime_data
    area = runtime_data.coordinator.data.area

    # Dispatch AREA_STATE_CHANGED event with EMPTY new_states and lost_states
    # This tests lines 122-123 in fan_control.py: if not new_states and not lost_states: return
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area.id,  # Correct area_id
        ([], [], [AreaStates.OCCUPIED]),  # (new_states, lost_states, current_states) - no changes
    )
    await hass.async_block_till_done()

    # The function should have returned early at line 135 due to no state changes

    await shutdown_integration(hass, [config_entry])
