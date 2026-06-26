"""Fan control policy wrapper."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
)
from custom_components.magic_areas.core.config.feature import coerce_float
from custom_components.magic_areas.core.controls.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.option_defaults import feature_option_default

__all__ = [
    "FanControlDecision",
    "FanControlGroupPolicy",
    "FanControlPolicy",
    "FanPolicySignals",
    "build_fan_control_group_policy",
    "build_fan_policy",
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
    def from_signals(cls, signals: object) -> FanPolicySignals:
        """Parse typed fan signals from control-group context."""
        if isinstance(signals, cls):
            return signals
        return cls(sensor_value=None, fan_group_entity_id=None, fan_group_state=None)


@dataclass(slots=True)
class FanControlDecision:
    """Fan control decision result."""

    should_turn_on: bool
    should_turn_off: bool
    reason: str


@dataclass(slots=True)
class FanControlPolicy:
    """Policy for controlling fans based on area state and sensor values."""

    setpoint: float
    required_state: str

    def evaluate(
        self,
        current_states: Sequence[str],
        sensor_value: float | None,
    ) -> FanControlDecision:
        """Evaluate whether fan should turn on or off."""
        if AreaStates.CLEAR in current_states:
            return FanControlDecision(
                should_turn_on=False,
                should_turn_off=True,
                reason="area_clear",
            )

        if self.required_state not in current_states:
            return FanControlDecision(
                should_turn_on=False,
                should_turn_off=True,
                reason=f"required_state_not_met ({self.required_state})",
            )

        if sensor_value is None:
            return FanControlDecision(
                should_turn_on=False,
                should_turn_off=True,
                reason="sensor_unavailable",
            )

        if sensor_value >= self.setpoint:
            return FanControlDecision(
                should_turn_on=True,
                should_turn_off=False,
                reason=f"setpoint_reached ({sensor_value:.1f} >= {self.setpoint:.1f})",
            )

        return FanControlDecision(
            should_turn_on=False,
            should_turn_off=True,
            reason=f"below_setpoint ({sensor_value:.1f} < {self.setpoint:.1f})",
        )


def build_fan_policy(feature_config: Mapping[str, object]) -> FanControlPolicy:
    """Build fan control policy from feature configuration."""
    default_setpoint = coerce_float(
        feature_option_default(MagicAreasFeatures.FAN_GROUPS, CONF_FAN_GROUPS_SETPOINT),
        default=0.0,
    )
    setpoint = coerce_float(
        feature_config.get(
            CONF_FAN_GROUPS_SETPOINT,
            default_setpoint,
        ),
        default=default_setpoint,
    )
    required_state = str(
        feature_config.get(
            CONF_FAN_GROUPS_REQUIRED_STATE,
            feature_option_default(
                MagicAreasFeatures.FAN_GROUPS, CONF_FAN_GROUPS_REQUIRED_STATE
            ),
        )
    )
    return FanControlPolicy(setpoint=setpoint, required_state=required_state)


def build_fan_control_group_policy(
    feature_config: Mapping[str, object],
) -> FanControlGroupPolicy:
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
