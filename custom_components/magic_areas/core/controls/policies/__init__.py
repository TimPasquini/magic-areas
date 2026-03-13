"""Policy adapter surface for control-group features."""

from custom_components.magic_areas.core.controls.policies.climate import (
    ClimateControlGroupPolicy,
    ClimatePolicySignals,
    ClimatePresetPolicy,
    build_climate_control_group_policy,
    build_preset_policy,
    climate_preset_to_control_group,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    FanControlDecision,
    FanControlGroupPolicy,
    FanControlPolicy,
    FanPolicySignals,
    build_fan_control_group_policy,
    build_fan_policy,
    fan_decision_to_control_group,
)
from custom_components.magic_areas.core.controls.policies.media import (
    MediaControlPolicy,
    MediaPolicySignals,
    build_media_control_group_policy,
    evaluate_area_routing,
    has_valid_notification_states,
    media_state_change_to_control_group,
    should_skip_sleep_state,
)

__all__ = [
    "ClimateControlGroupPolicy",
    "ClimatePolicySignals",
    "ClimatePresetPolicy",
    "FanControlDecision",
    "FanControlGroupPolicy",
    "FanControlPolicy",
    "FanPolicySignals",
    "MediaControlPolicy",
    "MediaPolicySignals",
    "build_climate_control_group_policy",
    "build_fan_control_group_policy",
    "build_fan_policy",
    "build_media_control_group_policy",
    "build_preset_policy",
    "climate_preset_to_control_group",
    "evaluate_area_routing",
    "fan_decision_to_control_group",
    "has_valid_notification_states",
    "media_state_change_to_control_group",
    "should_skip_sleep_state",
]
