"""Test binary_sensor platform setup with coordinator data conditions."""

from collections.abc import Iterable
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.binary_sensor import (
    _build_platform_base_entities,
    async_setup_entry,
    create_wasp_in_a_box_sensor,
    create_ble_tracker_sensor,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers.config_entries import get_basic_config_entry_data


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


def test_build_platform_base_entities_selects_meta_area_sensor() -> None:
    """Meta-area setup should build only the meta-area state sensor."""
    area_config = MagicMock()
    area_config.is_meta.return_value = True
    coordinator = MagicMock()
    data = MagicMock()
    meta_entity = MagicMock(spec=Entity)

    with (
        patch(
            "custom_components.magic_areas.binary_sensor.MetaAreaStateBinarySensor",
            return_value=meta_entity,
        ) as meta_sensor,
        patch(
            "custom_components.magic_areas.binary_sensor.AreaStateBinarySensor"
        ) as area_sensor,
    ):
        entities = _build_platform_base_entities(area_config, coordinator, data)

    assert entities == [meta_entity]
    meta_sensor.assert_called_once_with(area_config, coordinator)
    area_sensor.assert_not_called()
