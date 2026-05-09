"""Control intent engine contracts."""

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
    "custom_control_label_name",
    "evaluate_intent",
    "resolve_custom_control_target",
    "resolve_role_target",
]
