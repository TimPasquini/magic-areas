"""Fan control policy wrapper."""

from __future__ import annotations

from custom_components.magic_areas.core.fan_control_policy import (
    FanControlDecision,
    FanControlPolicy,
    build_fan_policy,
)

__all__ = [
    "FanControlDecision",
    "FanControlPolicy",
    "build_fan_policy",
]
