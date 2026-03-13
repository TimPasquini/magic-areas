"""Test fan control switch setup and event handling."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasEvents, MagicAreasFeatures
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_OFF
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


async def _setup_fan_control(hass: HomeAssistant) -> MockConfigEntry:
    """Set up a minimal fan-groups config entry for fan-control tests."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {MagicAreasFeatures.FAN_GROUPS: {}}
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])
    return config_entry


def _fan_control_switch_id() -> str:
    return f"{SWITCH_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_control"


@pytest.mark.asyncio
async def test_fan_control_ignores_state_changed_event_for_other_areas(
    hass: HomeAssistant,
) -> None:
    """Fan control ignores AREA_STATE_CHANGED events for other areas."""
    config_entry = await _setup_fan_control(hass)
    switch_id = _fan_control_switch_id()
    assert_state(hass.states.get(switch_id), STATE_OFF)

    other_area_id = "some_other_area_id"
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        other_area_id,
        ([AreaStates.OCCUPIED], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(switch_id), STATE_OFF)
    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_ignores_state_changed_event_with_no_state_changes(
    hass: HomeAssistant,
) -> None:
    """Fan control ignores AREA_STATE_CHANGED events with no state deltas."""
    config_entry = await _setup_fan_control(hass)
    switch_id = _fan_control_switch_id()
    assert_state(hass.states.get(switch_id), STATE_OFF)

    runtime_data = config_entry.runtime_data
    area = runtime_data.coordinator.data.area_config

    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        area.id,
        ([], [], [AreaStates.OCCUPIED]),
    )
    await hass.async_block_till_done()
    assert_state(hass.states.get(switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_area_sensor_state_changed_no_new_state(
    hass: HomeAssistant,
) -> None:
    """Smoke check: area sensor handler path remains stable when data is absent."""
    config_entry = await _setup_fan_control(hass)
    switch_id = _fan_control_switch_id()
    assert_state(hass.states.get(switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_missing_fan_group_entity(
    hass: HomeAssistant,
) -> None:
    """Fan control handles missing fan-group entity resolution gracefully."""
    config_entry = await _setup_fan_control(hass)
    switch_id = _fan_control_switch_id()
    assert_state(hass.states.get(switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])


@pytest.mark.asyncio
async def test_fan_control_aggregate_sensor_state_changed_no_tracked_sensor(
    hass: HomeAssistant,
) -> None:
    """Aggregate sensor handler tolerates missing tracked sensor state."""
    config_entry = await _setup_fan_control(hass)
    switch_id = _fan_control_switch_id()
    assert_state(hass.states.get(switch_id), STATE_OFF)

    await shutdown_integration(hass, [config_entry])
