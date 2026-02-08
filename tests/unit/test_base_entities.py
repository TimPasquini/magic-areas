"""Unit tests for base/entities.py."""

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.magic_areas.base.entities import MagicGroupEntity
from custom_components.magic_areas.features import CONF_FEATURE_LIGHT_GROUPS
from custom_components.magic_areas.feature_info import MagicAreasFeatureInfoLightGroups
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN


class MockGroupEntity(MagicGroupEntity):
    """Mock group entity for testing."""

    feature_info = MagicAreasFeatureInfoLightGroups()

    def __init__(self, area, member_entity_ids):
        """Initialize mock group entity."""
        super().__init__(
            area=area,
            domain=LIGHT_DOMAIN,
            member_entity_ids=member_entity_ids,
        )


class TestMagicGroupEntity:
    """Tests for MagicGroupEntity base class."""

    def test_stores_member_entity_ids(self):
        """Should store member entity IDs."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        entity_ids = ["light.one", "light.two"]
        group = MockGroupEntity(area=area, member_entity_ids=entity_ids)
        assert group.member_entity_ids == entity_ids

    def test_initializes_listeners_list(self):
        """Should initialize empty listeners list."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        assert group._group_listeners == []

    async def test_async_added_to_hass_writes_state(self, hass):
        """Should write state when added to hass."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        area.hass = hass
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        group.hass = hass
        group._async_setup_group = AsyncMock()
        group.async_write_ha_state = Mock()

        await group.async_added_to_hass()

        group._async_setup_group.assert_called_once()
        group.async_write_ha_state.assert_called_once()

    async def test_async_will_remove_from_hass_cleans_listeners(self, hass):
        """Should clean up tracked listeners on removal."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        area.hass = hass
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        group.hass = hass
        group._attr_name = "Test Group"  # Mock name to avoid platform_data access

        # Track some listeners
        remove_callback_1 = Mock()
        remove_callback_2 = Mock()
        group.track_group_listener(remove_callback_1, "listener_1")
        group.track_group_listener(remove_callback_2, "listener_2")

        assert len(group._group_listeners) == 2

        # Mock the teardown hook
        group._async_teardown_group = AsyncMock()

        # Remove from hass
        await group.async_will_remove_from_hass()

        # Should have called remove callbacks
        remove_callback_1.assert_called_once()
        remove_callback_2.assert_called_once()

        # Should have cleared listeners
        assert len(group._group_listeners) == 0

        # Should have called teardown hook
        group._async_teardown_group.assert_called_once()

    def test_track_group_listener_stores_callback(self):
        """Should store listener callback for cleanup."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        group._attr_name = "Test Group"  # Mock name to avoid platform_data access

        remove_callback = Mock()
        group.track_group_listener(remove_callback, "test_listener")

        assert len(group._group_listeners) == 1
        assert group._group_listeners[0] == ("test_listener", remove_callback)

    def test_track_group_listener_multiple_callbacks(self):
        """Should track multiple listener callbacks."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        group._attr_name = "Test Group"  # Mock name to avoid platform_data access

        remove_callback_1 = Mock()
        remove_callback_2 = Mock()
        remove_callback_3 = Mock()

        group.track_group_listener(remove_callback_1, "listener_1")
        group.track_group_listener(remove_callback_2, "listener_2")
        group.track_group_listener(remove_callback_3, "listener_3")

        assert len(group._group_listeners) == 3

    async def test_listener_cleanup_handles_exceptions(self, hass):
        """Should handle exceptions during listener cleanup gracefully."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        area.hass = hass
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        group.hass = hass
        group.name = "Test Group"

        # Track a listener that will raise an exception
        failing_callback = Mock(side_effect=Exception("Cleanup failed"))
        working_callback = Mock()

        group.track_group_listener(failing_callback, "failing_listener")
        group.track_group_listener(working_callback, "working_listener")

        # Mock the teardown hook
        group._async_teardown_group = AsyncMock()

        # Should not raise exception
        await group.async_will_remove_from_hass()

        # Both should have been attempted
        failing_callback.assert_called_once()
        working_callback.assert_called_once()

        # Should still clear the list
        assert len(group._group_listeners) == 0

    async def test_setup_hook_called_during_setup(self, hass):
        """Should call _async_setup_group hook during setup."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        area.hass = hass
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        group.hass = hass

        setup_hook_called = False

        async def mock_setup():
            nonlocal setup_hook_called
            setup_hook_called = True

        group._async_setup_group = mock_setup
        group.async_write_ha_state = Mock()

        await group.async_added_to_hass()

        assert setup_hook_called is True

    async def test_teardown_hook_called_during_teardown(self, hass):
        """Should call _async_teardown_group hook during teardown."""
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        area.hass = hass
        group = MockGroupEntity(area=area, member_entity_ids=["light.one"])
        group.hass = hass

        teardown_hook_called = False

        async def mock_teardown():
            nonlocal teardown_hook_called
            teardown_hook_called = True

        group._async_teardown_group = mock_teardown

        await group.async_will_remove_from_hass()

        assert teardown_hook_called is True


class TestMagicEntityFeatureConfig:
    """Tests for MagicEntity.get_feature_config()."""

    def test_reads_from_coordinator_when_available(self):
        """Should prefer coordinator snapshot over area method."""
        from unittest.mock import Mock

        # Setup area with coordinator
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        config_entry = Mock()
        runtime_data = Mock()
        coordinator = Mock()
        coordinator.data = Mock()
        coordinator.data.feature_configs = {
            CONF_FEATURE_LIGHT_GROUPS: {"key": "snapshot_value"}
        }
        runtime_data.coordinator = coordinator
        config_entry.runtime_data = runtime_data
        area.hass_config = config_entry

        # Create entity
        entity = MockGroupEntity(area, member_entity_ids=["light.one"])
        entity._attr_name = "Test Group"  # Mock name

        # Should read from coordinator
        config = entity.get_feature_config()
        assert config == {"key": "snapshot_value"}

    def test_falls_back_to_area_when_coordinator_unavailable(self):
        """Should fall back to area.feature_config() when coordinator not ready."""
        from unittest.mock import Mock

        # Setup area without coordinator
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        area.hass_config = None
        area.feature_config.return_value = {"key": "area_value"}

        # Create entity
        entity = MockGroupEntity(area, member_entity_ids=["light.one"])

        # Should fall back to area method
        config = entity.get_feature_config()
        assert config == {"key": "area_value"}
        area.feature_config.assert_called_once_with(CONF_FEATURE_LIGHT_GROUPS)

    def test_returns_empty_dict_when_feature_not_in_snapshot(self):
        """Should return empty dict when feature not in coordinator snapshot."""
        from unittest.mock import Mock

        # Setup area with coordinator but no feature config
        area = Mock()
        area.id = "test_area"
        area.slug = "test_area"
        area.name = "Test Area"
        config_entry = Mock()
        runtime_data = Mock()
        coordinator = Mock()
        coordinator.data = Mock()
        coordinator.data.feature_configs = {}  # Empty - no light_groups config
        runtime_data.coordinator = coordinator
        config_entry.runtime_data = runtime_data
        area.hass_config = config_entry

        # Create entity
        entity = MockGroupEntity(area, member_entity_ids=["light.one"])
        entity._attr_name = "Test Group"  # Mock name

        # Should return empty dict
        config = entity.get_feature_config()
        assert config == {}
