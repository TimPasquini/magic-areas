"""Test for area changes and how the system handles it."""

from collections.abc import AsyncGenerator
from datetime import timedelta
import logging
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.const import (
    ATTR_PRESENCE_SENSORS,
    ATTR_STATES,
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
    DOMAIN,
    MagicAreasEvents,
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

_LOGGER = logging.getLogger(__name__)


# Fixtures


@pytest.fixture(name="secondary_states_config_entry")
def mock_config_entry_secondary_states() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
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


@pytest.fixture(name="keep_only_sensor_config_entry")
def mock_config_entry_keep_only_sensor() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update({CONF_KEEP_ONLY_ENTITIES: ["binary_sensor.motion_sensor_1"]})
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="timeout_config_entry")
def mock_config_entry_timeout() -> MockConfigEntry:
    """Fixture for mock configuration entry with timeout."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_CLEAR_TIMEOUT] = 1  # 1 minute
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_secondary_states")
async def setup_integration_secondary_states(
    hass: HomeAssistant,
    secondary_states_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration with secondary states config."""

    await init_integration_helper(hass, [secondary_states_config_entry])
    yield
    await shutdown_integration(hass, [secondary_states_config_entry])


@pytest.fixture(name="_setup_integration_keep_only_sensor")
async def setup_integration_keep_only_sensor(
    hass: HomeAssistant,
    keep_only_sensor_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration with secondary states config."""

    await init_integration_helper(hass, [keep_only_sensor_config_entry])
    yield
    await shutdown_integration(hass, [keep_only_sensor_config_entry])


# Entities


@pytest.fixture(name="secondary_states_sensors")
async def setup_secondary_state_sensors(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create binary sensors for the secondary states."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="sleep_sensor",
            unique_id="sleep_sensor",
            device_class=None,
        ),
        MockBinarySensor(
            name="area_light_sensor",
            unique_id="area_light_sensor",
            device_class=BinarySensorDeviceClass.LIGHT,
        ),
        MockBinarySensor(
            name="accent_sensor",
            unique_id="accent_sensor",
            device_class=None,
        ),
    ]
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


# Tests


async def test_area_primary_state_change(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic,
) -> None:
    """Test primary area state change."""

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    assert_state(area_binary_sensor, STATE_OFF)
    assert_in_attribute(
        area_binary_sensor, ATTR_PRESENCE_SENSORS, motion_sensor_entity_id
    )
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.CLEAR)

    # Turn on motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Update states
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)
    assert_state(motion_sensor, STATE_ON)
    assert_state(area_binary_sensor, STATE_ON)
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.OCCUPIED)

    # Turn off motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    # @FIXME figure out why this is blocking instead of doing the VirtualClock trick
    # await asyncio.sleep(60)
    # await hass.async_block_till_done()

    # Update states
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)
    assert_state(motion_sensor, STATE_OFF)
    assert_state(area_binary_sensor, STATE_OFF)
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.CLEAR)


async def test_area_secondary_state_change(
    hass: HomeAssistant,
    secondary_states_sensors: list[MockBinarySensor],
    _setup_integration_secondary_states,
) -> None:
    """Test secondary area state changes."""

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    secondary_state_map = {
        secondary_states_sensors[0].entity_id: (AreaStates.SLEEP, None),
        secondary_states_sensors[1].entity_id: (AreaStates.BRIGHT, AreaStates.DARK),
        secondary_states_sensors[2].entity_id: (AreaStates.ACCENT, None),
    }

    for entity_id, state_tuples in secondary_state_map.items():
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)

        # Ensure off
        assert_state(entity_state, STATE_OFF)
        assert_in_attribute(
            area_binary_sensor, ATTR_STATES, state_tuples[0], negate=True
        )
        if state_tuples[1]:
            assert_in_attribute(area_binary_sensor, ATTR_STATES, state_tuples[1])

        # Turn entity on
        hass.states.async_set(entity_id, STATE_ON)
        await hass.async_block_till_done()

        # Update states
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)

        # Ensure on
        assert_state(entity_state, STATE_ON)
        assert_in_attribute(area_binary_sensor, ATTR_STATES, state_tuples[0])
        if state_tuples[1]:
            assert_in_attribute(
                area_binary_sensor, ATTR_STATES, state_tuples[1], negate=True
            )

        # Turn entity off
        hass.states.async_set(entity_id, STATE_OFF)
        await hass.async_block_till_done()

        # Update states
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)

        # Ensure off
        assert_state(entity_state, STATE_OFF)
        assert_in_attribute(
            area_binary_sensor, ATTR_STATES, state_tuples[0], negate=True
        )
        if state_tuples[1]:
            assert_in_attribute(area_binary_sensor, ATTR_STATES, state_tuples[1])


# Test extended state
# @TODO pending figuring out virtualclock


# Test keep-only sensors
async def test_keep_only_sensors(
    hass: HomeAssistant,
    entities_binary_sensor_motion_multiple: list[MockBinarySensor],
    _setup_integration_keep_only_sensor,
) -> None:
    """Test keep-only sensors."""

    motion_sensor_entity_id = entities_binary_sensor_motion_multiple[0].entity_id
    flappy_sensor_entity_id = entities_binary_sensor_motion_multiple[1].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(area_sensor_entity_id)

    assert_state(area_binary_sensor, STATE_OFF)
    assert_in_attribute(
        area_binary_sensor, ATTR_PRESENCE_SENSORS, motion_sensor_entity_id
    )
    assert_in_attribute(
        area_binary_sensor, ATTR_PRESENCE_SENSORS, flappy_sensor_entity_id
    )
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.CLEAR)

    # Turn on flappy sensor
    hass.states.async_set(flappy_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Update states, ensure area remains clear
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    flappy_sensor = hass.states.get(flappy_sensor_entity_id)

    assert_state(flappy_sensor, STATE_ON)
    assert_state(area_binary_sensor, STATE_OFF)
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.CLEAR)

    # Turn on motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Update states, ensure area is now occupied
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert_state(motion_sensor, STATE_ON)
    assert_state(area_binary_sensor, STATE_ON)
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.OCCUPIED)

    # Turn off motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    # Update states, ensure area remains occupied
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert_state(motion_sensor, STATE_OFF)
    assert_state(area_binary_sensor, STATE_ON)
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.OCCUPIED)

    # Turn off flappy sensor
    hass.states.async_set(flappy_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    # Update states, ensure area clears
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    flappy_sensor = hass.states.get(flappy_sensor_entity_id)

    assert_state(flappy_sensor, STATE_OFF)
    assert_state(area_binary_sensor, STATE_OFF)
    assert_in_attribute(area_binary_sensor, ATTR_STATES, AreaStates.CLEAR)


async def test_sensor_invalid_states(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic,
) -> None:
    """Test sensor state changes to invalid states."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Initial state
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)

    # Turn on
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)

    # Set to unavailable
    hass.states.async_set(motion_sensor_entity_id, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    # Should remain ON because unavailable is ignored
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)

    # Set to unknown
    hass.states.async_set(motion_sensor_entity_id, STATE_UNKNOWN)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)


async def test_sensor_missing(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic,
) -> None:
    """Test missing sensor entity."""
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Turn on
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)

    # Remove sensor
    hass.states.async_remove(motion_sensor_entity_id)
    await hass.async_block_till_done()

    # Force update via time interval
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=60))
    await hass.async_block_till_done()

    # Area should be clear if sensor is missing (treated as not ON)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)


async def test_clear_timeout_expiration(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    timeout_config_entry: MockConfigEntry,
    freezer,
) -> None:
    """Test clear timeout expiration.

    This integration uses dt_util.utcnow() to decide whether the clear timeout has
    elapsed, so the test must advance *real* (frozen) time, not only fire
    async_fire_time_changed().
    """
    await init_integration_helper(hass, [timeout_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Turn on -> occupied
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)

    # Turn off -> clear timeout starts (entity remains ON during timeout)
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    # Anchor time AFTER turning off (this is when last_off_time is set)
    off_time = dt_util.utcnow()

    # Still occupied due to clear timeout
    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    entity_state = hass.states.get(area_sensor_entity_id)
    assert entity_state is not None
    computed_states = entity_state.attributes.get("states") or []
    assert AreaStates.OCCUPIED in computed_states

    # Advance time by 30s (< 1 minute): still occupied
    freezer.move_to(off_time + timedelta(seconds=30))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    assert_state(hass.states.get(area_sensor_entity_id), STATE_ON)
    entity_state = hass.states.get(area_sensor_entity_id)
    assert entity_state is not None
    computed_states = entity_state.attributes.get("states") or []
    assert AreaStates.OCCUPIED in computed_states

    # Advance time past 1 minute: occupancy should clear
    freezer.move_to(off_time + timedelta(minutes=1, seconds=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    # Now the primary occupancy should be cleared (state should go OFF)
    assert_state(hass.states.get(area_sensor_entity_id), STATE_OFF)
    entity_state = hass.states.get(area_sensor_entity_id)
    assert entity_state is not None
    computed_states = entity_state.attributes.get("states") or []
    assert AreaStates.OCCUPIED not in computed_states
    assert AreaStates.EXTENDED not in computed_states
    assert AreaStates.CLEAR in computed_states

    await shutdown_integration(hass, [timeout_config_entry])


async def test_event_filtering(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_basic,
) -> None:
    """Test event filtering logic."""

    # Send event for different area
    async_dispatcher_send(
        hass,
        MagicAreasEvents.AREA_STATE_CHANGED,
        "other_area",
        ([], []),
    )
    await hass.async_block_till_done()
    # No assertion, just coverage of the early return
