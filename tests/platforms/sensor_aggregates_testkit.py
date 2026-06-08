"""Shared fixtures/helpers for sensor aggregate platform tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from random import randint

import pytest
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import UnitOfElectricCurrent, UnitOfTemperature
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.entities import setup_mock_entities
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockBinarySensor, MockSensor


@pytest.fixture(name="aggregates_config_entry")
def mock_config_entry_aggregates() -> MockConfigEntry:
    """Fixture for default aggregate-enabled configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.AGGREGATES: {CONF_AGGREGATES_MIN_ENTITIES: 1}
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="aggregates_filtered_config_entry")
def mock_config_entry_aggregates_filtered() -> MockConfigEntry:
    """Fixture with filtered binary sensor classes (door-only)."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                MagicAreasFeatures.AGGREGATES: {
                    CONF_AGGREGATES_MIN_ENTITIES: 1,
                    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: [
                        BinarySensorDeviceClass.DOOR
                    ],
                },
                MagicAreasFeatures.HEALTH: {},
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_aggregates")
async def setup_integration_aggregates(
    hass: HomeAssistant,
    aggregates_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up integration with aggregate-enabled config entry."""
    await init_integration_helper(hass, [aggregates_config_entry])
    yield
    await shutdown_integration(hass, [aggregates_config_entry])


@pytest.fixture(name="entities_binary_sensor_connectivity_multiple")
async def setup_entities_binary_sensor_connectivity_multiple(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create multiple connectivity binary sensors in the area."""
    entities = [
        MockBinarySensor(
            name=f"connectivity_sensor_{i}",
            unique_id=f"connectivity_sensor_{i}",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
        )
        for i in range(3)
    ]
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: entities})
    return entities


@pytest.fixture(name="entities_sensor_temperature_multiple")
async def setup_entities_sensor_temperature_multiple(
    hass: HomeAssistant,
) -> list[MockSensor]:
    """Create multiple temperature sensors in the area."""
    entities: list[MockSensor] = []
    for i in range(3):
        entities.append(
            MockSensor(
                name=f"temperature_sensor_{i}",
                unique_id=f"temperature_sensor_{i}",
                native_value=randint(0, 100),
                device_class=SensorDeviceClass.TEMPERATURE,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                unit_of_measurement=UnitOfTemperature.CELSIUS,
                extra_state_attributes={"unit_of_measurement": UnitOfTemperature.CELSIUS},
            )
        )
    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: entities})
    return entities


@pytest.fixture(name="entities_sensor_current_multiple")
async def setup_entities_sensor_current_multiple(
    hass: HomeAssistant,
) -> list[MockSensor]:
    """Create multiple current sensors in the area."""
    entities: list[MockSensor] = []
    for i in range(3):
        entities.append(
            MockSensor(
                name=f"current_sensor_{i}",
                unique_id=f"current_sensor_{i}",
                native_value=randint(0, 100),
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                extra_state_attributes={
                    "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                },
            )
        )
    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: entities})
    return entities
