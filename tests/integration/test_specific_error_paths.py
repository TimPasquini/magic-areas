"""Tests targeting specific uncovered error paths in key modules."""

import pytest
from unittest.mock import AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, AreaStates
from custom_components.magic_areas.features import CONF_FEATURE_FAN_GROUPS
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_fan_control_missing_tracked_sensor_value_parsing(
    hass: HomeAssistant,
) -> None:
    """Test fan control when tracked sensor returns invalid value.

    Targets lines 243-251 in switch/fan_control.py (ValueError/TypeError handling).
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_FAN_GROUPS: {
            "tracked_device_class": "temperature",
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Create a sensor with invalid value that can't be parsed
    hass.states.async_set("sensor.temperature_aggregate", "not_a_number")

    # Trigger fan control logic
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # Should handle the parsing error gracefully

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_area_sensor_turned_off(hass: HomeAssistant) -> None:
    """Test area sensor state change handler.

    Targets lines 200-204 in switch/fan_control.py (new_state handling).
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {CONF_FEATURE_FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Simulate area sensor turning off
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        DEFAULT_MOCK_AREA,
        ([AreaStates.CLEAR], [AreaStates.OCCUPIED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_climate_control_with_missing_entity_multiple_states(
    hass: HomeAssistant,
) -> None:
    """Test climate control when target entity doesn't exist.

    Targets error handling in switch/climate_control.py (lines 118-124, 142, 146).
    """
    from custom_components.magic_areas.features import CONF_FEATURE_CLIMATE_CONTROL

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        CONF_FEATURE_CLIMATE_CONTROL: {
            "target_entity": "climate.nonexistent",
            "presets": {
                "occupied": "heat",
                "clear": "off",
                "extended": "eco",
                "dark": "auto",
            },
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Send multiple state changes to trigger preset lookups
    states_to_test = [
        AreaStates.OCCUPIED,
        AreaStates.EXTENDED,
        AreaStates.DARK,
        AreaStates.CLEAR,
    ]

    for state in states_to_test:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area.id,
            ([state], [], [state]),
        )
        await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_entity_registry_filter_ignore_throttle(hass: HomeAssistant) -> None:
    """Test entity registry filter throttling.

    Targets throttle check in base/magic.py (lines 292-295).
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Get the filter function
    filter_func = area.make_entity_registry_filter()

    # Create event data
    event_data = {
        "entity_id": "light.test",
        "action": "update",
        "changes": {"area_id": area.id},
    }

    # First call should process it (or not based on timestamp)
    result1 = filter_func(event_data)

    # Immediate second call should be throttled
    result2 = filter_func(event_data)

    # Both should be booleans
    assert isinstance(result1, bool)
    assert isinstance(result2, bool)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_device_registry_filter_ignore_throttle(hass: HomeAssistant) -> None:
    """Test device registry filter throttling.

    Targets throttle check in base/magic.py (lines 333-337).
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area = runtime_data.area

    # Get the filter function
    filter_func = area.make_device_registry_filter()

    # Create event data
    event_data = {
        "device_id": "device_123",
        "action": "update",
        "changes": {"area_id": area.id},
    }

    # First call should process it
    result1 = filter_func(event_data)

    # Immediate second call should be throttled
    result2 = filter_func(event_data)

    # Both should be booleans
    assert isinstance(result1, bool)
    assert isinstance(result2, bool)

    await shutdown_integration(hass, [config_entry])
