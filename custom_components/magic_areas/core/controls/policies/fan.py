"""Fan control policy wrapper."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_FAN_CONTROLLER_ACTIVE_STATES,
    CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR,
    CONF_FAN_CONTROLLER_DETECTION_MODE,
    CONF_FAN_CONTROLLER_HYSTERESIS,
    CONF_FAN_CONTROLLER_MEMBERS,
    CONF_FAN_CONTROLLER_ON_THRESHOLD,
    CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS,
    CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID,
    CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR,
    CONF_FAN_CONTROLLER_SUPPRESS_STATES,
    CONF_FAN_GROUPS_CONTROLLERS,
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
    "fan_controller_evaluation_to_control_group",
    "fan_decision_to_control_group",
    "legacy_cooling_controller",
]

LEGACY_FAN_SENSOR_KEY = "__legacy_fan_sensor__"


@dataclass(slots=True)
class FanControlGroupPolicy(ControlGroupPolicy):
    """Canonical control-group policy adapter for fan control."""

    policy: FanControlPolicy | None = None
    controllers: tuple[FanControllerConfig, ...] = ()
    last_evaluation: FanControllerEvaluation | None = None

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Evaluate fan control for a canonical control-group context."""
        signals = FanPolicySignals.from_signals(context.signals)

        if self.controllers:
            sensor_values = dict(signals.sensor_values or {})
            sensor_values.setdefault(LEGACY_FAN_SENSOR_KEY, signals.sensor_value)
            evaluation = evaluate_fan_controllers(
                self.controllers,
                current_states=context.current_states,
                sensor_values=sensor_values,
                trend_states=signals.trend_states,
            )
            self.last_evaluation = evaluation
            return fan_controller_evaluation_to_control_group(
                evaluation=evaluation,
                fan_group_entity_id=signals.fan_group_entity_id,
                fan_group_state=signals.fan_group_state,
            )

        if self.policy is None:
            return ControlGroupDecision(
                action_type=ControlActionType.NOOP,
                reason="fan_policy_unavailable",
            )

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
    THRESHOLD_TREND = "threshold_trend"


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
    sensor_values: Mapping[str, float | None] | None = None
    trend_states: Mapping[str, bool | None] | None = None

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
    trend_states: Mapping[str, bool | None] | None = None,
    previously_active_controller_ids: Sequence[str] = (),
) -> FanControllerEvaluation:
    """Evaluate fan controllers and aggregate per-entity service intent."""
    current_state_set = {str(state) for state in current_states}
    previous_active = {str(controller_id) for controller_id in previously_active_controller_ids}
    current_trend_states = trend_states or {}

    active: list[FanControllerReason] = []
    suppressed: list[FanControllerReason] = []
    inactive: list[FanControllerReason] = []

    for controller in controllers:
        reason = _evaluate_fan_controller(
            controller,
            current_states=current_state_set,
            sensor_values=sensor_values,
            trend_states=current_trend_states,
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
    trend_states: Mapping[str, bool | None],
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

    if (
        controller.detection_mode is FanDetectionMode.THRESHOLD_TREND
        and trend_states.get(controller.controller_id) is True
        and sensor_value >= controller.off_threshold
    ):
        return FanControllerReason(
            controller_id=controller.controller_id,
            members=controller.members,
            reason=(
                f"active_trend_rising_inside_hysteresis "
                f"({sensor_value:.1f} >= {controller.off_threshold:.1f})"
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
    controllers = _controllers_from_feature_config(feature_config)
    if controllers:
        return FanControlGroupPolicy(controllers=controllers)

    policy = build_fan_policy(feature_config)
    return FanControlGroupPolicy(
        policy=policy,
        controllers=(
            legacy_cooling_controller(
                setpoint=policy.setpoint,
                required_state=policy.required_state,
                tracked_sensor_entity_id=LEGACY_FAN_SENSOR_KEY,
            ),
        ),
    )


def _controllers_from_feature_config(
    feature_config: Mapping[str, object],
) -> tuple[FanControllerConfig, ...]:
    """Build controller configs from persisted role config."""
    raw_controllers = feature_config.get(CONF_FAN_GROUPS_CONTROLLERS)
    if not isinstance(raw_controllers, Mapping):
        return ()

    controllers: list[FanControllerConfig] = []
    for controller_id in (
        FanControllerRole.COOLING.value,
        FanControllerRole.HUMIDITY.value,
        FanControllerRole.ODOR.value,
    ):
        raw_controller = raw_controllers.get(controller_id)
        if not isinstance(raw_controller, Mapping):
            continue
        controller = _controller_from_mapping(controller_id, raw_controller)
        if controller is not None:
            controllers.append(controller)
    return tuple(controllers)


def _controller_from_mapping(
    controller_id: str,
    raw_controller: Mapping[str, object],
) -> FanControllerConfig | None:
    """Coerce persisted controller config into runtime policy config."""
    members = _string_tuple(raw_controller.get(CONF_FAN_CONTROLLER_MEMBERS))
    sensor_entity_id = raw_controller.get(CONF_FAN_CONTROLLER_SENSOR_ENTITY_ID)
    sensor_entity_id = str(sensor_entity_id) if sensor_entity_id else None

    if not members or not sensor_entity_id:
        return None

    detection_mode = _enum_or_default(
        FanDetectionMode,
        raw_controller.get(CONF_FAN_CONTROLLER_DETECTION_MODE),
        FanDetectionMode.THRESHOLD,
    )
    clear_behavior = _enum_or_default(
        FanClearBehavior,
        raw_controller.get(CONF_FAN_CONTROLLER_CLEAR_BEHAVIOR),
        FanClearBehavior.OCCUPANCY_ONLY,
    )
    unavailable_behavior = _enum_or_default(
        FanSensorUnavailableBehavior,
        raw_controller.get(CONF_FAN_CONTROLLER_SENSOR_UNAVAILABLE_BEHAVIOR),
        FanSensorUnavailableBehavior.CLEAR_REASON,
    )
    active_states = _string_tuple(raw_controller.get(CONF_FAN_CONTROLLER_ACTIVE_STATES))

    return FanControllerConfig(
        controller_id=controller_id,
        members=members,
        sensor_entity_id=sensor_entity_id,
        detection_mode=detection_mode,
        on_threshold=coerce_float(
            raw_controller.get(CONF_FAN_CONTROLLER_ON_THRESHOLD),
            default=0.0,
        ),
        hysteresis=coerce_float(
            raw_controller.get(CONF_FAN_CONTROLLER_HYSTERESIS),
            default=0.0,
        ),
        active_states=active_states,
        suppress_states=_string_tuple(
            raw_controller.get(CONF_FAN_CONTROLLER_SUPPRESS_STATES)
        ),
        clear_behavior=clear_behavior,
        post_clear_hold_seconds=int(
            coerce_float(
                raw_controller.get(CONF_FAN_CONTROLLER_POST_CLEAR_HOLD_SECONDS),
                default=0.0,
            )
        ),
        sensor_unavailable_behavior=unavailable_behavior,
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    """Coerce a stored string/list value into a string tuple."""
    if isinstance(value, str):
        return (value,) if value else ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(item) for item in value if item)


def _enum_or_default[T: StrEnum](
    enum_type: type[T],
    value: object,
    default: T,
) -> T:
    """Coerce a stored enum value or return the default."""
    try:
        return enum_type(str(value))
    except ValueError:
        return default


def fan_controller_evaluation_to_control_group(
    *,
    evaluation: FanControllerEvaluation,
    fan_group_entity_id: str | None,
    fan_group_state: str | None,
) -> ControlGroupDecision:
    """Translate controller-list evaluation into a control-group decision."""
    activate_targets = evaluation.turn_on_entity_ids or (
        (fan_group_entity_id,) if fan_group_entity_id else ()
    )
    deactivate_targets = evaluation.turn_off_entity_ids or (
        (fan_group_entity_id,) if fan_group_entity_id else ()
    )

    if not activate_targets and not deactivate_targets:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason="fan_group_unavailable",
        )

    if evaluation.active_reasons:
        return ControlGroupDecision(
            action_type=ControlActionType.ACTIVATE,
            reason=", ".join(reason.reason for reason in evaluation.active_reasons),
            actions=(
                ControlAction(
                    domain=FAN_DOMAIN,
                    service=SERVICE_TURN_ON,
                    target_entity_ids=activate_targets,
                ),
            ),
        )

    reason = (
        ", ".join(reason.reason for reason in evaluation.inactive_reasons)
        or "no_active_fan_reasons"
    )
    if evaluation.turn_off_entity_ids or fan_group_state == STATE_ON:
        return ControlGroupDecision(
            action_type=ControlActionType.DEACTIVATE,
            reason=reason,
            actions=(
                ControlAction(
                    domain=FAN_DOMAIN,
                    service=SERVICE_TURN_OFF,
                    target_entity_ids=deactivate_targets,
                ),
            ),
        )

    return ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        reason=f"{reason}_noop",
    )


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
