# tests/test_presence_timeouts.py

from __future__ import annotations

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.const import (
    ATTR_STATES,
    CONF_ACCENT_ENTITY,
    CONF_CLEAR_TIMEOUT,
    CONF_DARK_ENTITY,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
    DOMAIN,
    AreaStates,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_in_attribute,
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    setup_mock_entities,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor


@pytest.fixture(name="timeout_config_entry")
def mock_config_entry_timeout() -> MockConfigEntry:
    """Config entry with clear timeout enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_CLEAR_TIMEOUT] = 1  # minutes
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="secondary_states_config_entry")
def mock_config_entry_secondary_states() -> MockConfigEntry:
    """Config entry with secondary state entities enabled."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_SECONDARY_STATES: {
                CONF_ACCENT_ENTITY: "binary_sensor.accent_sensor",
                CONF_DARK_ENTITY: "binary_sensor.area_light_sensor",
                CONF_SLEEP_ENTITY: "binary_sensor.sleep_sensor",
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="secondary_states_sensors")
async def setup_secondary_state_sensors(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create binary sensors for the secondary states."""
    mock_binary_sensor_entities = [
        MockBinarySensor(name="sleep_sensor", unique_id="sleep_sensor", device_class=None),
        MockBinarySensor(name="area_light_sensor", unique_id="area_light_sensor", device_class=None),
        MockBinarySensor(name="accent_sensor", unique_id="accent_sensor", device_class=None),
    ]
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


async def test_clear_timeout_expiration(
    hass: HomeAssistant,
    freezer,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    timeout_config_entry: MockConfigEntry,
) -> None:
    """clear_timeout keeps the area occupied briefly after sensors go OFF, then clears."""
    await init_integration_helper(hass, [timeout_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Occupy area.
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_in_attribute(hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.OCCUPIED)

    # Sensors go clear; clear_timeout window starts "now".
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    start = dt_util.utcnow()

    # Still occupied within the timeout window.
    freezer.move_to(start + timedelta(seconds=30))
    async_fire_time_changed(hass, start + timedelta(seconds=30))
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    assert_in_attribute(hass.states.get(area_sensor_entity_id), ATTR_STATES, AreaStates.OCCUPIED)

    # Past clear_timeout: occupied should be cleared (entity becomes OFF).
    freezer.move_to(start + timedelta(minutes=1, seconds=1))
    async_fire_time_changed(hass, start + timedelta(minutes=1, seconds=1))
    await hass.async_block_till_done()

    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_OFF)
    assert_in_attribute(area_state, ATTR_STATES, AreaStates.OCCUPIED, negate=True)
    assert_in_attribute(area_state, ATTR_STATES, AreaStates.CLEAR)

    await shutdown_integration(hass, [timeout_config_entry])


async def test_clear_timeout_is_canceled_if_sensor_returns(
    hass: HomeAssistant,
    freezer,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    timeout_config_entry: MockConfigEntry,
) -> None:
    """If a sensor returns ON during clear_timeout, the pending clear is canceled."""
    await init_integration_helper(hass, [timeout_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)

    # Start timeout window.
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()
    start = dt_util.utcnow()

    # Sensor returns before timeout expires (should cancel the scheduled clear).
    freezer.move_to(start + timedelta(seconds=30))
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Go past the original timeout deadline; area should still be occupied.
    freezer.move_to(start + timedelta(minutes=1, seconds=1))
    async_fire_time_changed(hass, start + timedelta(minutes=1, seconds=1))
    await hass.async_block_till_done()

    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_ON)
    assert_in_attribute(area_state, ATTR_STATES, AreaStates.OCCUPIED)

    await shutdown_integration(hass, [timeout_config_entry])


async def test_secondary_state_change_ignores_unknown_and_unavailable(
    hass: HomeAssistant,
    secondary_states_sensors: list[MockBinarySensor],
    secondary_states_config_entry: MockConfigEntry,
) -> None:
    """Secondary state handler ignores STATE_UNKNOWN/STATE_UNAVAILABLE (no changes applied)."""
    await init_integration_helper(hass, [secondary_states_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Find the "dark" secondary sensor from the provided fixture list.
    dark_entity_id = next(
        sensor.entity_id
        for sensor in secondary_states_sensors
        if sensor.entity_id.endswith("area_light_sensor")
    )

    # Force at least one real area-state transition so the entity attributes (ATTR_STATES)
    # are populated via the AREA_STATE_CHANGED dispatcher.
    motion_entity_id = "binary_sensor.motion_sensor"
    hass.states.async_set(motion_entity_id, STATE_ON)
    await hass.async_block_till_done()

    baseline_state = hass.states.get(area_sensor_entity_id)
    assert baseline_state is not None
    baseline_states = list(baseline_state.attributes.get(ATTR_STATES, []))
    assert baseline_states  # sanity: should now be populated

    # Change the dark sensor to STATE_UNKNOWN -> should be ignored (no state recompute)
    hass.states.async_set(dark_entity_id, STATE_UNKNOWN)
    await hass.async_block_till_done()

    after_unknown = hass.states.get(area_sensor_entity_id)
    assert after_unknown is not None
    assert list(after_unknown.attributes.get(ATTR_STATES, [])) == baseline_states

    # Change the dark sensor to STATE_UNAVAILABLE -> should be ignored (no state recompute)
    hass.states.async_set(dark_entity_id, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    after_unavailable = hass.states.get(area_sensor_entity_id)
    assert after_unavailable is not None
    assert list(after_unavailable.attributes.get(ATTR_STATES, [])) == baseline_states

    await shutdown_integration(hass, [secondary_states_config_entry])
