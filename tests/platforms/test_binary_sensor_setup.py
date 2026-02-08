"""Test binary_sensor platform setup with coordinator data conditions."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.binary_sensor import (
    async_setup_entry,
    create_wasp_in_a_box_sensor,
    create_ble_tracker_sensor,
    create_health_sensors,
    create_aggregate_sensors,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.features import (
    CONF_FEATURE_WASP_IN_A_BOX,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_HEALTH,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import get_basic_config_entry_data


@pytest.mark.asyncio
async def test_binary_sensor_setup_calls_refresh_when_coordinator_data_none(
    hass: HomeAssistant,
) -> None:
    """Test that async_setup_entry calls coordinator.async_refresh() when data is None."""
    # Create a mock config entry
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    # Create mock runtime_data with coordinator that has None data
    mock_coordinator = AsyncMock()
    mock_coordinator.data = None  # Initially None
    mock_coordinator.async_refresh = AsyncMock()

    # After refresh, still None (to test the second check)
    mock_coordinator.async_refresh.side_effect = lambda: (
        setattr(mock_coordinator, 'data', None),  # Keep it None after refresh
        None
    )

    mock_runtime_data = MagicMock()
    mock_runtime_data.coordinator = mock_coordinator

    config_entry.runtime_data = mock_runtime_data

    # Call async_setup_entry with no entities added
    async_add_entities: AddEntitiesCallback = AsyncMock()

    # Call the function
    result = await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify that async_refresh was called (line 82)
    mock_coordinator.async_refresh.assert_called_once()

    # Verify that no entities were added (because data remained None)
    async_add_entities.assert_not_called()

    # Result should be None (early return at line 86)
    assert result is None


def test_create_wasp_in_a_box_sensor_returns_empty_when_aggregation_disabled() -> None:
    """Test that create_wasp_in_a_box_sensor returns empty list when aggregation disabled."""
    # Create mock data with wasp enabled but aggregation disabled
    mock_data = MagicMock()
    mock_data.enabled_features = {CONF_FEATURE_WASP_IN_A_BOX}  # Wasp enabled
    # Aggregation NOT enabled
    mock_data.feature_configs = {}

    # Call the function
    result = create_wasp_in_a_box_sensor(mock_data)

    # Should return empty list (line 139)
    assert result == []
    assert isinstance(result, list)


def test_create_ble_tracker_sensor_returns_empty_when_feature_disabled() -> None:
    """Test that create_ble_tracker_sensor returns empty list when feature disabled."""
    # Create mock data with BLE trackers feature disabled
    mock_data = MagicMock()
    mock_data.enabled_features = set()  # No features enabled
    mock_data.feature_configs = {}

    # Call the function
    result = create_ble_tracker_sensor(mock_data)

    # Should return empty list (line 158)
    assert result == []
    assert isinstance(result, list)


def test_create_health_sensors_returns_empty_when_feature_disabled() -> None:
    """Test that create_health_sensors returns empty list when health feature disabled."""
    # Create mock data with health feature disabled
    mock_data = MagicMock()
    mock_data.enabled_features = set()  # No features enabled
    mock_data.feature_configs = {}

    # Call the function
    result = create_health_sensors(mock_data, {})

    # Should return empty list (line 186)
    assert result == []
    assert isinstance(result, list)


def test_create_health_sensors_handles_exception_during_creation() -> None:
    """Test that create_health_sensors handles exceptions during sensor creation."""
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass

    # Create mock data with health feature enabled and a health sensor
    mock_area = MagicMock()
    mock_area.slug = "test_area"
    mock_area.name = "Test Area"

    mock_data = MagicMock()
    mock_data.enabled_features = {CONF_FEATURE_HEALTH}
    mock_data.feature_configs = {CONF_FEATURE_HEALTH: {}}
    mock_data.area = mock_area

    # Create entities with a health sensor
    entities_by_domain = {
        "binary_sensor": [
            {
                "entity_id": "binary_sensor.smoke",
                "device_class": BinarySensorDeviceClass.SMOKE,
            }
        ]
    }

    # Patch AreaHealthBinarySensor to raise an exception
    with patch(
        "custom_components.magic_areas.binary_sensor.AreaHealthBinarySensor",
        side_effect=Exception("Test exception"),
    ):
        result = create_health_sensors(mock_data, entities_by_domain)

    # Should return empty list after catching exception (lines 228-234)
    assert result == []
    assert isinstance(result, list)


def test_create_aggregate_sensors_handles_exception_during_creation() -> None:
    """Test that create_aggregate_sensors handles exceptions during sensor creation."""
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass
    from custom_components.magic_areas.config_keys import CONF_AGGREGATES_MIN_ENTITIES

    # Create mock data
    mock_area = MagicMock()
    mock_area.slug = "test_area"

    mock_data = MagicMock()
    mock_data.area = mock_area
    mock_data.enabled_features = {CONF_FEATURE_AGGREGATION}
    # Configure aggregation with min 1 entity
    mock_data.feature_configs = {
        CONF_FEATURE_AGGREGATION: {
            CONF_AGGREGATES_MIN_ENTITIES: 1,
        }
    }

    # Create entities with binary sensors for aggregation
    entities_by_domain = {
        "binary_sensor": [
            {
                "entity_id": "binary_sensor.motion_1",
                "device_class": BinarySensorDeviceClass.MOTION,
            },
            {
                "entity_id": "binary_sensor.motion_2",
                "device_class": BinarySensorDeviceClass.MOTION,
            },
        ]
    }

    # Patch AreaAggregateBinarySensor to raise an exception
    with patch(
        "custom_components.magic_areas.binary_sensor.AreaAggregateBinarySensor",
        side_effect=Exception("Test exception"),
    ):
        result = create_aggregate_sensors(mock_data, entities_by_domain)

    # Should return empty list (exception was caught, no sensors created)
    assert result == []
    assert isinstance(result, list)
