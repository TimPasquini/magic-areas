"""Tests for entity loading and filtering functions."""

from datetime import UTC, datetime

import pytest
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_registry import RegistryEntry, RegistryEntryDisabler

from custom_components.magic_areas.coordinator.pipeline import (
    filter_entity_list,
    is_magic_area_entity,
    should_exclude_entity,
)


def create_mock_entity(
    entity_id: str = "sensor.temperature",
    unique_id: str = "temp_sensor_123",
    config_entry_id: str = "config_entry_123",
    disabled_by: RegistryEntryDisabler | None = None,
    entity_category: EntityCategory | None = None,
) -> RegistryEntry:
    """Create a mock entity registry entry."""
    now = datetime.now(UTC)
    return RegistryEntry(
        entity_id=entity_id,
        unique_id=unique_id,
        platform="test",
        previous_unique_id=None,
        area_id=None,
        capabilities=None,
        config_entry_id=config_entry_id,
        config_subentry_id=None,
        created_at=now,
        device_class=None,
        device_id=None,
        disabled_by=disabled_by,
        entity_category=entity_category,
        has_entity_name=False,
        hidden_by=None,
        id=f"{unique_id}_id",
        name=None,
        options=None,
        original_device_class=None,
        original_icon=None,
        original_name=None,
        suggested_object_id=None,
        supported_features=0,
        translation_key=None,
        unit_of_measurement=None,
    )


@pytest.fixture
def mock_entity() -> RegistryEntry:
    """Create a mock entity registry entry."""
    return create_mock_entity()


@pytest.fixture
def magic_entity() -> RegistryEntry:
    """Create a magic area entity registry entry."""
    return create_mock_entity(
        entity_id="binary_sensor.presence_tracking_kitchen_area_state",
        unique_id="presence_tracking_kitchen_area_state",
        config_entry_id="magic_config_entry",
    )


@pytest.fixture
def disabled_entity() -> RegistryEntry:
    """Create a disabled entity registry entry."""
    return create_mock_entity(
        entity_id="sensor.humidity",
        unique_id="humidity_sensor_456",
        disabled_by=RegistryEntryDisabler.USER,
    )


@pytest.fixture
def diagnostic_entity() -> RegistryEntry:
    """Create a diagnostic entity registry entry."""
    return create_mock_entity(
        entity_id="sensor.device_info",
        unique_id="device_info_789",
        entity_category=EntityCategory.DIAGNOSTIC,
    )


@pytest.fixture
def config_entity() -> RegistryEntry:
    """Create a config entity registry entry."""
    return create_mock_entity(
        entity_id="number.mqtt_interval",
        unique_id="mqtt_interval_abc",
        entity_category=EntityCategory.CONFIG,
    )


class TestIsMagicAreaEntity:
    """Tests for is_magic_area_entity function."""

    def test_is_magic_area_entity_match(self, mock_entity: RegistryEntry) -> None:
        """Test entity with matching config entry ID."""
        assert is_magic_area_entity(mock_entity, "config_entry_123") is True

    def test_is_magic_area_entity_no_match(self, mock_entity: RegistryEntry) -> None:
        """Test entity with non-matching config entry ID."""
        assert is_magic_area_entity(mock_entity, "different_config_entry") is False

    def test_is_magic_area_entity_magic_area(self, magic_entity: RegistryEntry) -> None:
        """Test magic area entity."""
        assert is_magic_area_entity(magic_entity, "magic_config_entry") is True


class TestShouldExcludeEntity:
    """Tests for should_exclude_entity function."""

    def test_should_exclude_magic_area_entity(self, magic_entity: RegistryEntry) -> None:
        """Test that magic area entities are excluded."""
        assert should_exclude_entity(magic_entity, "magic_config_entry") is True

    def test_should_exclude_disabled_entity(self, disabled_entity: RegistryEntry) -> None:
        """Test that disabled entities are excluded."""
        assert should_exclude_entity(disabled_entity, "different_config") is True

    def test_should_exclude_entity_in_exclude_list(
        self, mock_entity: RegistryEntry
    ) -> None:
        """Test that entities in exclude list are excluded."""
        exclude_list = ["sensor.temperature", "sensor.humidity"]
        assert (
            should_exclude_entity(
                mock_entity,
                "different_config",
                exclude_list=exclude_list,
            )
            is True
        )

    def test_should_not_exclude_entity_not_in_exclude_list(
        self, mock_entity: RegistryEntry
    ) -> None:
        """Test that entities not in exclude list are not excluded."""
        exclude_list = ["sensor.humidity", "sensor.pressure"]
        assert (
            should_exclude_entity(
                mock_entity,
                "different_config",
                exclude_list=exclude_list,
            )
            is False
        )

    def test_should_exclude_diagnostic_entity(
        self, diagnostic_entity: RegistryEntry
    ) -> None:
        """Test that diagnostic entities are excluded when enabled."""
        assert (
            should_exclude_entity(
                diagnostic_entity,
                "different_config",
                ignore_diagnostic=True,
            )
            is True
        )

    def test_should_not_exclude_diagnostic_entity_when_disabled(
        self, diagnostic_entity: RegistryEntry
    ) -> None:
        """Test that diagnostic entities are not excluded when disabled."""
        assert (
            should_exclude_entity(
                diagnostic_entity,
                "different_config",
                ignore_diagnostic=False,
            )
            is False
        )

    def test_should_exclude_config_entity(self, config_entity: RegistryEntry) -> None:
        """Test that config entities are excluded when enabled."""
        assert (
            should_exclude_entity(
                config_entity,
                "different_config",
                ignore_diagnostic=True,
            )
            is True
        )

    def test_should_not_exclude_config_entity_when_disabled(
        self, config_entity: RegistryEntry
    ) -> None:
        """Test that config entities are not excluded when disabled."""
        assert (
            should_exclude_entity(
                config_entity,
                "different_config",
                ignore_diagnostic=False,
            )
            is False
        )

    def test_should_exclude_with_default_ignore_diagnostic(
        self, diagnostic_entity: RegistryEntry
    ) -> None:
        """Test that diagnostic exclusion defaults to True."""
        assert should_exclude_entity(diagnostic_entity, "different_config") is True

    def test_should_exclude_multiple_criteria(
        self, disabled_entity: RegistryEntry
    ) -> None:
        """Test exclusion with multiple criteria met."""
        exclude_list = ["sensor.humidity"]
        assert (
            should_exclude_entity(
                disabled_entity,
                "different_config",
                exclude_list=exclude_list,
            )
            is True
        )


class TestFilterEntityList:
    """Tests for filter_entity_list function."""

    def test_filter_entity_list_empty(self) -> None:
        """Test filtering empty list."""
        result = filter_entity_list([], "config_entry_123")
        assert result == []

    def test_filter_entity_list_no_exclusions(self, mock_entity: RegistryEntry) -> None:
        """Test filtering with no exclusions applied."""
        entity_list = [mock_entity]
        result = filter_entity_list(entity_list, "different_config")
        assert len(result) == 1
        assert result[0] == mock_entity

    def test_filter_entity_list_exclude_magic_area(
        self, mock_entity: RegistryEntry, magic_entity: RegistryEntry
    ) -> None:
        """Test filtering excludes magic area entities."""
        entity_list = [mock_entity, magic_entity]
        result = filter_entity_list(entity_list, "magic_config_entry")
        assert len(result) == 1
        assert result[0] == mock_entity

    def test_filter_entity_list_exclude_disabled(
        self, mock_entity: RegistryEntry, disabled_entity: RegistryEntry
    ) -> None:
        """Test filtering excludes disabled entities."""
        entity_list = [mock_entity, disabled_entity]
        result = filter_entity_list(entity_list, "different_config")
        assert len(result) == 1
        assert result[0] == mock_entity

    def test_filter_entity_list_exclude_by_list(self, mock_entity: RegistryEntry) -> None:
        """Test filtering with entity ID exclude list."""
        entity_list = [mock_entity]
        result = filter_entity_list(
            entity_list,
            "different_config",
            exclude_list=["sensor.temperature"],
        )
        assert result == []

    def test_filter_entity_list_exclude_diagnostic(
        self, mock_entity: RegistryEntry, diagnostic_entity: RegistryEntry
    ) -> None:
        """Test filtering excludes diagnostic entities."""
        entity_list = [mock_entity, diagnostic_entity]
        result = filter_entity_list(entity_list, "different_config")
        assert len(result) == 1
        assert result[0] == mock_entity

    def test_filter_entity_list_keep_diagnostic_when_disabled(
        self, mock_entity: RegistryEntry, diagnostic_entity: RegistryEntry
    ) -> None:
        """Test filtering keeps diagnostic entities when ignore is disabled."""
        entity_list = [mock_entity, diagnostic_entity]
        result = filter_entity_list(
            entity_list,
            "different_config",
            ignore_diagnostic=False,
        )
        assert len(result) == 2
        assert diagnostic_entity in result

    def test_filter_entity_list_multiple_exclusions(
        self,
        mock_entity: RegistryEntry,
        magic_entity: RegistryEntry,
        disabled_entity: RegistryEntry,
        diagnostic_entity: RegistryEntry,
    ) -> None:
        """Test filtering with multiple exclusion criteria."""
        entity_list = [mock_entity, magic_entity, disabled_entity, diagnostic_entity]
        result = filter_entity_list(
            entity_list,
            "magic_config_entry",
            exclude_list=["sensor.temperature"],
        )
        assert result == []

