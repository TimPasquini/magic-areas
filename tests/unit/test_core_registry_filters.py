"""Tests for registry filter factory functions."""

from typing import cast
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import (
    EventEntityRegistryUpdatedData,
    _EventEntityRegistryUpdatedData_CreateRemove,
    _EventEntityRegistryUpdatedData_Update,
)
from homeassistant.helpers.device_registry import EventDeviceRegistryUpdatedData
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.coordinator.pipeline import (
    make_device_registry_filter,
    make_entity_registry_filter,
)
from custom_components.magic_areas.coordinator.pipeline.lifecycle import (
    _extract_changed_area_id,
    _merged_area_config_data,
    _runtime_snapshot,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    init_integration as init_integration_helper,
    shutdown_integration,
)


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    return cast(HomeAssistant, hass)


class TestMakeEntityRegistryFilter:
    """Tests for make_entity_registry_filter factory."""

    def test_filter_ignores_magic_areas_entities(self, mock_hass: HomeAssistant) -> None:
        """Test that Magic Areas' own entities are ignored."""
        filter_func = make_entity_registry_filter(mock_hass, "test_area")

        event_data = cast(
            EventEntityRegistryUpdatedData,
            {
                "entity_id": "binary_sensor.magic_areas_presence_tracking_test_area_state",
                "action": "create",
            },
        )

        assert filter_func(event_data) is False

    def test_filter_accepts_entity_added_to_area(self, mock_hass: HomeAssistant) -> None:
        """Test that entities added to the area are accepted."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "test_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_entity_registry_filter(mock_hass, "test_area")

            event_data = cast(
                EventEntityRegistryUpdatedData,
                {
                    "entity_id": "light.living_room_light",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is True

    def test_filter_ignores_entity_in_different_area(self, mock_hass: HomeAssistant) -> None:
        """Test that entities in different areas are ignored."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "other_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_entity_registry_filter(mock_hass, "test_area")

            event_data = cast(
                EventEntityRegistryUpdatedData,
                {
                    "entity_id": "light.kitchen_light",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is False

    def test_filter_detects_entity_removed_from_area(self, mock_hass: HomeAssistant) -> None:
        """Test detection when entity is removed from area."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry
            mock_registry.async_get.return_value = None

            filter_func = make_entity_registry_filter(mock_hass, "test_area")

            event_data = cast(
                EventEntityRegistryUpdatedData,
                {
                    "entity_id": "light.living_room",
                    "action": "update",
                    "changes": {"area_id": "test_area"},
                },
            )

            assert filter_func(event_data) is True

    def test_filter_detects_entity_area_changed_to_this_area(self, mock_hass: HomeAssistant) -> None:
        """Test detection when entity area changes to this area."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.entityreg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "test_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_entity_registry_filter(mock_hass, "test_area")

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

    def test_filter_ignores_magic_area_devices(self, mock_hass: HomeAssistant) -> None:
        """Test that Magic Areas' own devices are ignored."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.devicereg_async_get"):
            filter_func = make_device_registry_filter(mock_hass, "test_area")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "magic_areas_device_test_area",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is False

    def test_filter_accepts_device_in_area(self, mock_hass: HomeAssistant) -> None:
        """Test that devices in the area are accepted."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.devicereg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "test_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_device_registry_filter(mock_hass, "test_area")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "light_device_123",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is True

    def test_filter_ignores_device_in_different_area(self, mock_hass: HomeAssistant) -> None:
        """Test that devices in different areas are ignored."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.devicereg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry

            mock_entry = MagicMock()
            mock_entry.area_id = "other_area"
            mock_registry.async_get.return_value = mock_entry

            filter_func = make_device_registry_filter(mock_hass, "test_area")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "device_456",
                    "action": "create",
                },
            )

            assert filter_func(event_data) is False

    def test_filter_detects_device_removed_from_area(self, mock_hass: HomeAssistant) -> None:
        """Test detection when device is removed from area."""
        with patch("custom_components.magic_areas.coordinator.pipeline.lifecycle.devicereg_async_get") as mock_reg:
            mock_registry = MagicMock()
            mock_reg.return_value = mock_registry
            mock_registry.async_get.return_value = None

            filter_func = make_device_registry_filter(mock_hass, "test_area")

            event_data = cast(
                EventDeviceRegistryUpdatedData,
                {
                    "device_id": "device_789",
                    "action": "update",
                    "changes": {"area_id": "test_area"},
                },
            )

            assert filter_func(event_data) is True


# Integration tests from test_magic.py


async def test_registry_filters_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test registry filters with full integration setup."""
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry is not None
    area_config = entry.runtime_data.coordinator._area_config

    entity_filter = make_entity_registry_filter(hass, area_config.id)

    # Test entity update in area
    event_data: _EventEntityRegistryUpdatedData_Update = cast(
        _EventEntityRegistryUpdatedData_Update,
        {
            "action": "update",
            "entity_id": "light.test",
            "changes": {"area_id": DEFAULT_MOCK_AREA.value},  # Removed from area
        },
    )
    # Mock registry lookup to return None or different area to simulate removal
    with patch(
        "custom_components.magic_areas.coordinator.pipeline.lifecycle.entityreg_async_get"
    ) as mock_er:
        mock_registry_instance = MagicMock()
        mock_er.return_value = mock_registry_instance
        mock_registry_instance.async_get.return_value = (
            None  # Entity not in registry anymore or moved
        )

        assert entity_filter(event_data) is True

    # Test entity create in area
    event_data_create: _EventEntityRegistryUpdatedData_CreateRemove = cast(
        _EventEntityRegistryUpdatedData_CreateRemove,
        {
            "action": "create",
            "entity_id": "light.test_new",
        },
    )
    with patch(
        "custom_components.magic_areas.coordinator.pipeline.lifecycle.entityreg_async_get"
    ) as mock_er:
        mock_registry_instance = MagicMock()
        mock_er.return_value = mock_registry_instance
        mock_entry = MagicMock()
        mock_entry.area_id = DEFAULT_MOCK_AREA.value
        mock_registry_instance.async_get.return_value = mock_entry

        assert entity_filter(event_data_create) is True

    await shutdown_integration(hass, [mock_config_entry])


def test_extract_changed_area_id_helper() -> None:
    """Changed-area extraction should normalize optional payloads."""
    assert _extract_changed_area_id({"area_id": "kitchen"}) == "kitchen"
    assert _extract_changed_area_id({"area_id": None}) is None
    assert _extract_changed_area_id({"area_id": 123}) is None
    assert _extract_changed_area_id(None) is None


def test_merged_area_config_data_prefers_options() -> None:
    """Merged area config should overlay options onto base data."""
    config_entry = MagicMock()
    config_entry.data = {"name": "Kitchen", "reload_on_registry_change": True}
    config_entry.options = {"reload_on_registry_change": False}

    merged = _merged_area_config_data(config_entry)

    assert merged["name"] == "Kitchen"
    assert merged["reload_on_registry_change"] is False


def test_runtime_snapshot_helper_handles_missing_runtime_data() -> None:
    """Runtime snapshot helper should return None when runtime_data absent."""
    config_entry = MagicMock()
    config_entry.runtime_data = None

    assert _runtime_snapshot(config_entry) is None
