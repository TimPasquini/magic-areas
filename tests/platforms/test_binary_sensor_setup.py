"""Test binary_sensor platform setup with coordinator data conditions."""

from collections.abc import Iterable
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.binary_sensor import (
    async_setup_entry,
    create_aggregate_sensors_from_definitions,
    create_wasp_in_a_box_sensor,
    create_ble_tracker_sensor,
)
from custom_components.magic_areas.core.aggregates import AggregateDefinition, AggregateKind
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
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
    async def set_data_none() -> None:
        mock_coordinator.data = None

    mock_coordinator.async_refresh.side_effect = set_data_none

    mock_runtime_data = MagicMock()
    mock_runtime_data.coordinator = mock_coordinator

    config_entry.runtime_data = mock_runtime_data

    # Call async_setup_entry with no entities added
    added_entities: list[list[Entity]] = []

    def async_add_entities(
        new_entities: Iterable[Entity], update_before_add: bool = False
    ) -> None:
        del update_before_add
        added_entities.append(list(new_entities))

    # Call the function
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify that async_refresh was called (line 82)
    mock_coordinator.async_refresh.assert_called_once()

    # Verify that no entities were added (because data remained None)
    assert added_entities == []


def test_create_wasp_in_a_box_sensor_returns_empty_when_aggregation_disabled() -> None:
    """Test that create_wasp_in_a_box_sensor returns empty list when aggregation disabled."""
    # Create mock data with wasp enabled but aggregation disabled
    mock_data = MagicMock()
    mock_data.enabled_features = {MagicAreasFeatures.WASP_IN_A_BOX}  # Wasp enabled
    # Aggregation NOT enabled
    mock_data.feature_configs = {}

    # Create mock area_config and coordinator
    mock_area_config = MagicMock()
    mock_area_config.slug = "test"
    mock_coordinator = MagicMock()

    # Call the function
    result = create_wasp_in_a_box_sensor(mock_data, mock_area_config, mock_coordinator)

    # Should return empty list (line 139)
    assert result == []
    assert isinstance(result, list)


def test_create_ble_tracker_sensor_returns_empty_when_feature_disabled() -> None:
    """Test that create_ble_tracker_sensor returns empty list when feature disabled."""
    # Create mock data with BLE trackers feature disabled
    mock_data = MagicMock()
    mock_data.enabled_features = set()  # No features enabled
    mock_data.feature_configs = {}

    # Create mock area_config and coordinator
    mock_area_config = MagicMock()
    mock_area_config.slug = "test"
    mock_coordinator = MagicMock()

    # Call the function
    result = create_ble_tracker_sensor(mock_data, mock_area_config, mock_coordinator)

    # Should return empty list (line 158)
    assert result == []
    assert isinstance(result, list)


def test_create_aggregate_sensors_handles_exception_during_creation() -> None:
    """Test aggregate creation handles exceptions during entity construction."""
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass

    # Create mock data
    mock_area_config = MagicMock()
    mock_area_config.slug = "test_area"

    mock_coordinator = MagicMock()

    definitions = [
        AggregateDefinition(
            domain="binary_sensor",
            device_class=BinarySensorDeviceClass.MOTION,
            entity_ids=("binary_sensor.motion_1", "binary_sensor.motion_2"),
            kind=AggregateKind.STANDARD,
        )
    ]

    # Patch AreaAggregateBinarySensor to raise an exception
    with patch(
        "custom_components.magic_areas.binary_sensor.aggregate_factory.AreaAggregateBinarySensor",
        side_effect=RuntimeError("Test exception"),
    ):
        result = create_aggregate_sensors_from_definitions(
            definitions=definitions,
            area_config=mock_area_config,
            coordinator=mock_coordinator,
        )

    # Should return empty list (exception was caught, no sensors created)
    assert result == []
    assert isinstance(result, list)
