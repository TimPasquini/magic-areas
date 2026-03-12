"""Canonical control-group policy IDs and group-ID builders."""

from __future__ import annotations

from enum import StrEnum


class ControlGroupPolicyId(StrEnum):
    """Policy IDs used for control/aggregate group registration and lookup."""

    LIGHT_GROUPS = "light_groups"
    FAN_GROUPS = "fan_groups"
    CLIMATE_CONTROL = "climate_control"
    MEDIA_PLAYER_GROUPS = "media_player_groups"
    AGGREGATE = "aggregate"
    CUSTOM_CONTROL_GROUP = "custom_control_group"


RESERVED_POLICY_IDS: frozenset[str] = frozenset(str(policy) for policy in ControlGroupPolicyId)


def is_reserved_policy_id(policy_id: str) -> bool:
    """Return True when the policy ID is reserved by built-in control flows."""
    return policy_id in RESERVED_POLICY_IDS


def build_light_group_id(*, area_id: str, category: str) -> str:
    """Return stable light-group unique ID."""
    return f"{ControlGroupPolicyId.LIGHT_GROUPS}_{area_id}_{category}"


def build_fan_group_id(*, area_id: str) -> str:
    """Return stable fan-group unique ID."""
    return f"{ControlGroupPolicyId.FAN_GROUPS}_{area_id}_fan_group"


def build_climate_control_group_id(*, area_id: str) -> str:
    """Return stable climate-control group unique ID."""
    return f"{ControlGroupPolicyId.CLIMATE_CONTROL}_{area_id}_climate_control"


def build_media_player_group_id(*, area_id: str) -> str:
    """Return stable media-player-group unique ID."""
    return f"{ControlGroupPolicyId.MEDIA_PLAYER_GROUPS}_{area_id}_media_player_group"


def build_aggregate_group_id(*, area_id: str, device_class: str) -> str:
    """Return stable aggregate group unique ID."""
    return f"aggregates_{area_id}_aggregate_{device_class}"
