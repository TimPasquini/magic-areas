"""Integration tests for area-state robustness and timeout handling."""

from datetime import timedelta
from typing import Protocol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.magic_areas.area_state import AreaStates
from tests.helpers import (
    assert_state,
    init_integration as init_integration_helper,
    shutdown_integration,
    wait_for_state,
)
from tests.mocks import MockBinarySensor

pytest_plugins = ("tests.integration.area_state_testkit",)


class _Freezer(Protocol):
    """Protocol for freezegun freezer fixture."""

    def move_to(self, target_datetime: object) -> None: ...


async def test_sensor_invalid_states(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic: None,
) -> None:
    """Unavailable/unknown sensor states should not clear active occupancy."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await wait_for_state(hass, area_sensor_entity_id, STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    await wait_for_state(hass, area_sensor_entity_id, STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_UNKNOWN)
    await hass.async_block_till_done()
    await wait_for_state(hass, area_sensor_entity_id, STATE_ON)


async def test_sensor_missing(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic: None,
) -> None:
    """Missing sensor should eventually clear occupancy."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await wait_for_state(hass, area_sensor_entity_id, STATE_ON)

    hass.states.async_remove(motion_sensor_entity_id)
    await hass.async_block_till_done()
    clear_at = dt_util.utcnow() + timedelta(seconds=60)
    async_fire_time_changed(hass, clear_at)
    await hass.async_block_till_done()
    await wait_for_state(hass, area_sensor_entity_id, STATE_OFF)


async def test_clear_timeout_expiration(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    timeout_config_entry: MockConfigEntry,
    freezer: _Freezer,
) -> None:
    """Clear timeout should hold occupied until timeout elapses."""
    await init_integration_helper(hass, [timeout_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await wait_for_state(hass, area_sensor_entity_id, STATE_ON)
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    off_time = dt_util.utcnow()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    state = hass.states.get(area_sensor_entity_id)
    assert state is not None
    computed_states = state.attributes.get("states") or []
    assert AreaStates.OCCUPIED in computed_states

    within_timeout = off_time + timedelta(seconds=30)
    freezer.move_to(within_timeout)
    async_fire_time_changed(hass, within_timeout)
    await hass.async_block_till_done()
    await wait_for_state(hass, area_sensor_entity_id, STATE_ON)

    after_timeout = off_time + timedelta(minutes=1, seconds=1)
    freezer.move_to(after_timeout)
    async_fire_time_changed(hass, after_timeout)
    await hass.async_block_till_done()
    await wait_for_state(hass, area_sensor_entity_id, STATE_OFF)

    state = hass.states.get(area_sensor_entity_id)
    assert state is not None
    computed_states = state.attributes.get("states") or []
    assert AreaStates.OCCUPIED not in computed_states
    assert AreaStates.EXTENDED not in computed_states
    assert AreaStates.CLEAR in computed_states

    await shutdown_integration(hass, [timeout_config_entry])
