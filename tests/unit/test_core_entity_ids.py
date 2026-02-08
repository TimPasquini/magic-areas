"""Unit tests for core.entity_ids module."""

from unittest.mock import MagicMock

from custom_components.magic_areas.core.entity_ids import (
    EntityReferences,
    build_entity_references,
)


def _make_registry(*entries: tuple[str, str, str, str]) -> MagicMock:
    """Create a mock entity registry with given entries.

    Each entry is (entity_id, domain, platform, unique_id).
    """
    registry = MagicMock()

    # Build the lookup dict: (domain, platform, unique_id) -> entity_id
    lookup: dict[tuple[str, str, str], str] = {}
    mock_entries = []

    for entity_id, domain, platform, unique_id in entries:
        lookup[(domain, platform, unique_id)] = entity_id

        entry = MagicMock()
        entry.entity_id = entity_id
        entry.domain = domain
        entry.platform = platform
        entry.unique_id = unique_id
        mock_entries.append(entry)

    registry.async_get_entity_id = MagicMock(
        side_effect=lambda d, p, u: lookup.get((d, p, u))
    )
    registry.entities.values = MagicMock(return_value=mock_entries)

    return registry


def test_build_entity_references_empty_registry() -> None:
    """Test build_entity_references with empty entity registry."""
    registry = _make_registry()
    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert refs.area_state_sensor is None
    assert refs.presence_hold_switch is None
    assert len(refs.aggregates_by_device_class) == 0
    assert len(refs.binary_aggregates_by_device_class) == 0
    assert refs.light_control_switch is None
    assert len(refs.light_groups_by_category) == 0
    assert refs.fan_group is None
    assert refs.fan_control_switch is None
    assert refs.media_player_group is None
    assert refs.media_player_control_switch is None
    assert refs.climate_control_switch is None
    assert refs.cover_group is None
    assert refs.wasp_in_a_box_sensor is None
    assert refs.ble_tracker_monitor is None
    assert refs.threshold_sensor is None
    assert refs.health_sensor is None


def test_build_entity_references_presence_tracking() -> None:
    """Test resolving presence tracking sensors."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
            "binary_sensor",
            "magic_areas",
            "presence_tracking_kitchen_area_state",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.area_state_sensor
        == "binary_sensor.magic_areas_presence_tracking_kitchen_area_state"
    )


def test_build_entity_references_presence_hold() -> None:
    """Test resolving presence hold switch."""
    registry = _make_registry(
        (
            "switch.magic_areas_presence_hold_kitchen",
            "switch",
            "magic_areas",
            "presence_hold_kitchen",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert refs.presence_hold_switch == "switch.magic_areas_presence_hold_kitchen"


def test_build_entity_references_sensor_aggregates() -> None:
    """Test resolving sensor aggregates by device class."""
    registry = _make_registry(
        (
            "sensor.magic_areas_aggregates_kitchen_aggregate_temperature",
            "sensor",
            "magic_areas",
            "aggregates_kitchen_aggregate_temperature",
        ),
        (
            "sensor.magic_areas_aggregates_kitchen_aggregate_humidity",
            "sensor",
            "magic_areas",
            "aggregates_kitchen_aggregate_humidity",
        ),
        # Different area - should be ignored
        (
            "sensor.magic_areas_aggregates_living_room_aggregate_temperature",
            "sensor",
            "magic_areas",
            "aggregates_living_room_aggregate_temperature",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert len(refs.aggregates_by_device_class) == 2
    assert (
        refs.aggregates_by_device_class["temperature"]
        == "sensor.magic_areas_aggregates_kitchen_aggregate_temperature"
    )
    assert (
        refs.aggregates_by_device_class["humidity"]
        == "sensor.magic_areas_aggregates_kitchen_aggregate_humidity"
    )


def test_build_entity_references_binary_aggregates() -> None:
    """Test resolving binary sensor aggregates by device class."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_aggregates_kitchen_aggregate_motion",
            "binary_sensor",
            "magic_areas",
            "aggregates_kitchen_aggregate_motion",
        ),
        (
            "binary_sensor.magic_areas_aggregates_kitchen_aggregate_door",
            "binary_sensor",
            "magic_areas",
            "aggregates_kitchen_aggregate_door",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert len(refs.binary_aggregates_by_device_class) == 2
    assert (
        refs.binary_aggregates_by_device_class["motion"]
        == "binary_sensor.magic_areas_aggregates_kitchen_aggregate_motion"
    )
    assert (
        refs.binary_aggregates_by_device_class["door"]
        == "binary_sensor.magic_areas_aggregates_kitchen_aggregate_door"
    )


def test_build_entity_references_light_groups() -> None:
    """Test resolving light groups by category."""
    registry = _make_registry(
        (
            "light.magic_areas_light_groups_kitchen_overhead",
            "light",
            "magic_areas",
            "light_groups_kitchen_overhead",
        ),
        (
            "light.magic_areas_light_groups_kitchen_task",
            "light",
            "magic_areas",
            "light_groups_kitchen_task",
        ),
        (
            "switch.magic_areas_light_groups_kitchen_light_control",
            "switch",
            "magic_areas",
            "light_groups_kitchen_light_control",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert len(refs.light_groups_by_category) == 2
    assert (
        refs.light_groups_by_category["overhead"]
        == "light.magic_areas_light_groups_kitchen_overhead"
    )
    assert (
        refs.light_groups_by_category["task"]
        == "light.magic_areas_light_groups_kitchen_task"
    )
    assert (
        refs.light_control_switch
        == "switch.magic_areas_light_groups_kitchen_light_control"
    )


def test_build_entity_references_fan_groups() -> None:
    """Test resolving fan group and control switch."""
    registry = _make_registry(
        (
            "fan.magic_areas_fan_groups_kitchen_fan_group",
            "fan",
            "magic_areas",
            "fan_groups_kitchen_fan_group",
        ),
        (
            "switch.magic_areas_fan_groups_kitchen_fan_control",
            "switch",
            "magic_areas",
            "fan_groups_kitchen_fan_control",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert refs.fan_group == "fan.magic_areas_fan_groups_kitchen_fan_group"
    assert (
        refs.fan_control_switch == "switch.magic_areas_fan_groups_kitchen_fan_control"
    )


def test_build_entity_references_media_player_groups() -> None:
    """Test resolving media player group and control switch."""
    registry = _make_registry(
        (
            "media_player.magic_areas_media_player_groups_kitchen_media_player_group",
            "media_player",
            "magic_areas",
            "media_player_groups_kitchen_media_player_group",
        ),
        (
            "switch.magic_areas_media_player_groups_kitchen_media_player_control",
            "switch",
            "magic_areas",
            "media_player_groups_kitchen_media_player_control",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.media_player_group
        == "media_player.magic_areas_media_player_groups_kitchen_media_player_group"
    )
    assert (
        refs.media_player_control_switch
        == "switch.magic_areas_media_player_groups_kitchen_media_player_control"
    )


def test_build_entity_references_climate_control() -> None:
    """Test resolving climate control switch."""
    registry = _make_registry(
        (
            "switch.magic_areas_climate_control_kitchen",
            "switch",
            "magic_areas",
            "climate_control_kitchen",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.climate_control_switch
        == "switch.magic_areas_climate_control_kitchen"
    )


def test_build_entity_references_cover_groups() -> None:
    """Test resolving cover group."""
    registry = _make_registry(
        (
            "cover.magic_areas_cover_groups_kitchen_cover_group",
            "cover",
            "magic_areas",
            "cover_groups_kitchen_cover_group",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert refs.cover_group == "cover.magic_areas_cover_groups_kitchen_cover_group"


def test_build_entity_references_wasp_in_a_box() -> None:
    """Test resolving wasp in a box sensor."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_wasp_in_a_box_kitchen",
            "binary_sensor",
            "magic_areas",
            "wasp_in_a_box_kitchen",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.wasp_in_a_box_sensor
        == "binary_sensor.magic_areas_wasp_in_a_box_kitchen"
    )


def test_build_entity_references_ble_tracker() -> None:
    """Test resolving BLE tracker monitor."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor",
            "binary_sensor",
            "magic_areas",
            "ble_trackers_kitchen_ble_tracker_monitor",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.ble_tracker_monitor
        == "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor"
    )


def test_build_entity_references_threshold() -> None:
    """Test resolving threshold sensor."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_threshold_kitchen_light",
            "binary_sensor",
            "magic_areas",
            "threshold_kitchen_light",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.threshold_sensor
        == "binary_sensor.magic_areas_threshold_kitchen_light"
    )


def test_build_entity_references_health() -> None:
    """Test resolving health sensor."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_health_kitchen",
            "binary_sensor",
            "magic_areas",
            "health_kitchen",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert refs.health_sensor == "binary_sensor.magic_areas_health_kitchen"


def test_build_entity_references_filters_by_area_id() -> None:
    """Test that build_entity_references only resolves entities for the specified area."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
            "binary_sensor",
            "magic_areas",
            "presence_tracking_kitchen_area_state",
        ),
        (
            "sensor.magic_areas_aggregates_kitchen_aggregate_temperature",
            "sensor",
            "magic_areas",
            "aggregates_kitchen_aggregate_temperature",
        ),
        # Different area
        (
            "sensor.magic_areas_aggregates_living_room_aggregate_temperature",
            "sensor",
            "magic_areas",
            "aggregates_living_room_aggregate_temperature",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.area_state_sensor
        == "binary_sensor.magic_areas_presence_tracking_kitchen_area_state"
    )
    assert len(refs.aggregates_by_device_class) == 1
    assert (
        refs.aggregates_by_device_class["temperature"]
        == "sensor.magic_areas_aggregates_kitchen_aggregate_temperature"
    )


def test_build_entity_references_ignores_other_platforms() -> None:
    """Test that entities from other platforms are ignored."""
    registry = _make_registry(
        # Same unique_id pattern but different platform
        (
            "sensor.other_aggregates_kitchen_aggregate_temperature",
            "sensor",
            "other_integration",
            "aggregates_kitchen_aggregate_temperature",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert len(refs.aggregates_by_device_class) == 0


def test_build_entity_references_survives_renames() -> None:
    """Test that entity registry lookups work even if entity_id was renamed."""
    registry = _make_registry(
        # Entity was renamed by user
        (
            "binary_sensor.my_custom_presence_sensor",
            "binary_sensor",
            "magic_areas",
            "presence_tracking_kitchen_area_state",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    # Should return the renamed entity_id
    assert refs.area_state_sensor == "binary_sensor.my_custom_presence_sensor"


def test_build_entity_references_comprehensive() -> None:
    """Test build_entity_references with all entity types."""
    registry = _make_registry(
        (
            "binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
            "binary_sensor",
            "magic_areas",
            "presence_tracking_kitchen_area_state",
        ),
        (
            "binary_sensor.magic_areas_aggregates_kitchen_aggregate_motion",
            "binary_sensor",
            "magic_areas",
            "aggregates_kitchen_aggregate_motion",
        ),
        (
            "binary_sensor.magic_areas_wasp_in_a_box_kitchen",
            "binary_sensor",
            "magic_areas",
            "wasp_in_a_box_kitchen",
        ),
        (
            "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor",
            "binary_sensor",
            "magic_areas",
            "ble_trackers_kitchen_ble_tracker_monitor",
        ),
        (
            "binary_sensor.magic_areas_threshold_kitchen_light",
            "binary_sensor",
            "magic_areas",
            "threshold_kitchen_light",
        ),
        (
            "binary_sensor.magic_areas_health_kitchen",
            "binary_sensor",
            "magic_areas",
            "health_kitchen",
        ),
        (
            "sensor.magic_areas_aggregates_kitchen_aggregate_temperature",
            "sensor",
            "magic_areas",
            "aggregates_kitchen_aggregate_temperature",
        ),
        (
            "switch.magic_areas_light_groups_kitchen_light_control",
            "switch",
            "magic_areas",
            "light_groups_kitchen_light_control",
        ),
        (
            "switch.magic_areas_fan_groups_kitchen_fan_control",
            "switch",
            "magic_areas",
            "fan_groups_kitchen_fan_control",
        ),
        (
            "switch.magic_areas_media_player_groups_kitchen_media_player_control",
            "switch",
            "magic_areas",
            "media_player_groups_kitchen_media_player_control",
        ),
        (
            "switch.magic_areas_climate_control_kitchen",
            "switch",
            "magic_areas",
            "climate_control_kitchen",
        ),
        (
            "switch.magic_areas_presence_hold_kitchen",
            "switch",
            "magic_areas",
            "presence_hold_kitchen",
        ),
        (
            "light.magic_areas_light_groups_kitchen_overhead",
            "light",
            "magic_areas",
            "light_groups_kitchen_overhead",
        ),
        (
            "fan.magic_areas_fan_groups_kitchen_fan_group",
            "fan",
            "magic_areas",
            "fan_groups_kitchen_fan_group",
        ),
        (
            "media_player.magic_areas_media_player_groups_kitchen_media_player_group",
            "media_player",
            "magic_areas",
            "media_player_groups_kitchen_media_player_group",
        ),
        (
            "cover.magic_areas_cover_groups_kitchen_cover_group",
            "cover",
            "magic_areas",
            "cover_groups_kitchen_cover_group",
        ),
    )

    refs = build_entity_references(area_id="kitchen", entity_registry=registry)

    assert (
        refs.area_state_sensor
        == "binary_sensor.magic_areas_presence_tracking_kitchen_area_state"
    )
    assert refs.presence_hold_switch == "switch.magic_areas_presence_hold_kitchen"
    assert (
        refs.aggregates_by_device_class["temperature"]
        == "sensor.magic_areas_aggregates_kitchen_aggregate_temperature"
    )
    assert (
        refs.binary_aggregates_by_device_class["motion"]
        == "binary_sensor.magic_areas_aggregates_kitchen_aggregate_motion"
    )
    assert (
        refs.light_control_switch
        == "switch.magic_areas_light_groups_kitchen_light_control"
    )
    assert (
        refs.light_groups_by_category["overhead"]
        == "light.magic_areas_light_groups_kitchen_overhead"
    )
    assert refs.fan_group == "fan.magic_areas_fan_groups_kitchen_fan_group"
    assert (
        refs.fan_control_switch == "switch.magic_areas_fan_groups_kitchen_fan_control"
    )
    assert (
        refs.media_player_group
        == "media_player.magic_areas_media_player_groups_kitchen_media_player_group"
    )
    assert (
        refs.media_player_control_switch
        == "switch.magic_areas_media_player_groups_kitchen_media_player_control"
    )
    assert (
        refs.climate_control_switch
        == "switch.magic_areas_climate_control_kitchen"
    )
    assert refs.cover_group == "cover.magic_areas_cover_groups_kitchen_cover_group"
    assert (
        refs.wasp_in_a_box_sensor
        == "binary_sensor.magic_areas_wasp_in_a_box_kitchen"
    )
    assert (
        refs.ble_tracker_monitor
        == "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor"
    )
    assert (
        refs.threshold_sensor
        == "binary_sensor.magic_areas_threshold_kitchen_light"
    )
    assert refs.health_sensor == "binary_sensor.magic_areas_health_kitchen"
