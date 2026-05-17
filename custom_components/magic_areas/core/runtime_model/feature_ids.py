"""Feature-specific runtime ID builders.

This module hosts legacy-stable ID contracts used by runtime resolution and
feature assembly. Keep it internal to runtime_model; do not re-export from
the package root.
"""

from __future__ import annotations

from custom_components.magic_areas.core.runtime_model.groups import ControlGroupPolicyId
from custom_components.magic_areas.core.runtime_model.identity import (
    build_feature_unique_id,
)


def build_presence_hold_switch_unique_id(*, area_id: str) -> str:
    """Return unique_id for the presence-hold switch."""
    return build_feature_unique_id(feature_id="presence_hold", area_id=area_id)


def build_light_control_switch_unique_id(*, area_id: str) -> str:
    """Return unique_id for the light control switch."""
    return build_feature_unique_id(
        feature_id="light_groups",
        area_id=area_id,
        translation_key="light_control",
    )


def build_fan_control_switch_unique_id(*, area_id: str) -> str:
    """Return unique_id for the fan control switch."""
    return build_feature_unique_id(
        feature_id="fan_groups",
        area_id=area_id,
        translation_key="fan_control",
    )


def build_media_player_control_switch_unique_id(*, area_id: str) -> str:
    """Return unique_id for the media-player control switch."""
    return build_feature_unique_id(
        feature_id="media_player_groups",
        area_id=area_id,
        translation_key="media_player_control",
    )


def build_cover_control_switch_unique_id(*, area_id: str) -> str:
    """Return unique_id for the cover control switch."""
    return build_feature_unique_id(
        feature_id="cover_groups",
        area_id=area_id,
        translation_key="cover_control",
    )


def build_climate_control_switch_unique_id(*, area_id: str) -> str:
    """Return unique_id for the climate-control switch."""
    return build_feature_unique_id(feature_id="climate_control", area_id=area_id)


def build_cover_group_unique_id(*, area_id: str) -> str:
    """Return unique_id for the cover group entity."""
    return build_feature_unique_id(
        feature_id="cover_groups",
        area_id=area_id,
        translation_key="cover_group",
    )


def build_wasp_sensor_unique_id(*, area_id: str) -> str:
    """Return unique_id for the wasp-in-a-box sensor."""
    return build_feature_unique_id(feature_id="wasp_in_a_box", area_id=area_id)


def build_ble_tracker_monitor_unique_id(*, area_id: str) -> str:
    """Return unique_id for the BLE tracker monitor entity."""
    return build_feature_unique_id(
        feature_id="ble_trackers",
        area_id=area_id,
        translation_key="ble_tracker_monitor",
    )


def build_health_sensor_unique_id(*, area_id: str) -> str:
    """Return unique_id for the health sensor."""
    return build_feature_unique_id(feature_id="health", area_id=area_id)


def build_threshold_light_sensor_unique_id(*, area_id: str) -> str:
    """Return unique_id for the threshold light sensor."""
    return build_feature_unique_id(
        feature_id="threshold",
        area_id=area_id,
        translation_key="light",
    )


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
    return (
        f"{ControlGroupPolicyId.MEDIA_PLAYER_GROUPS}_{area_id}_media_player_group"
    )
