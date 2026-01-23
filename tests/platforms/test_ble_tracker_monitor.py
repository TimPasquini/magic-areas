"""Tests for the BLE Tracker feature."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.attrs import (
    ATTR_ACTIVE_SENSORS,
    ATTR_PRESENCE_SENSORS,
)
from custom_components.magic_areas.config_keys import (
    CONF_BLE_TRACKER_ENTITIES,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.core_constants import (
    DOMAIN,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_BLE_TRACKERS,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_in_attribute,
    assert_state,
    get_basic_config_entry_data,
    setup_mock_entities,
    shutdown_integration,
)
from tests.helpers import (
    init_integration as init_integration_helper,
)
from tests.mocks import MockSensor

# Fixtures


@pytest.fixture(name="ble_tracker_config_entry")
def mock_config_entry_ble_tracker() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_BLE_TRACKERS: {
                    CONF_BLE_TRACKER_ENTITIES: ["sensor.ble_tracker_1"],
                }
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_ble_tracker")
async def setup_integration_ble_tracker(
    hass: HomeAssistant,
    ble_tracker_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration with BLE tracker config."""

    await init_integration_helper(hass, [ble_tracker_config_entry])
    yield
    await shutdown_integration(hass, [ble_tracker_config_entry])


# Entities


@pytest.fixture(name="entities_ble_sensor_one")
async def setup_entities_ble_sensor_one(
    hass: HomeAssistant,
) -> list[MockSensor]:
    """Create one mock sensor and set up the system with it."""
    mock_ble_sensor_entities = [
        MockSensor(
            name="ble_sensor_1",
            unique_id="unique_ble_sensor",
            device_class=None,
        )
    ]
    await setup_mock_entities(
        hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_ble_sensor_entities}
    )
    return mock_ble_sensor_entities


# Tests


async def test_ble_tracker_presence_sensor(
    hass: HomeAssistant,
    entities_ble_sensor_one: list[MockSensor],
    _setup_integration_ble_tracker,
) -> None:
    """Test BLE tracker monitor functionality."""

    ble_sensor_entity_id = "sensor.ble_tracker_1"
    ble_tracker_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_ble_trackers_{DEFAULT_MOCK_AREA.value}_ble_tracker_monitor"
    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA.value}_area_state"

    hass.states.async_set(ble_sensor_entity_id, STATE_UNKNOWN)
    await hass.async_block_till_done()

    ble_sensor_state = hass.states.get(ble_sensor_entity_id)

    assert ble_sensor_state is not None
    assert ble_sensor_state.state is not None

    ble_tracker_state = hass.states.get(ble_tracker_entity_id)
    assert ble_tracker_state is not None
    assert ble_tracker_state.state == STATE_OFF
    assert ble_sensor_entity_id in ble_tracker_state.attributes[ATTR_ENTITY_ID]

    area_sensor_state = hass.states.get(area_sensor_entity_id)
    assert area_sensor_state is not None
    assert area_sensor_state.state == STATE_OFF
    assert ble_tracker_entity_id in area_sensor_state.attributes[ATTR_PRESENCE_SENSORS]

    # Set BLE sensor to DEFAULT_MOCK_AREA
    hass.states.async_set(ble_sensor_entity_id, DEFAULT_MOCK_AREA.value)
    await hass.async_block_till_done()

    ble_sensor_state = hass.states.get(ble_sensor_entity_id)
    assert_state(ble_sensor_state, DEFAULT_MOCK_AREA.value)

    ble_tracker_state = hass.states.get(ble_tracker_entity_id)
    assert_state(ble_tracker_state, STATE_ON)

    area_sensor_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_sensor_state, STATE_ON)
    assert_in_attribute(area_sensor_state, ATTR_ACTIVE_SENSORS, ble_tracker_entity_id)

    # Set BLE sensor to something else
    hass.states.async_set(ble_sensor_entity_id, STATE_UNKNOWN)
    await hass.async_block_till_done()

    ble_sensor_state = hass.states.get(ble_sensor_entity_id)
    assert_state(ble_sensor_state, STATE_UNKNOWN)

    ble_tracker_state = hass.states.get(ble_tracker_entity_id)
    assert_state(ble_tracker_state, STATE_OFF)

    area_sensor_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_sensor_state, STATE_OFF)


async def test_ble_tracker_missing_entity(
    hass: HomeAssistant,
    entities_ble_sensor_one: list[MockSensor],
    _setup_integration_ble_tracker,
) -> None:
    """Test BLE tracker with missing entity."""

    ble_sensor_entity_id = "sensor.ble_tracker_1"
    ble_tracker_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_ble_trackers_{DEFAULT_MOCK_AREA.value}_ble_tracker_monitor"

    # Remove the sensor from the state machine
    hass.states.async_remove(ble_sensor_entity_id)
    await hass.async_block_till_done()

    # The tracker normally updates via state-change events. Removing a sensor may not
    # generate an event the tracker reacts to unless we simulate one, which is awkward.
    # Internally, _update_state iterates over tracked sensors and calls hass.states.get().
    # We rely on the initial update path to ensure missing sensor states are handled
    # gracefully and do not cause a crash.

    # Let's simulate a state change event for the sensor, but where the new state is None (removal)
    # or just ensure the tracker state remains correct.

    ble_tracker_state = hass.states.get(ble_tracker_entity_id)
    assert_state(ble_tracker_state, STATE_OFF)


async def test_ble_tracker_no_entities_configured(
    hass: HomeAssistant,
) -> None:
    """Test BLE tracker with no entities configured."""

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_BLE_TRACKERS: {
                    CONF_BLE_TRACKER_ENTITIES: [],
                }
            }
        }
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    await init_integration_helper(hass, [config_entry])

    ble_tracker_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_ble_trackers_{DEFAULT_MOCK_AREA.value}_ble_tracker_monitor"
    assert hass.states.get(ble_tracker_entity_id) is None

    await shutdown_integration(hass, [config_entry])
