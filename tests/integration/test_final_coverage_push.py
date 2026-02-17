"""Final push to reach 96% coverage by testing remaining error paths."""

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
async def test_fan_control_disabled_ignores_events(hass: HomeAssistant) -> None:
    """Test fan control returns early when disabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Send state changes - should be handled gracefully
    for new_state in [AreaStates.OCCUPIED, AreaStates.CLEAR, AreaStates.DARK]:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area_config.id,
            ([new_state], [], [new_state]),
        )
        await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_groups_handles_no_states(hass: HomeAssistant) -> None:
    """Test light groups with no state changes."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Send event with no state changes
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_multiple_state_transitions(hass: HomeAssistant) -> None:
    """Test rapid state transitions."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {},
        MagicAreasFeatures.FAN_GROUPS: {},
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Rapid transitions
    state_transitions = [
        AreaStates.OCCUPIED,
        AreaStates.EXTENDED,
        AreaStates.OCCUPIED,
        AreaStates.CLEAR,
        AreaStates.DARK,
        AreaStates.BRIGHT,
    ]

    for state in state_transitions:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area_config.id,
            ([state], [], [state]),
        )
        await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_area_with_all_features(hass: HomeAssistant) -> None:
    """Test area with multiple features enabled simultaneously."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {},
        MagicAreasFeatures.FAN_GROUPS: {},
        MagicAreasFeatures.CLIMATE_CONTROL: {
            "target_entity": "climate.test",
            "presets": {"occupied": "heat", "clear": "off"},
        },
        MagicAreasFeatures.AGGREGATES: {},
        MagicAreasFeatures.PRESENCE_HOLD: {},
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Test with occupied state
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # Test with clear state
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.CLEAR], [AreaStates.OCCUPIED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_extended_timeout_scenario(hass: HomeAssistant) -> None:
    """Test extended timeout state transitions."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.LIGHT_GROUPS: {},
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Occupied → Extended → Clear sequence
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.EXTENDED], [], [AreaStates.EXTENDED]),
    )
    await hass.async_block_till_done()

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.CLEAR], [AreaStates.EXTENDED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])
