"""Parity tests between legacy entity-id migration and current ID contracts."""

from __future__ import annotations

import pytest

from custom_components.magic_areas.core.runtime_model import (
    build_presence_tracking_unique_id,
)
from custom_components.magic_areas.core.runtime_model import (
    compute_unique_id_from_entity_id,
)
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_ble_tracker_monitor_unique_id,
    build_climate_control_switch_unique_id,
    build_cover_group_unique_id,
    build_fan_control_switch_unique_id,
    build_fan_group_id,
    build_health_sensor_unique_id,
    build_light_control_switch_unique_id,
    build_light_group_id,
    build_media_player_control_switch_unique_id,
    build_media_player_group_id,
    build_presence_hold_switch_unique_id,
    build_wasp_sensor_unique_id,
)


@pytest.mark.parametrize(
    ("legacy_entity_id", "expected_unique_id"),
    [
        (
            "binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
            build_presence_tracking_unique_id(area_id="kitchen"),
        ),
        (
            "switch.magic_areas_presence_hold_kitchen",
            build_presence_hold_switch_unique_id(area_id="kitchen"),
        ),
        (
            "switch.magic_areas_light_groups_kitchen_light_control",
            build_light_control_switch_unique_id(area_id="kitchen"),
        ),
        (
            "switch.magic_areas_fan_groups_kitchen_fan_control",
            build_fan_control_switch_unique_id(area_id="kitchen"),
        ),
        (
            "switch.magic_areas_media_player_groups_kitchen_media_player_control",
            build_media_player_control_switch_unique_id(area_id="kitchen"),
        ),
        (
            "switch.magic_areas_climate_control_kitchen",
            build_climate_control_switch_unique_id(area_id="kitchen"),
        ),
        (
            "cover.magic_areas_cover_groups_kitchen_cover_group",
            build_cover_group_unique_id(area_id="kitchen"),
        ),
        (
            "binary_sensor.magic_areas_wasp_in_a_box_kitchen",
            build_wasp_sensor_unique_id(area_id="kitchen"),
        ),
        (
            "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor",
            build_ble_tracker_monitor_unique_id(area_id="kitchen"),
        ),
        (
            "binary_sensor.magic_areas_health_kitchen",
            build_health_sensor_unique_id(area_id="kitchen"),
        ),
        (
            "fan.magic_areas_fan_groups_kitchen_fan_group",
            build_fan_group_id(area_id="kitchen"),
        ),
        (
            "media_player.magic_areas_media_player_groups_kitchen_media_player_group",
            build_media_player_group_id(area_id="kitchen"),
        ),
        (
            "light.magic_areas_light_groups_kitchen_all_lights",
            build_light_group_id(area_id="kitchen", category="all_lights"),
        ),
    ],
)
def test_migration_output_matches_current_id_contracts(
    legacy_entity_id: str,
    expected_unique_id: str,
) -> None:
    """Legacy entity-id migration should resolve to current canonical IDs."""
    assert (
        compute_unique_id_from_entity_id(
            entity_id=legacy_entity_id,
            area_id="kitchen",
            area_slug="kitchen",
        )
        == expected_unique_id
    )


@pytest.mark.parametrize(
    "legacy_entity_id",
    [
        "binary_sensor.not_magic_areas_presence_tracking_kitchen_area_state",
        "binary_sensor.magic_areas_presence_tracking_living_room_area_state",
        "binary_sensor.magic_areas__kitchen_area_state",
    ],
)
def test_migration_returns_none_for_non_migratable_entity_ids(
    legacy_entity_id: str,
) -> None:
    """Malformed or non-magic IDs should not migrate."""
    assert (
        compute_unique_id_from_entity_id(
            entity_id=legacy_entity_id,
            area_id="kitchen",
            area_slug="kitchen",
        )
        is None
    )
