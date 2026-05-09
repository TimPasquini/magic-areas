"""Control intent engine contracts."""

from custom_components.magic_areas.core.control_intents.adaptive_lighting import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
    AdaptiveLightingSwitchSet,
    adaptive_lighting_switch_entity_ids,
    switch_set_from_explicit_refs,
    switch_set_from_name_candidates,
)
from custom_components.magic_areas.core.control_intents.engine import (
    ConstraintEffect,
    ControlIntent,
    IntentAction,
    IntentConstraint,
    IntentDecision,
    IntentReason,
    evaluate_intent,
)
from custom_components.magic_areas.core.control_intents.models import (
    ControlTargetKind,
    ControlTargetPrecision,
    ControlTargetSource,
    RoleTarget,
)
from custom_components.magic_areas.core.control_intents.targets import (
    custom_control_label_name,
    resolve_custom_control_target,
    resolve_role_target,
)

__all__ = [
    "ADAPT_BRIGHTNESS_SWITCH",
    "ADAPT_COLOR_SWITCH",
    "MAIN_SWITCH",
    "SLEEP_SWITCH",
    "AdaptiveLightingSwitchSet",
    "ConstraintEffect",
    "ControlIntent",
    "ControlTargetKind",
    "ControlTargetPrecision",
    "ControlTargetSource",
    "IntentAction",
    "IntentConstraint",
    "IntentDecision",
    "IntentReason",
    "RoleTarget",
    "adaptive_lighting_switch_entity_ids",
    "custom_control_label_name",
    "evaluate_intent",
    "resolve_custom_control_target",
    "resolve_role_target",
    "switch_set_from_explicit_refs",
    "switch_set_from_name_candidates",
]
