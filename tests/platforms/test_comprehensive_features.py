"""Comprehensive platform feature testing to improve coverage."""

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN, BinarySensorDeviceClass
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import LIGHT_LUX
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.config_keys.area import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_ENABLED_FEATURES,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.defaults import DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.entities import setup_mock_entities
from tests.helpers.config_entries import get_basic_config_entry_data
from tests.helpers.lifecycle import (
    init_integration as init_integration_helper,
    shutdown_integration,
)
from tests.mocks import MockSensor, MockBinarySensor


async def test_aggregates_and_health_features_together(
    hass: HomeAssistant,
) -> None:
    """Test platform setup with both aggregation and health features enabled."""
    # Create mock sensors for health monitoring
    health_sensors = [
        MockBinarySensor(
            name="smoke_detector",
            unique_id="smoke_detector",
            device_class=BinarySensorDeviceClass.SMOKE,
        ),
        MockBinarySensor(
            name="co_detector",
            unique_id="co_detector",
            device_class=BinarySensorDeviceClass.CO,
        ),
    ]
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: health_sensors})

    # Create mock illuminance sensors
    illuminance_sensors = [
        MockSensor(
            name=f"illuminance_{i}",
            unique_id=f"illuminance_{i}",
            native_value=300 + (i * 100),
            device_class=SensorDeviceClass.ILLUMINANCE,
            native_unit_of_measurement=LIGHT_LUX,
            unit_of_measurement=LIGHT_LUX,
        )
        for i in range(2)
    ]
    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: illuminance_sensors})

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 600,
        },
        MagicAreasFeatures.HEALTH: {
            CONF_HEALTH_SENSOR_DEVICE_CLASSES: DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
        },
        MagicAreasFeatures.WASP_IN_A_BOX: {},
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Verify setup completed without errors
    assert config_entry.state.value == "loaded"

    await shutdown_integration(hass, [config_entry])


async def test_health_feature_without_health_entities(
    hass: HomeAssistant,
) -> None:
    """Test health feature when no health sensor entities exist."""
    # Create non-health sensors
    temp_sensors = [
        MockSensor(
            name="temperature",
            unique_id="temperature",
            native_value=20.0,
            device_class=SensorDeviceClass.TEMPERATURE,
        )
    ]
    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: temp_sensors})

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.HEALTH: {
            CONF_HEALTH_SENSOR_DEVICE_CLASSES: DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Health feature enabled but no matching health sensors - setup should still succeed
    assert config_entry.state.value == "loaded"

    await shutdown_integration(hass, [config_entry])


async def test_wasp_feature_requires_aggregation(
    hass: HomeAssistant,
) -> None:
    """Test that wasp-in-a-box requires aggregation feature."""
    # Create motion sensors
    motion_sensors = [
        MockBinarySensor(
            name="motion_1",
            unique_id="motion_1",
            device_class=BinarySensorDeviceClass.MOTION,
        ),
        MockBinarySensor(
            name="door_1",
            unique_id="door_1",
            device_class=BinarySensorDeviceClass.DOOR,
        ),
    ]
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: motion_sensors})

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        # Enable wasp WITHOUT aggregation - should not create wasp sensor
        MagicAreasFeatures.WASP_IN_A_BOX: {},
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Wasp sensor should not be created
    wasp_entities = [
        eid
        for eid in hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)
        if "wasp" in eid.lower()
    ]
    assert len(wasp_entities) == 0

    await shutdown_integration(hass, [config_entry])


async def test_aggregation_with_illuminance_threshold_creation(
    hass: HomeAssistant,
) -> None:
    """Test aggregation feature creates illuminance threshold."""
    # Create illuminance sensors
    illuminance_sensors = [
        MockSensor(
            name="illuminance_1",
            unique_id="illuminance_1",
            native_value=500.0,
            device_class=SensorDeviceClass.ILLUMINANCE,
            native_unit_of_measurement=LIGHT_LUX,
            unit_of_measurement=LIGHT_LUX,
        )
    ]
    await setup_mock_entities(hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: illuminance_sensors})

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[CONF_ENABLED_FEATURES] = {
        MagicAreasFeatures.AGGREGATES: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 600,  # Non-zero threshold
        }
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    await init_integration_helper(hass, [config_entry])

    # Threshold sensor should be created
    threshold_entities = [
        eid
        for eid in hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)
        if "threshold" in eid.lower()
    ]
    assert len(threshold_entities) > 0

    await shutdown_integration(hass, [config_entry])
