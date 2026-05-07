"""Control intent engine contracts."""

from custom_components.magic_areas.core.control_intents.models import (
    ControlTargetKind,
    ControlTargetPrecision,
    ControlTargetSource,
    RoleTarget,
)
from custom_components.magic_areas.core.control_intents.targets import (
    resolve_role_target,
)

__all__ = [
    "ControlTargetKind",
    "ControlTargetPrecision",
    "ControlTargetSource",
    "RoleTarget",
    "resolve_role_target",
]
