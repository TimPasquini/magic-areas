"""Contract tests for presence entity write behavior."""

from unittest.mock import MagicMock, Mock, patch

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.binary_sensor.presence import AreaStateBinarySensor


def _area_config() -> Mock:
    area_config = Mock()
    area_config.id = "kitchen"
    area_config.slug = "kitchen"
    area_config.name = "Kitchen"
    area_config.icon = None
    area_config.config = {}
    area_config.is_meta.return_value = False
    return area_config


def _coordinator() -> Mock:
    coordinator = Mock()
    coordinator.hass = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = Mock()
    coordinator.data.presence_sensors = ["binary_sensor.motion_1"]
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    return coordinator


def test_area_state_changed_uses_scheduled_write_path() -> None:
    """Dispatcher-driven area state changes keep scheduler writes."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}

    with (
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        entity._area_state_changed(
            "kitchen",
            ([AreaStates.OCCUPIED.value], [], [AreaStates.OCCUPIED.value]),
        )

    mock_schedule.assert_called_once()
    mock_write.assert_not_called()


def test_coordinator_update_uses_scheduled_write_path() -> None:
    """Coordinator refresh listener keeps scheduler writes."""
    coordinator = _coordinator()
    entity = AreaStateBinarySensor(_area_config(), coordinator)
    entity._attr_extra_state_attributes = {}
    entity._sensors = []
    coordinator.data.presence_sensors = ["binary_sensor.motion_1"]

    with (
        patch.object(entity, "_track_presence_sensor_listener") as mock_track,
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        entity._handle_coordinator_update()

    mock_track.assert_called_once_with(["binary_sensor.motion_1"])
    mock_schedule.assert_called_once()
    mock_write.assert_not_called()


def test_apply_state_projection_updates_cached_state_and_attributes() -> None:
    """Projection helper owns binary state refresh from current states."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}

    entity._apply_state_projection([AreaStates.OCCUPIED.value])

    assert entity._current_states == [AreaStates.OCCUPIED.value]
    assert entity._attr_is_on is True
    assert entity._attr_extra_state_attributes["states"] == [
        AreaStates.OCCUPIED.value
    ]


def test_apply_sensor_inventory_update_tracks_added_sensors() -> None:
    """Inventory helper owns snapshot-driven presence sensor reconciliation."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}
    entity._sensors = []

    with patch.object(entity, "_track_presence_sensor_listener") as mock_track:
        entity._apply_sensor_inventory_update(["binary_sensor.motion_1"])

    assert entity._sensors == ["binary_sensor.motion_1"]
    mock_track.assert_called_once_with(["binary_sensor.motion_1"])
