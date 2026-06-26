"""Unit tests for base/entities.py."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.entity import (
    BinaryMagicEntity,
    MagicEntity,
    MagicGroupEntity,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.core.runtime_model import AreaConfig


class MockGroupEntity(MagicGroupEntity):
    """Mock group entity for testing."""

    feature_id = MagicAreasFeatures.LIGHT_GROUPS

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        member_entity_ids: list[str],
    ) -> None:
        """Initialize mock group entity."""
        super().__init__(
            area_config=area_config,
            coordinator=coordinator,
            domain=LIGHT_DOMAIN,
            member_entity_ids=member_entity_ids,
        )


class MockMagicEntity(MagicEntity):
    """Mock entity for base restore-state contract tests."""

    feature_id = MagicAreasFeatures.LIGHT_GROUPS

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize mock entity."""
        super().__init__(
            area_config=area_config,
            coordinator=coordinator,
            domain=LIGHT_DOMAIN,
        )


class MockBinaryMagicEntity(BinaryMagicEntity):
    """Mock binary entity for base restore-state contract tests."""

    feature_id = MagicAreasFeatures.PRESENCE_TRACKING

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize mock binary entity."""
        super().__init__(
            area_config=area_config,
            coordinator=coordinator,
            domain=BINARY_SENSOR_DOMAIN,
        )


class TestMagicGroupEntity:
    """Tests for MagicGroupEntity base class."""

    def test_magic_entity_exposes_ha_entity_contracts(self) -> None:
        """Base entities are coordinator-driven and identify their area device."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        area_config.is_meta.return_value = False
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None

        entity = MockMagicEntity(area_config, coordinator)

        assert entity.should_poll is False
        assert entity.feature_info.id is MagicAreasFeatures.LIGHT_GROUPS
        assert entity.device_info["identifiers"] == {
            (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}test_area")
        }
        assert entity.device_info["name"] == "Test Area"

    def test_stores_member_entity_ids(self) -> None:
        """Should store member entity IDs."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        entity_ids = ["light.one", "light.two"]
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=entity_ids,
        )
        assert group.member_entity_ids == entity_ids

    def test_initializes_listeners_list(self) -> None:
        """Should initialize empty listener registry."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        assert group._listener_registry.count == 0

    async def test_async_added_to_hass_writes_state(self, hass: HomeAssistant) -> None:
        """Should write state when added to hass."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        group.hass = hass

        with (
            patch.object(
                group, "_async_setup_group", new_callable=AsyncMock
            ) as mock_setup,
            patch.object(
                group, "async_write_ha_state", new_callable=Mock
            ) as mock_write,
        ):
            await group.async_added_to_hass()

            mock_setup.assert_called_once()
            mock_write.assert_called_once()

    async def test_async_will_remove_from_hass_cleans_listeners(
        self, hass: HomeAssistant
    ) -> None:
        """Should clean up tracked listeners on removal."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        group.hass = hass
        group._attr_name = "Test Group"  # Mock name to avoid platform_data access

        # Track some listeners
        remove_callback_1 = Mock()
        remove_callback_2 = Mock()
        group.track_group_listener(remove_callback_1, "listener_1")
        group.track_group_listener(remove_callback_2, "listener_2")

        assert group._listener_registry.count == 2

        # Mock the teardown hook
        with patch.object(
            group, "_async_teardown_group", new_callable=AsyncMock
        ) as mock_teardown:
            # Remove from hass
            await group.async_will_remove_from_hass()

            # Should have called remove callbacks
            remove_callback_1.assert_called_once()
            remove_callback_2.assert_called_once()

            # Should have cleared listeners
            assert group._listener_registry.count == 0

            # Should have called teardown hook
            mock_teardown.assert_called_once()

    def test_track_group_listener_stores_callback(self) -> None:
        """Should store listener callback for cleanup."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        group._attr_name = "Test Group"  # Mock name to avoid platform_data access

        remove_callback = Mock()
        group.track_group_listener(remove_callback, "test_listener")

        assert group._listener_registry.count == 1

    def test_track_group_listener_multiple_callbacks(self) -> None:
        """Should track multiple listener callbacks."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        group._attr_name = "Test Group"  # Mock name to avoid platform_data access

        remove_callback_1 = Mock()
        remove_callback_2 = Mock()
        remove_callback_3 = Mock()

        group.track_group_listener(remove_callback_1, "listener_1")
        group.track_group_listener(remove_callback_2, "listener_2")
        group.track_group_listener(remove_callback_3, "listener_3")

        assert group._listener_registry.count == 3

    async def test_listener_cleanup_handles_exceptions(
        self, hass: HomeAssistant
    ) -> None:
        """Should handle exceptions during listener cleanup gracefully."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        group.hass = hass
        group.name = "Test Group"

        # Track a listener that will raise an exception
        failing_callback = Mock(side_effect=RuntimeError("Cleanup failed"))
        working_callback = Mock()

        group.track_group_listener(failing_callback, "failing_listener")
        group.track_group_listener(working_callback, "working_listener")

        # Mock the teardown hook
        with patch.object(group, "_async_teardown_group", new_callable=AsyncMock):
            # Should not raise exception
            await group.async_will_remove_from_hass()

        # Both should have been attempted
        failing_callback.assert_called_once()
        working_callback.assert_called_once()

        # Should still clear the listener registry
        assert group._listener_registry.count == 0

    async def test_setup_hook_called_during_setup(self, hass: HomeAssistant) -> None:
        """Should call _async_setup_group hook during setup."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        group.hass = hass

        setup_hook_called = False

        async def mock_setup() -> None:
            nonlocal setup_hook_called
            setup_hook_called = True

        with (
            patch.object(group, "_async_setup_group", side_effect=mock_setup),
            patch.object(group, "async_write_ha_state"),
        ):
            await group.async_added_to_hass()

        assert setup_hook_called is True

    async def test_teardown_hook_called_during_teardown(
        self, hass: HomeAssistant
    ) -> None:
        """Should call _async_teardown_group hook during teardown."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        group = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        group.hass = hass

        teardown_hook_called = False

        async def mock_teardown() -> None:
            nonlocal teardown_hook_called
            teardown_hook_called = True

        with patch.object(group, "_async_teardown_group", side_effect=mock_teardown):
            await group.async_will_remove_from_hass()

        assert teardown_hook_called is True


class TestMagicEntityFeatureConfig:
    """Tests for MagicEntity.get_feature_config()."""

    def test_reads_from_coordinator_when_available(self) -> None:
        """Should prefer coordinator snapshot over area method."""
        from unittest.mock import Mock

        # Setup area_config and coordinator with feature config
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = Mock()
        coordinator.data.feature_configs = {
            MagicAreasFeatures.LIGHT_GROUPS: {"key": "snapshot_value"}
        }

        # Create entity
        entity = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        entity._attr_name = "Test Group"  # Mock name

        # Should read from coordinator
        config = entity.get_feature_config()
        assert config == {"key": "snapshot_value"}

    def test_returns_empty_dict_when_coordinator_data_unavailable(self) -> None:
        """Should return empty dict when coordinator data is not available."""
        from unittest.mock import Mock

        # Setup area_config and coordinator without data
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None

        # Create entity
        entity = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )

        # Should return empty dict
        config = entity.get_feature_config()
        assert config == {}


class TestBaseRestoreWriteContracts:
    """Contract tests for base restore helpers."""

    async def test_magic_entity_restore_state_uses_immediate_write(self) -> None:
        """MagicEntity restore_state writes immediately and does not schedule."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        area_config.is_meta.return_value = False
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        entity = MockMagicEntity(area_config, coordinator)
        entity._attr_name = "Test Entity"

        with (
            patch.object(
                entity, "async_get_last_state", new=AsyncMock(return_value=None)
            ),
            patch.object(entity, "async_write_ha_state") as mock_write,
            patch.object(entity, "schedule_update_ha_state") as mock_schedule,
        ):
            await entity.restore_state()

        mock_write.assert_called_once()
        mock_schedule.assert_not_called()

    async def test_binary_magic_entity_restore_state_uses_immediate_write(self) -> None:
        """BinaryMagicEntity restore_state writes immediately and does not schedule."""
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        area_config.is_meta.return_value = False
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = None
        entity = MockBinaryMagicEntity(area_config, coordinator)
        entity._attr_name = "Test Binary Entity"

        with (
            patch.object(
                entity, "async_get_last_state", new=AsyncMock(return_value=None)
            ),
            patch.object(entity, "async_write_ha_state") as mock_write,
            patch.object(entity, "schedule_update_ha_state") as mock_schedule,
        ):
            await entity.restore_state()

        mock_write.assert_called_once()
        mock_schedule.assert_not_called()

    def test_returns_empty_dict_when_feature_not_in_snapshot(self) -> None:
        """Should return empty dict when feature not in coordinator snapshot."""
        from unittest.mock import Mock

        # Setup area_config and coordinator with data but no feature config
        area_config = Mock()
        area_config.id = "test_area"
        area_config.slug = "test_area"
        area_config.name = "Test Area"
        area_config.icon = None
        area_config.hass_config = None
        coordinator = Mock()
        coordinator.last_update_success = True
        coordinator.data = Mock()
        coordinator.data.feature_configs = {}  # Empty - no light_groups config

        # Create entity
        entity = MockGroupEntity(
            area_config=area_config,
            coordinator=coordinator,
            member_entity_ids=["light.one"],
        )
        entity._attr_name = "Test Group"  # Mock name

        # Should return empty dict
        config = entity.get_feature_config()
        assert config == {}
