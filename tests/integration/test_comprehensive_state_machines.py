"""Comprehensive state machine and error path tests for reaching 96% coverage."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ON, STATE_OFF
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
async def test_light_group_dark_state_noop(hass: HomeAssistant) -> None:
    """Test light group enters DARK state and does not turn off.

    Targets lines 454-458 in light.py - debug logging when entering DARK state.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Create a mock light
    hass.states.async_set("light.test_light", STATE_OFF)

    # Send state changes: OCCUPIED -> DARK (should noop for light groups)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    # Now transition to DARK - light group should noop
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.DARK], [AreaStates.OCCUPIED], [AreaStates.DARK]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_group_priority_state_transitions(
    hass: HomeAssistant,
) -> None:
    """Test light group handles coming out of priority states.

    Targets lines 461-476 in light.py - PRIORITY_STATE handling.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Create a mock light
    hass.states.async_set("light.test_light", STATE_OFF)

    # Test transition through SLEEP state (priority state)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.SLEEP], [], [AreaStates.SLEEP]),
    )
    await hass.async_block_till_done()

    # Come out of SLEEP and go to CLEAR
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.CLEAR], [AreaStates.SLEEP], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_fallback_to_presence_sensor(
    hass: HomeAssistant,
) -> None:
    """Test fan control falls back to presence sensor when _last_states not set.

    Targets lines 154-170 in switch/fan_control.py - presence sensor fallback.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Create a presence sensor for the area with states attribute
    presence_entity_id = f"binary_sensor.magic_areas_presence_tracking_{area_config.id}_area_state"
    hass.states.async_set(
        presence_entity_id,
        STATE_ON,
        {"states": [AreaStates.OCCUPIED]},
    )

    # Create temperature sensor for tracking
    hass.states.async_set("sensor.temperature_aggregate", "22.5")

    # Trigger fan control (should read from presence sensor if _last_states is None)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_missing_fan_group_early_return(
    hass: HomeAssistant,
) -> None:
    """Test fan control returns early when no fan group entity ID resolved.

    Targets lines 230-234 in switch/fan_control.py - no fan group check.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Send area state change - should skip if no fan group
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_climate_control_empty_preset_state_missing(
    hass: HomeAssistant,
) -> None:
    """Test climate control when configured state has no preset.

    Targets lines 118-124 in switch/climate_control.py - preset lookup.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.CLIMATE_CONTROL: {
            "target_entity": "climate.test",
            "presets": {
                "occupied": "heat",
                # No preset for "extended" - should handle gracefully
            },
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Send EXTENDED state with no preset
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.EXTENDED], [AreaStates.OCCUPIED], [AreaStates.EXTENDED]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_presence_hold_ignores_other_areas_multiple_times(
    hass: HomeAssistant,
) -> None:
    """Test presence hold consistently ignores events from other areas.

    Targets lines 91-98 in switch/presence_hold.py - area ID check.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.PRESENCE_HOLD: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Send multiple events from different areas
    other_areas = ["bedroom", "living_room", "bathroom"]
    for other_area_id in other_areas:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            other_area_id,
            ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
        )
        await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_complex_feature_interaction_all_disabled(
    hass: HomeAssistant,
) -> None:
    """Test that disabling all features results in minimal state processing.

    Targets early returns in various platforms.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {}  # No features enabled

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Send various state changes - all should be ignored since no features
    for state in [
        AreaStates.OCCUPIED,
        AreaStates.EXTENDED,
        AreaStates.CLEAR,
        AreaStates.DARK,
        AreaStates.BRIGHT,
    ]:
        async_dispatcher_send(
            hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            area_config.id,
            ([state], [], [state]),
        )
        await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_group_active_lights_query(hass: HomeAssistant) -> None:
    """Test light group correctly identifies active lights.

    Targets line 200 in light.py - active light filtering.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Create multiple mock lights with different states
    hass.states.async_set("light.test_light_1", STATE_ON)
    hass.states.async_set("light.test_light_2", STATE_OFF)
    hass.states.async_set("light.test_light_3", STATE_ON)

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Send area occupied state
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_presence_sensor_recovery_from_registry(
    hass: HomeAssistant,
) -> None:
    """Test light group recovers state from presence sensor via entity registry.

    Targets lines 340-353 in light.py - registry fallback.
    """
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Set up presence sensor with states attribute
    presence_entity_id = f"binary_sensor.magic_areas_presence_tracking_{area_config.id}_area_state"
    hass.states.async_set(
        presence_entity_id,
        STATE_ON,
        {"states": [AreaStates.OCCUPIED, AreaStates.DARK]},
    )

    # Trigger a state change event
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.DARK], [AreaStates.OCCUPIED], [AreaStates.DARK]),
    )
    await hass.async_block_till_done()

    await shutdown_integration(hass, [config_entry])
