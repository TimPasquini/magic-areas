"""Contracts for canonical control-group IDs and policy IDs."""

from custom_components.magic_areas.core.group_contracts import (
    ControlGroupPolicyId,
    build_aggregate_group_id,
    build_climate_control_group_id,
    build_fan_group_id,
    build_light_group_id,
    build_media_player_group_id,
)


def test_policy_ids_are_stable() -> None:
    """Policy IDs should remain stable for registry/runtime compatibility."""
    assert str(ControlGroupPolicyId.LIGHT_GROUPS) == "light_groups"
    assert str(ControlGroupPolicyId.FAN_GROUPS) == "fan_groups"
    assert str(ControlGroupPolicyId.CLIMATE_CONTROL) == "climate_control"
    assert str(ControlGroupPolicyId.MEDIA_PLAYER_GROUPS) == "media_player_groups"
    assert str(ControlGroupPolicyId.AGGREGATE) == "aggregate"
    assert str(ControlGroupPolicyId.CUSTOM_CONTROL_GROUP) == "custom_control_group"


def test_group_id_builders_match_existing_unique_id_contracts() -> None:
    """Builder output should match legacy unique-id formats exactly."""
    assert build_light_group_id(area_id="area-1", category="all_lights") == (
        "light_groups_area-1_all_lights"
    )
    assert build_fan_group_id(area_id="area-1") == "fan_groups_area-1_fan_group"
    assert build_climate_control_group_id(area_id="area-1") == (
        "climate_control_area-1_climate_control"
    )
    assert build_media_player_group_id(area_id="area-1") == (
        "media_player_groups_area-1_media_player_group"
    )
    assert build_aggregate_group_id(area_id="area-1", device_class="temperature") == (
        "aggregates_area-1_aggregate_temperature"
    )
