"""Fan control policy wrapper."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
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
    "FanClearBehavior",
    "FanControllerConfig",
    "FanControllerEvaluation",
    "FanControllerReason",
    "FanControllerRole",
    "FanControlDecision",
    "FanControlGroupPolicy",
    "FanControlPolicy",
    "FanDetectionMode",
    "FanSensorUnavailableBehavior",
    "FanPolicySignals",
    "build_fan_control_group_policy",
    "build_fan_policy",
    "evaluate_fan_controllers",
    "fan_decision_to_control_group",
    "legacy_cooling_controller",
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


class FanControllerRole(StrEnum):
    """Built-in fan controller reason roles."""

    COOLING = "cooling"
    HUMIDITY = "humidity"
    ODOR = "odor"


class FanDetectionMode(StrEnum):
    """Supported fan controller signal detection modes."""

    THRESHOLD = "threshold"


class FanClearBehavior(StrEnum):
    """How a controller reason responds when occupancy/state gating clears."""

    RUN_UNTIL_CLEAR = "run_until_clear"
    OCCUPANCY_ONLY = "occupancy_only"
    POST_CLEAR_HOLD = "post_clear_hold"


class FanSensorUnavailableBehavior(StrEnum):
    """How a controller reason responds when its sensor cannot be read."""

    CLEAR_REASON = "clear_reason"
    HOLD_THEN_CLEAR = "hold_then_clear"
    HOLD_UNTIL_RESTORED = "hold_until_restored"


@dataclass(frozen=True, slots=True)
class FanControllerConfig:
    """Normalized config for one reason a fan may need to run."""

    controller_id: str
    members: tuple[str, ...]
    sensor_entity_id: str | None
    detection_mode: FanDetectionMode
    on_threshold: float
    hysteresis: float
    active_states: tuple[str, ...]
    suppress_states: tuple[str, ...] = ()
    clear_behavior: FanClearBehavior = FanClearBehavior.OCCUPANCY_ONLY
    post_clear_hold_seconds: int = 0
    sensor_unavailable_behavior: FanSensorUnavailableBehavior = (
        FanSensorUnavailableBehavior.CLEAR_REASON
    )

    @property
    def off_threshold(self) -> float:
        """Return the value below which a threshold reason clears."""
        return self.on_threshold - self.hysteresis


@dataclass(frozen=True, slots=True)
class FanControllerReason:
    """Evaluation result for one fan controller reason."""

    controller_id: str
    members: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class FanControllerEvaluation:
    """Pure fan controller policy output."""

    active_reasons: tuple[FanControllerReason, ...]
    suppressed_reasons: tuple[FanControllerReason, ...]
    inactive_reasons: tuple[FanControllerReason, ...]
    target_fan_entity_ids: tuple[str, ...]
    turn_on_entity_ids: tuple[str, ...]
    turn_off_entity_ids: tuple[str, ...]


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


def legacy_cooling_controller(
    *,
    setpoint: float,
    required_state: str,
    tracked_sensor_entity_id: str | None = None,
    members: Sequence[str] = (),
) -> FanControllerConfig:
    """Map the legacy single-threshold fan config into a Cooling controller."""
    return FanControllerConfig(
        controller_id=FanControllerRole.COOLING,
        members=tuple(members),
        sensor_entity_id=tracked_sensor_entity_id,
        detection_mode=FanDetectionMode.THRESHOLD,
        on_threshold=setpoint,
        hysteresis=0.0,
        active_states=(required_state,),
        clear_behavior=FanClearBehavior.OCCUPANCY_ONLY,
        sensor_unavailable_behavior=FanSensorUnavailableBehavior.CLEAR_REASON,
    )


def evaluate_fan_controllers(
    controllers: Sequence[FanControllerConfig],
    *,
    current_states: Sequence[str],
    sensor_values: Mapping[str, float | None],
    previously_active_controller_ids: Sequence[str] = (),
) -> FanControllerEvaluation:
    """Evaluate fan controllers and aggregate per-entity service intent."""
    current_state_set = {str(state) for state in current_states}
    previous_active = {str(controller_id) for controller_id in previously_active_controller_ids}

    active: list[FanControllerReason] = []
    suppressed: list[FanControllerReason] = []
    inactive: list[FanControllerReason] = []

    for controller in controllers:
        reason = _evaluate_fan_controller(
            controller,
            current_states=current_state_set,
            sensor_values=sensor_values,
            was_active=controller.controller_id in previous_active,
        )
        if reason.reason.startswith("suppressed"):
            suppressed.append(reason)
        elif reason.reason.startswith("active"):
            active.append(reason)
        else:
            inactive.append(reason)

    all_targets = _sorted_unique(
        member for controller in controllers for member in controller.members
    )
    active_targets = _sorted_unique(member for reason in active for member in reason.members)
    inactive_targets = tuple(
        entity_id for entity_id in all_targets if entity_id not in set(active_targets)
    )

    return FanControllerEvaluation(
        active_reasons=tuple(active),
        suppressed_reasons=tuple(suppressed),
        inactive_reasons=tuple(inactive),
        target_fan_entity_ids=all_targets,
        turn_on_entity_ids=active_targets,
        turn_off_entity_ids=inactive_targets,
    )


def _evaluate_fan_controller(
    controller: FanControllerConfig,
    *,
    current_states: set[str],
    sensor_values: Mapping[str, float | None],
    was_active: bool,
) -> FanControllerReason:
    """Evaluate one fan controller reason."""
    suppressing_states = tuple(
        state for state in controller.suppress_states if state in current_states
    )
    if suppressing_states:
        return FanControllerReason(
            controller_id=controller.controller_id,
            members=controller.members,
            reason=f"suppressed_by_state ({', '.join(suppressing_states)})",
        )

    if AreaStates.CLEAR in current_states and (
        controller.clear_behavior is not FanClearBehavior.RUN_UNTIL_CLEAR
    ):
        return FanControllerReason(
            controller_id=controller.controller_id,
            members=controller.members,
            reason="inactive_area_clear",
        )

    if controller.clear_behavior is FanClearBehavior.OCCUPANCY_ONLY and not any(
        state in current_states for state in controller.active_states
    ):
        return FanControllerReason(
            controller_id=controller.controller_id,
            members=controller.members,
            reason="inactive_required_state_not_met",
        )

    sensor_value = (
        sensor_values.get(controller.sensor_entity_id)
        if controller.sensor_entity_id
        else None
    )
    if sensor_value is None:
        return _evaluate_unavailable_controller(controller, was_active=was_active)

    if sensor_value >= controller.on_threshold:
        return FanControllerReason(
            controller_id=controller.controller_id,
            members=controller.members,
            reason=(
                f"active_threshold_reached "
                f"({sensor_value:.1f} >= {controller.on_threshold:.1f})"
            ),
        )

    if was_active and sensor_value >= controller.off_threshold:
        return FanControllerReason(
            controller_id=controller.controller_id,
            members=controller.members,
            reason=(
                f"active_hysteresis_hold "
                f"({sensor_value:.1f} >= {controller.off_threshold:.1f})"
            ),
        )

    return FanControllerReason(
        controller_id=controller.controller_id,
        members=controller.members,
        reason=(
            f"inactive_below_clear_threshold "
            f"({sensor_value:.1f} < {controller.off_threshold:.1f})"
        ),
    )


def _evaluate_unavailable_controller(
    controller: FanControllerConfig,
    *,
    was_active: bool,
) -> FanControllerReason:
    """Evaluate one controller with an unavailable sensor."""
    if (
        was_active
        and controller.sensor_unavailable_behavior
        is FanSensorUnavailableBehavior.HOLD_UNTIL_RESTORED
    ):
        return FanControllerReason(
            controller_id=controller.controller_id,
            members=controller.members,
            reason="active_sensor_unavailable_hold",
        )

    return FanControllerReason(
        controller_id=controller.controller_id,
        members=controller.members,
        reason="inactive_sensor_unavailable",
    )


def _sorted_unique(entity_ids: Iterable[str]) -> tuple[str, ...]:
    """Return a stable unique entity-id tuple."""
    return tuple(sorted(set(entity_ids)))


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
    feature_config: Mapping[str, object]
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
