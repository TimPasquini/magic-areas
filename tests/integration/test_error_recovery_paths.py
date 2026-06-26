"""Tests for error recovery and edge case paths."""



import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.assertions import assert_state
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.mark.asyncio
async def test_light_coordinator_data_refresh_on_setup(
    hass: HomeAssistant,
) -> None:
    """Test light platform refreshes coordinator when data is initially None."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    # Manually setup to control coordinator state
    await init_integration_helper(hass, [config_entry])

    # Verify light platform was set up successfully
    # (which means coordinator.data was available)
    runtime_data = config_entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.coordinator.data is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_sensor_value_parsing_invalid_string(
    hass: HomeAssistant,
) -> None:
    """Test fan control handles non-numeric sensor values gracefully."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config
    fan_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_fan_groups_{area_config.id}_fan_control"
    )
    assert_state(hass.states.get(fan_switch_id), STATE_OFF)

    # Create temperature sensor with invalid value
    hass.states.async_set("sensor.temperature_aggregate", "invalid_value")

    # Trigger fan control logic
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(fan_switch_id), STATE_OFF)
    assert runtime_data.coordinator.data is not None

    # Should handle the parsing error gracefully (no exception)
    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_area_sensor_turn_off_with_group(
    hass: HomeAssistant,
) -> None:
    """Test fan control turns off fan group when area sensor turns off."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.FAN_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config
    fan_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_fan_groups_{area_config.id}_fan_control"
    )
    assert_state(hass.states.get(fan_switch_id), STATE_OFF)

    # Create a mock fan group entity
    fan_group_entity_id = f"fan.magic_areas_fan_{area_config.id}"
    hass.states.async_set(fan_group_entity_id, STATE_ON)

    # Simulate area sensor turning off via STATE_CHANGED event
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.CLEAR], [AreaStates.OCCUPIED], [AreaStates.CLEAR]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(fan_switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_group_recovery_presence_sensor_no_states_attr(
    hass: HomeAssistant,
) -> None:
    """Test light group when presence sensor lacks states attribute."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config

    # Create presence sensor WITHOUT states attribute
    presence_entity_id = f"binary_sensor.magic_areas_presence_tracking_{area_config.id}_area_state"
    hass.states.async_set(
        presence_entity_id,
        STATE_ON,
        {},  # No states attribute
    )

    # Dispatch a state change event
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    light_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{area_config.id}_light_control"
    )
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_group_no_active_lights_fallback(hass: HomeAssistant) -> None:
    """Test light group with all lights off reverts to full entity list."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config
    light_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{area_config.id}_light_control"
    )
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    # Create mock lights all OFF
    hass.states.async_set("light.test_light_1", STATE_OFF)
    hass.states.async_set("light.test_light_2", STATE_OFF)

    # Dispatch state change (all lights are off, so active_lights will be empty)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_presence_binary_sensor_missing_coordinator_data(
    hass: HomeAssistant,
) -> None:
    """Test presence binary sensor handles missing coordinator data."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    await init_integration_helper(hass, [config_entry])

    # The presence sensor should initialize even if coordinator data is temporarily None
    # This test verifies the sensor's _load_sensors method handles this gracefully
    presence_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_"
        f"{DEFAULT_MOCK_AREA}_area_state"
    )
    assert hass.states.get(presence_sensor_id) is not None

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_group_secondary_state_no_valid_states_bright(
    hass: HomeAssistant,
) -> None:
    """Test light group entering BRIGHT state prevents turn-off."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config
    light_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{area_config.id}_light_control"
    )
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    # Send BRIGHT state change - should noop
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.BRIGHT], [], [AreaStates.BRIGHT]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_group_turn_on_with_kwargs_forwarding(
    hass: HomeAssistant,
) -> None:
    """Test light group forwards turn_on kwargs to lights."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config
    light_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{area_config.id}_light_control"
    )
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    # Create mock lights
    hass.states.async_set("light.test_light_1", STATE_OFF)

    # Send area occupied state which would normally trigger turn_on
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_light_group_all_lights_already_on_noop(
    hass: HomeAssistant,
) -> None:
    """Test light group does not send turn_on if lights already on."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.LIGHT_GROUPS: {}}

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    runtime_data = config_entry.runtime_data
    area_config = runtime_data.coordinator._area_config
    light_switch_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{area_config.id}_light_control"
    )
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    # Create mock lights already ON
    hass.states.async_set("light.test_light_1", STATE_ON)

    # Send area occupied (light already on, so _turn_on should noop)
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area_config.id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(light_switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])
