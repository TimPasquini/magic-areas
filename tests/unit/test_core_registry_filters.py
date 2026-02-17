"""Tests for registry filter factory functions."""

from typing import Any, cast
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EventEntityRegistryUpdatedData
from homeassistant.helpers.device_registry import EventDeviceRegistryUpdatedData
import pytest

from custom_components.magic_areas.core.registry_filters import (
    make_device_registry_filter,
    make_entity_registry_filter,
)


@pytest.fixture
def mock_hass() -> Any:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    return hass


class TestMakeEntityRegistryFilter:
    """Tests for make_entity_registry_filter factory."""

    def test_filter_ignores_magic_areas_entities(self, mock_hass: Any) -> None:
        """Test that Magic Areas' own entities are ignored."""
        filter_func = make_entity_registry_filter(mock_hass, "test_area", "config_id")

        event_data = cast(
            EventEntityRegistryUpdatedData,
            {
                "entity_id": "binary_sensor.magic_areas_presence_tracking_test_area_state",
                "action": "create",
            },
        )

        assert filter_func(event_data) is False

    def test_filter_accepts_entity_added_to_area(self, mock_hass: Any) -> None:
        """Test that entities added to the area are accepted."""
        with patch("custom_components.magic_areas.core.registry_filters.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "test_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_entity_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventEntityRegistryUpdatedData,
                {
                    "entity_id": "light.living_room_light",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is True

    def test_filter_ignores_entity_in_different_area(self, mock_hass: Any) -> None:
        """Test that entities in different areas are ignored."""
        with patch("custom_components.magic_areas.core.registry_filters.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "other_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_entity_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventEntityRegistryUpdatedData,
                {
                    "entity_id": "light.kitchen_light",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is False

    def test_filter_detects_entity_removed_from_area(self, mock_hass: Any) -> None:
        """Test detection when entity is removed from area."""
        with patch("custom_components.magic_areas.core.registry_filters.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry
            mock_registry.async_get.return_value = None

            filter_func = make_entity_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventEntityRegistryUpdatedData,
                {
                    "entity_id": "light.living_room",
                    "action": "update",
                    "changes": {"area_id": "test_area"},
                },
            )

            assert filter_func(event_data) is True

    def test_filter_detects_entity_area_changed_to_this_area(self, mock_hass: Any) -> None:
        """Test detection when entity area changes to this area."""
        with patch("custom_components.magic_areas.core.registry_filters.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "test_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_entity_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventEntityRegistryUpdatedData,
                {
                    "entity_id": "light.bedroom_light",
                    "action": "update",
                    "changes": {"area_id": "other_area"},
                },
            )

            assert filter_func(event_data) is True


class TestMakeDeviceRegistryFilter:
    """Tests for make_device_registry_filter factory."""

    def test_filter_ignores_magic_area_devices(self, mock_hass: Any) -> None:
        """Test that Magic Areas' own devices are ignored."""
        with patch("custom_components.magic_areas.core.registry_filters.devicereg_async_get"):
            filter_func = make_device_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "magic_areas_device_test_area",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is False

    def test_filter_accepts_device_in_area(self, mock_hass: Any) -> None:
        """Test that devices in the area are accepted."""
        with patch("custom_components.magic_areas.core.registry_filters.devicereg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "test_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_device_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "light_device_123",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is True

    def test_filter_ignores_device_in_different_area(self, mock_hass: Any) -> None:
        """Test that devices in different areas are ignored."""
        with patch("custom_components.magic_areas.core.registry_filters.devicereg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "other_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_device_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "device_456",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is False

    def test_filter_detects_device_removed_from_area(self, mock_hass: Any) -> None:
        """Test detection when device is removed from area."""
        with patch("custom_components.magic_areas.core.registry_filters.devicereg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry
            mock_registry.async_get.return_value = None

            filter_func = make_device_registry_filter(mock_hass, "test_area", "config_id")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "device_789",
                    "action": "update",
                    "changes": {"area_id": "test_area"},
                },
            )

            assert filter_func(event_data) is True
