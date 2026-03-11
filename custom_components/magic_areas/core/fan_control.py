"""Fan control policy wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON

from custom_components.magic_areas.core.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
)
from custom_components.magic_areas.core.fan_control_policy import (
    FanControlDecision,
    FanControlPolicy,
    build_fan_policy,
)

__all__ = [
    "FanControlDecision",
    "FanControlPolicy",
    "build_fan_policy",
    "build_fan_control_group_policy",
    "FanControlGroupPolicy",
    "fan_decision_to_control_group",
]


@dataclass(slots=True)
class FanControlGroupPolicy(ControlGroupPolicy):
    """Canonical control-group policy adapter for fan control."""

    policy: FanControlPolicy

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Evaluate fan control for a canonical control-group context."""
        signals = FanPolicySignals.from_signals(context.signals)

        decision = self.policy.evaluate(
            current_states=context.current_states,
            sensor_value=signals.sensor_value,
        )
        return fan_decision_to_control_group(
            decision=decision,
            fan_group_entity_id=signals.fan_group_entity_id,
            fan_group_state=signals.fan_group_state,
        )


@dataclass(frozen=True, slots=True)
class FanPolicySignals:
    """Typed runtime inputs for fan policy adapters."""

    sensor_value: float | None
    fan_group_entity_id: str | None
    fan_group_state: str | None

    @classmethod
    def from_signals(cls, signals: Any) -> FanPolicySignals:
        """Parse typed fan signals from control-group context."""
        if isinstance(signals, cls):
            return signals
        return cls(sensor_value=None, fan_group_entity_id=None, fan_group_state=None)


def build_fan_control_group_policy(feature_config: dict[str, Any]) -> FanControlGroupPolicy:
    """Build a canonical control-group policy adapter from feature config."""
    return FanControlGroupPolicy(policy=build_fan_policy(feature_config))


def fan_decision_to_control_group(
    decision: FanControlDecision,
    fan_group_entity_id: str | None,
    fan_group_state: str | None,
) -> ControlGroupDecision:
    """Translate fan policy output into control-group actions."""
    if not fan_group_entity_id:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason="fan_group_unavailable",
        )

    if decision.should_turn_on:
        return ControlGroupDecision(
            action_type=ControlActionType.ACTIVATE,
            reason=decision.reason,
            actions=(
                ControlAction(
                    domain=FAN_DOMAIN,
                    service=SERVICE_TURN_ON,
                    target_entity_ids=(fan_group_entity_id,),
                ),
            ),
        )

    if decision.should_turn_off and fan_group_state == STATE_ON:
        return ControlGroupDecision(
            action_type=ControlActionType.DEACTIVATE,
            reason=decision.reason,
            actions=(
                ControlAction(
                    domain=FAN_DOMAIN,
                    service=SERVICE_TURN_OFF,
                    target_entity_ids=(fan_group_entity_id,),
                ),
            ),
        )

    return ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        reason=f"{decision.reason}_noop",
    )


def _as_float_or_none(value: Any) -> float | None:
    """Normalize numeric signal values to float for policy input."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _as_optional_str(value: Any) -> str | None:
    """Normalize optional string signal values."""
    return value if isinstance(value, str) else None
