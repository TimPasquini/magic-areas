"""Tests for the Health feature."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import (
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_HEALTH,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    DOMAIN,
)

from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    assert_state,
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    setup_mock_entities,
    shutdown_integration,
    wait_for_state,
)
from tests.mocks import MockBinarySensor

# Fixtures

@pytest.fixture(name="health_config_entry")
def mock_config_entry_health() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_HEALTH: {
                    CONF_HEALTH_SENSOR_DEVICE_CLASSES: [
                        BinarySensorDeviceClass.PROBLEM,
                        BinarySensorDeviceClass.SMOKE,
                    ]
                }
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_health")
async def setup_integration_health(
    hass: HomeAssistant,
    health_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any, None]:
    """Set up integration with Health config."""

    await init_integration_helper(hass, [health_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()
    yield
    await shutdown_integration(hass, [health_config_entry])


@pytest.fixture(name="entities_health_sensors")
async def setup_entities_health_sensors(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create mock health sensors."""
    mock_entities = [
        MockBinarySensor(
            name="problem_sensor",
            unique_id="problem_sensor",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        MockBinarySensor(
            name="smoke_sensor",
            unique_id="smoke_sensor",
            device_class=BinarySensorDeviceClass.SMOKE,
        ),
        MockBinarySensor(
            name="motion_sensor", # Should be ignored
            unique_id="motion_sensor",
            device_class=BinarySensorDeviceClass.MOTION,
        ),
    ]
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_entities}
    )
    return mock_entities


# Tests

async def test_health_sensor(
    hass: HomeAssistant,
    entities_health_sensors: list[MockBinarySensor],
    _setup_integration_health,
) -> None:
    """Test health sensor logic."""

    health_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_health_{DEFAULT_MOCK_AREA}_health_problem"
    )
    problem_sensor = entities_health_sensors[0]
    smoke_sensor = entities_health_sensors[1]

    # Initial state (Healthy/OFF)
    await wait_for_state(hass, health_sensor_id, STATE_OFF)

    # Trigger problem sensor
    problem_sensor.turn_on()
    await hass.async_block_till_done()

    await wait_for_state(hass, health_sensor_id, STATE_ON)

    # Trigger smoke sensor (still ON)
    smoke_sensor.turn_on()
    await hass.async_block_till_done()

    await wait_for_state(hass, health_sensor_id, STATE_ON)

    # Clear problem (still ON due to smoke)
    problem_sensor.turn_off()
    await hass.async_block_till_done()

    await wait_for_state(hass, health_sensor_id, STATE_ON)

    # Clear smoke (OFF)
    smoke_sensor.turn_off()
    await hass.async_block_till_done()

    await wait_for_state(hass, health_sensor_id, STATE_OFF)


async def test_health_no_matching_entities(
    hass: HomeAssistant,
    health_config_entry: MockConfigEntry,
) -> None:
    """Test health sensor creation with no matching entities."""
    
    # Create a motion sensor (not in health device classes)
    mock_motion = MockBinarySensor(
        name="motion_sensor",
        unique_id="motion_sensor",
        device_class=BinarySensorDeviceClass.MOTION,
    )
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: [mock_motion]}
    )
    
    await init_integration_helper(hass, [health_config_entry])
    
    health_sensor_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_health_{DEFAULT_MOCK_AREA}_health_problem"
    assert hass.states.get(health_sensor_id) is None
    
    await shutdown_integration(hass, [health_config_entry])