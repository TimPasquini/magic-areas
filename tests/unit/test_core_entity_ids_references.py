"""Unit tests for runtime model entity-reference resolution."""
# ruff: noqa: D103

from custom_components.magic_areas.core.runtime_model import build_entity_references
from custom_components.magic_areas.core.runtime_model.references import (
    _build_reference_specs,
)

from tests.unit.core_entity_ids_testkit import make_registry


def test_build_reference_specs_contains_all_reference_fields() -> None:
    specs = _build_reference_specs("kitchen")
    assert len(specs) == 13
    assert {spec.field_name for spec in specs} == {
        "area_state_sensor",
        "presence_hold_switch",
        "light_control_switch",
        "fan_group",
        "fan_control_switch",
        "media_player_group",
        "media_player_control_switch",
        "climate_control_switch",
        "cover_group",
        "wasp_in_a_box_sensor",
        "ble_tracker_monitor",
        "threshold_sensor",
        "health_sensor",
    }


def test_build_reference_specs_encode_requested_area() -> None:
    specs = _build_reference_specs("kitchen")
    assert all("kitchen" in spec.unique_id for spec in specs)


def test_build_entity_references_presence_tracking() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
                "binary_sensor",
                "magic_areas",
                "presence_tracking_kitchen_area_state",
            ),
        ),
    )
    assert (
        refs.area_state_sensor
        == "binary_sensor.magic_areas_presence_tracking_kitchen_area_state"
    )


def test_build_entity_references_presence_hold() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "switch.magic_areas_presence_hold_kitchen",
                "switch",
                "magic_areas",
                "presence_hold_kitchen",
            ),
        ),
    )
    assert refs.presence_hold_switch == "switch.magic_areas_presence_hold_kitchen"


def test_build_entity_references_light_control() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "switch.magic_areas_light_groups_kitchen_light_control",
                "switch",
                "magic_areas",
                "light_groups_kitchen_light_control",
            ),
        ),
    )
    assert (
        refs.light_control_switch
        == "switch.magic_areas_light_groups_kitchen_light_control"
    )


def test_build_entity_references_fan_groups() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
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
        ),
    )
    assert refs.fan_group == "fan.magic_areas_fan_groups_kitchen_fan_group"
    assert (
        refs.fan_control_switch == "switch.magic_areas_fan_groups_kitchen_fan_control"
    )


def test_build_entity_references_media_player_groups() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
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
        ),
    )
    assert (
        refs.media_player_group
        == "media_player.magic_areas_media_player_groups_kitchen_media_player_group"
    )
    assert (
        refs.media_player_control_switch
        == "switch.magic_areas_media_player_groups_kitchen_media_player_control"
    )


def test_build_entity_references_climate_control() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "switch.magic_areas_climate_control_kitchen",
                "switch",
                "magic_areas",
                "climate_control_kitchen",
            ),
        ),
    )
    assert refs.climate_control_switch == "switch.magic_areas_climate_control_kitchen"


def test_build_entity_references_cover_groups() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "cover.magic_areas_cover_groups_kitchen_cover_group",
                "cover",
                "magic_areas",
                "cover_groups_kitchen_cover_group",
            ),
        ),
    )
    assert refs.cover_group == "cover.magic_areas_cover_groups_kitchen_cover_group"


def test_build_entity_references_wasp_in_a_box() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "binary_sensor.magic_areas_wasp_in_a_box_kitchen",
                "binary_sensor",
                "magic_areas",
                "wasp_in_a_box_kitchen",
            ),
        ),
    )
    assert refs.wasp_in_a_box_sensor == "binary_sensor.magic_areas_wasp_in_a_box_kitchen"


def test_build_entity_references_ble_tracker() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor",
                "binary_sensor",
                "magic_areas",
                "ble_trackers_kitchen_ble_tracker_monitor",
            ),
        ),
    )
    assert (
        refs.ble_tracker_monitor
        == "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor"
    )


def test_build_entity_references_threshold() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "binary_sensor.magic_areas_threshold_kitchen_light",
                "binary_sensor",
                "magic_areas",
                "threshold_kitchen_light",
            ),
        ),
    )
    assert refs.threshold_sensor == "binary_sensor.magic_areas_threshold_kitchen_light"


def test_build_entity_references_health() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "binary_sensor.magic_areas_health_kitchen",
                "binary_sensor",
                "magic_areas",
                "health_kitchen",
            ),
        ),
    )
    assert refs.health_sensor == "binary_sensor.magic_areas_health_kitchen"


def test_build_entity_references_survives_renames() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "binary_sensor.my_custom_presence_sensor",
                "binary_sensor",
                "magic_areas",
                "presence_tracking_kitchen_area_state",
            ),
            (
                "binary_sensor.my_custom_threshold_sensor",
                "binary_sensor",
                "magic_areas",
                "threshold_kitchen_light",
            ),
        ),
    )
    assert refs.area_state_sensor == "binary_sensor.my_custom_presence_sensor"
    assert refs.threshold_sensor == "binary_sensor.my_custom_threshold_sensor"


def test_build_entity_references_comprehensive() -> None:
    refs = build_entity_references(
        area_id="kitchen",
        entity_registry=make_registry(
            (
                "binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
                "binary_sensor",
                "magic_areas",
                "presence_tracking_kitchen_area_state",
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
        ),
    )
    assert (
        refs.area_state_sensor
        == "binary_sensor.magic_areas_presence_tracking_kitchen_area_state"
    )
    assert refs.presence_hold_switch == "switch.magic_areas_presence_hold_kitchen"
    assert (
        refs.light_control_switch
        == "switch.magic_areas_light_groups_kitchen_light_control"
    )
    assert refs.fan_group == "fan.magic_areas_fan_groups_kitchen_fan_group"
    assert refs.fan_control_switch == "switch.magic_areas_fan_groups_kitchen_fan_control"
    assert (
        refs.media_player_group
        == "media_player.magic_areas_media_player_groups_kitchen_media_player_group"
    )
    assert (
        refs.media_player_control_switch
        == "switch.magic_areas_media_player_groups_kitchen_media_player_control"
    )
    assert refs.climate_control_switch == "switch.magic_areas_climate_control_kitchen"
    assert refs.cover_group == "cover.magic_areas_cover_groups_kitchen_cover_group"
    assert refs.wasp_in_a_box_sensor == "binary_sensor.magic_areas_wasp_in_a_box_kitchen"
    assert (
        refs.ble_tracker_monitor
        == "binary_sensor.magic_areas_ble_trackers_kitchen_ble_tracker_monitor"
    )
    assert refs.threshold_sensor == "binary_sensor.magic_areas_threshold_kitchen_light"
    assert refs.health_sensor == "binary_sensor.magic_areas_health_kitchen"
