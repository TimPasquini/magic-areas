"""Contracts for control-group policy IDs and public group API surface."""

import custom_components.magic_areas.core.runtime_model as core_groups
from custom_components.magic_areas.core.aggregates import aggregate_group_id
from custom_components.magic_areas.core.runtime_model import ControlGroupPolicyId


def test_policy_ids_are_stable() -> None:
    """Policy IDs should remain stable for registry/runtime compatibility."""
    assert str(ControlGroupPolicyId.LIGHT_GROUPS) == "light_groups"
    assert str(ControlGroupPolicyId.FAN_GROUPS) == "fan_groups"
    assert str(ControlGroupPolicyId.CLIMATE_CONTROL) == "climate_control"
    assert str(ControlGroupPolicyId.MEDIA_PLAYER_GROUPS) == "media_player_groups"
    assert str(ControlGroupPolicyId.AGGREGATE) == "aggregate"
    assert str(ControlGroupPolicyId.CUSTOM_CONTROL_GROUP) == "custom_control_group"


def test_core_groups_public_surface_excludes_feature_group_id_builders() -> None:
    """Feature-specific group-id builders should not be exported by core.groups."""
    exported = set(getattr(core_groups, "__all__", []))
    assert "build_aggregate_group_id" not in exported
    assert "build_climate_control_group_id" not in exported
    assert "build_fan_group_id" not in exported
    assert "build_light_group_id" not in exported
    assert "build_media_player_group_id" not in exported


def test_aggregate_group_id_remains_stable() -> None:
    """Aggregate IDs must preserve legacy format for entity lookup."""
    assert aggregate_group_id(area_id="area-1", device_class="temperature") == (
        "aggregates_area-1_aggregate_temperature"
    )
