"""Light group control policy for Magic Areas."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum, auto
from collections.abc import Mapping

from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON

from custom_components.magic_areas.core.state_priority import (
    LIGHT_PRIORITY_STATES,
    filter_by_priority,
)
from custom_components.magic_areas.core.controls import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
    ControlRuntimeEffect,
    ControlRuntimeEffectType,
)
from custom_components.magic_areas.area_state import AreaStates

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CommandEchoState:
    """Immutable snapshot of command ownership state."""

    owner_id: str | None = None
    controlling: bool = False
    awaiting_echo: bool = False

    def command_issued(self, owner_id: str | None = None) -> CommandEchoState:
        """Return state after issuing a command."""
        return CommandEchoState(
            owner_id=owner_id if owner_id is not None else self.owner_id,
            controlling=True,
            awaiting_echo=True,
        )

    def command_completed(self) -> CommandEchoState:
        """Return state after receiving an expected echo."""
        return CommandEchoState(
            owner_id=self.owner_id,
            controlling=self.controlling,
            awaiting_echo=False,
        )

    def external_change(self) -> CommandEchoState:
        """Return neutral state after non-owned change."""
        return CommandEchoState()

    def set_controlling(self, controlling: bool) -> CommandEchoState:
        """Return state with updated controlling flag."""
        return CommandEchoState(
            owner_id=self.owner_id,
            controlling=controlling,
            awaiting_echo=self.awaiting_echo,
        )


CONTROLLED_READY_STATE = CommandEchoState(controlling=True, awaiting_echo=False)


class LightAction(StrEnum):
    """Light group action to take."""

    TURN_ON = auto()
    TURN_OFF = auto()
    NOOP = auto()


class ActOnMode(StrEnum):
    """When light group should act."""

    OCCUPANCY_CHANGE = "occupancy"  # Act when occupancy changes
    STATE_CHANGE = "state"  # Act when secondary states change


class BrightnessMode(StrEnum):
    """How BRIGHT state influences light-group automation."""

    INHIBIT = "inhibit"
    ADVISORY = "advisory"
    ADAPTIVE = "adaptive"


@dataclass(slots=True)
class LightGroupDecision:
    """Light group control decision result."""

    action: LightAction
    reason: str
    should_track_control: bool = False
    reset_control: bool = False
    next_control_state: CommandEchoState | None = None


@dataclass(slots=True)
class LightGroupPolicy:
    """Policy for controlling a light group based on area-state transitions."""

    assigned_states: Sequence[str]
    act_on_modes: Sequence[str]
    brightness_mode: str = BrightnessMode.INHIBIT.value
    bright_min_on_seconds: int = 0
    bright_dwell_seconds: int = 0
    outside_context_source: str = "sun"
    outside_lux_entity: str | None = None
    outside_lux_min: int = 0
    outside_lux_inside_entity: str | None = None
    outside_lux_inside_delta: int = 0
    outside_lux_inside_ratio_min_percent: int = 0
    bright_attribution_hold_seconds: int = 0
    adaptive_require_ambient_rise: bool = False
    ambient_rise_window_seconds: int = 120
    ambient_rise_min_delta: int = 20
    use_priority_filtering: bool = True

    @staticmethod
    def _decision(
        action: LightAction,
        reason: str,
        *,
        should_track_control: bool = False,
        reset_control: bool = False,
        next_control_state: CommandEchoState | None = None,
    ) -> LightGroupDecision:
        """Build a policy decision in one place."""
        return LightGroupDecision(
            action=action,
            reason=reason,
            should_track_control=should_track_control,
            reset_control=reset_control,
            next_control_state=next_control_state,
        )

    def evaluate(
        self,
        new_states: Sequence[str],
        lost_states: Sequence[str],
        current_states: Sequence[str],
        *,
        bright_dwell_met: bool = True,
        min_on_met: bool = True,
        outside_context_ok: bool = True,
        attribution_hold_met: bool = True,
        ambient_rise_met: bool = True,
    ) -> LightGroupDecision:
        """Evaluate a secondary-group light action from area state transitions."""
        current_state_set = set(current_states)

        if AreaStates.CLEAR in new_states:
            return self._decision(LightAction.NOOP, "area_clear", reset_control=True)

        if (
            AreaStates.BRIGHT in current_state_set
            and AreaStates.BRIGHT not in self.assigned_states
        ):
            if self.brightness_mode == BrightnessMode.ADVISORY.value:
                return self._decision(LightAction.NOOP, "bright_advisory_ignore")
            if (
                AreaStates.BRIGHT in new_states
                and AreaStates.OCCUPIED not in new_states
            ):
                if self.brightness_mode == BrightnessMode.ADAPTIVE.value:
                    if not bright_dwell_met:
                        return self._decision(
                            LightAction.NOOP,
                            "bright_adaptive_waiting_dwell",
                        )
                    if not min_on_met:
                        return self._decision(
                            LightAction.NOOP,
                            "bright_adaptive_waiting_min_on",
                        )
                    if not outside_context_ok:
                        return self._decision(
                            LightAction.NOOP,
                            "bright_adaptive_outside_context_blocked",
                        )
                    if not attribution_hold_met:
                        return self._decision(
                            LightAction.NOOP,
                            "bright_adaptive_attribution_hold",
                        )
                    if self.adaptive_require_ambient_rise and not ambient_rise_met:
                        return self._decision(
                            LightAction.NOOP,
                            "bright_adaptive_waiting_ambient_rise",
                        )
                return self._decision(
                    LightAction.TURN_OFF,
                    "bright_not_assigned",
                    should_track_control=True,
                )
            return self._decision(LightAction.NOOP, "bright_active_but_stable")

        if not new_states and not lost_states:
            return self._decision(LightAction.NOOP, "no_state_changes")

        if not self.assigned_states:
            return self._decision(LightAction.NOOP, "no_assigned_states")

        if AreaStates.OCCUPIED not in current_state_set:
            return self._decision(LightAction.NOOP, "not_occupied")

        # Sleep is globally suppressive for regular light behaviors.
        # Only groups explicitly assigned to SLEEP should remain active.
        if (
            AreaStates.SLEEP in current_state_set
            and AreaStates.SLEEP not in self.assigned_states
        ):
            if AreaStates.SLEEP in new_states:
                return self._decision(
                    LightAction.TURN_OFF,
                    "sleep_not_assigned",
                    should_track_control=True,
                )
            return self._decision(LightAction.NOOP, "sleep_active_not_assigned")

        valid_states = [
            state for state in self.assigned_states if state in current_state_set
        ]

        if self.use_priority_filtering:
            valid_states = filter_by_priority(valid_states, LIGHT_PRIORITY_STATES)

        if AreaStates.OCCUPIED in new_states:
            if ActOnMode.OCCUPANCY_CHANGE not in self.act_on_modes:
                return self._decision(
                    LightAction.NOOP, "occupancy_change_not_configured"
                )
        else:
            if ActOnMode.STATE_CHANGE not in self.act_on_modes:
                return self._decision(LightAction.NOOP, "state_change_not_configured")

        if valid_states:
            return self._decision(
                LightAction.TURN_ON,
                f"valid_states_present ({', '.join(valid_states)})",
                should_track_control=True,
            )

        if AreaStates.DARK in new_states:
            return self._decision(LightAction.NOOP, "entering_dark")

        out_of_priority = [
            s for s in LIGHT_PRIORITY_STATES
            if s in self.assigned_states and s in lost_states
        ]
        if out_of_priority:
            return self._decision(
                LightAction.TURN_OFF,
                f"leaving_priority_states ({', '.join(out_of_priority)})",
                should_track_control=True,
            )

        new_priority = [s for s in LIGHT_PRIORITY_STATES if s in new_states]
        if not new_priority:
            return self._decision(LightAction.NOOP, "no_new_priority_states")

        return self._decision(
            LightAction.TURN_OFF,
            "no_valid_states",
            should_track_control=True,
        )

    def evaluate_control_context(
        self,
        *,
        new_states: Sequence[str],
        lost_states: Sequence[str],
        current_states: Sequence[str],
        control_state: object,
        is_primary: bool,
        bright_dwell_met: bool = True,
        min_on_met: bool = True,
        outside_context_ok: bool = True,
        attribution_hold_met: bool = True,
        ambient_rise_met: bool = True,
    ) -> LightGroupDecision:
        """Evaluate a light group decision from explicit control-context fields."""
        if not isinstance(control_state, CommandEchoState):
            msg = "control_state must be CommandEchoState"
            raise TypeError(msg)

        if is_primary:
            if AreaStates.CLEAR in new_states:
                return self._decision(
                    LightAction.TURN_OFF,
                    "area_clear",
                    next_control_state=CONTROLLED_READY_STATE,
                )
            return self._decision(LightAction.NOOP, "primary_noop")

        decision = self.evaluate(
            new_states=new_states,
            lost_states=lost_states,
            current_states=current_states,
            bright_dwell_met=bright_dwell_met,
            min_on_met=min_on_met,
            outside_context_ok=outside_context_ok,
            attribution_hold_met=attribution_hold_met,
            ambient_rise_met=ambient_rise_met,
        )

        # Preserve manual override: if another actor owns the group, do not
        # auto-reclaim control via policy actions.
        if decision.should_track_control and not control_state.controlling:
            return self._decision(LightAction.NOOP, "manual_override_active")

        next_control_state: CommandEchoState | None = None
        if decision.should_track_control:
            next_control_state = control_state.command_issued()
        elif decision.reset_control:
            next_control_state = CONTROLLED_READY_STATE

        return self._decision(
            decision.action,
            decision.reason,
            next_control_state=next_control_state,
        )


@dataclass(slots=True)
class LightControlGroupPolicy(ControlGroupPolicy):
    """Canonical control-group adapter for light group policy evaluation."""

    policy: LightGroupPolicy
    light_group_entity_id: str

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Evaluate canonical control-group context for light actions."""
        decision = self._evaluate_light_decision(context)
        mapped = light_action_to_control_group(decision.action, self.light_group_entity_id)
        runtime_effects: tuple[ControlRuntimeEffect, ...] = ()
        if decision.next_control_state is not None:
            runtime_effects = (
                ControlRuntimeEffect(
                    effect_type=ControlRuntimeEffectType.SET_STATE,
                    namespace="command_echo",
                    key="state",
                    value=decision.next_control_state,
                ),
            )
        return ControlGroupDecision(
            action_type=mapped.action_type,
            actions=mapped.actions,
            reason=decision.reason,
            runtime_effects=runtime_effects,
        )

    def _evaluate_light_decision(self, context: ControlGroupContext) -> LightGroupDecision:
        """Map canonical control-group context into light policy evaluation."""
        signals = LightPolicySignals.from_signals(context.signals)
        if signals.fallback_used and signals.is_primary is None:
            _LOGGER.warning(
                "Light policy signals missing primary-group identity; skipping light action."
            )
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="invalid_light_policy_signals",
            )
        if signals.is_primary is None:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="missing_primary_flag",
            )
        return self.policy.evaluate_control_context(
            new_states=context.new_states,
            lost_states=context.lost_states,
            current_states=context.current_states,
            control_state=signals.control_state,
            is_primary=signals.is_primary,
            bright_dwell_met=signals.bright_dwell_met,
            min_on_met=signals.min_on_met,
            outside_context_ok=signals.outside_context_ok,
            attribution_hold_met=signals.attribution_hold_met,
            ambient_rise_met=signals.ambient_rise_met,
        )


def build_light_control_group_policy(
    *,
    assigned_states: Sequence[str],
    act_on_modes: Sequence[str],
    brightness_mode: str = BrightnessMode.INHIBIT.value,
    bright_min_on_seconds: int = 0,
    bright_dwell_seconds: int = 0,
    outside_context_source: str = "sun",
    outside_lux_entity: str | None = None,
    outside_lux_min: int = 0,
    outside_lux_inside_entity: str | None = None,
    outside_lux_inside_delta: int = 0,
    outside_lux_inside_ratio_min_percent: int = 0,
    bright_attribution_hold_seconds: int = 0,
    adaptive_require_ambient_rise: bool = False,
    ambient_rise_window_seconds: int = 120,
    ambient_rise_min_delta: int = 20,
    light_group_entity_id: str,
) -> LightControlGroupPolicy:
    """Build canonical light control-group policy adapter."""
    return LightControlGroupPolicy(
        policy=LightGroupPolicy(
            assigned_states=assigned_states,
            act_on_modes=act_on_modes,
            brightness_mode=brightness_mode,
            bright_min_on_seconds=max(0, int(bright_min_on_seconds)),
            bright_dwell_seconds=max(0, int(bright_dwell_seconds)),
            outside_context_source=outside_context_source,
            outside_lux_entity=outside_lux_entity,
            outside_lux_min=max(0, int(outside_lux_min)),
            outside_lux_inside_entity=outside_lux_inside_entity,
            outside_lux_inside_delta=max(0, int(outside_lux_inside_delta)),
            outside_lux_inside_ratio_min_percent=max(
                0, int(outside_lux_inside_ratio_min_percent)
            ),
            bright_attribution_hold_seconds=max(0, int(bright_attribution_hold_seconds)),
            adaptive_require_ambient_rise=bool(adaptive_require_ambient_rise),
            ambient_rise_window_seconds=max(0, int(ambient_rise_window_seconds)),
            ambient_rise_min_delta=max(0, int(ambient_rise_min_delta)),
            use_priority_filtering=True,
        ),
        light_group_entity_id=light_group_entity_id,
    )


@dataclass(frozen=True, slots=True)
class LightPolicySignals:
    """Typed runtime inputs for light policy adapters."""

    is_primary: bool | None
    control_state: CommandEchoState
    bright_dwell_met: bool = True
    min_on_met: bool = True
    outside_context_ok: bool = True
    attribution_hold_met: bool = True
    ambient_rise_met: bool = True
    fallback_used: bool = False

    @staticmethod
    def _default_control_state() -> CommandEchoState:
        """Return fallback command-echo state for malformed signals."""
        return CONTROLLED_READY_STATE

    @classmethod
    def from_signals(cls, signals: object) -> LightPolicySignals:
        """Parse typed light signals from control-group context."""
        if isinstance(signals, cls):
            return signals
        if isinstance(signals, Mapping):
            is_primary_raw = signals.get("is_primary")
            is_primary = is_primary_raw if isinstance(is_primary_raw, bool) else None
            control_state_raw = signals.get("control_state")
            control_state = (
                control_state_raw
                if isinstance(control_state_raw, CommandEchoState)
                else cls._default_control_state()
            )
            bright_dwell_raw = signals.get("bright_dwell_met")
            min_on_raw = signals.get("min_on_met")
            outside_context_raw = signals.get("outside_context_ok")
            attribution_hold_raw = signals.get("attribution_hold_met")
            ambient_rise_raw = signals.get("ambient_rise_met")
            return cls(
                is_primary=is_primary,
                control_state=control_state,
                bright_dwell_met=(
                    bright_dwell_raw if isinstance(bright_dwell_raw, bool) else True
                ),
                min_on_met=min_on_raw if isinstance(min_on_raw, bool) else True,
                outside_context_ok=(
                    outside_context_raw
                    if isinstance(outside_context_raw, bool)
                    else True
                ),
                attribution_hold_met=(
                    attribution_hold_raw
                    if isinstance(attribution_hold_raw, bool)
                    else True
                ),
                ambient_rise_met=(
                    ambient_rise_raw
                    if isinstance(ambient_rise_raw, bool)
                    else True
                ),
                fallback_used=(
                    is_primary is None
                    or not isinstance(control_state_raw, CommandEchoState)
                ),
            )
        return cls(
            is_primary=None,
            control_state=cls._default_control_state(),
            fallback_used=True,
        )


def light_action_to_control_group(
    action: LightAction, light_group_entity_id: str
) -> ControlGroupDecision:
    """Translate a light group action into control-group execution form."""
    service_map: dict[LightAction, tuple[ControlActionType, str, str]] = {
        LightAction.TURN_ON: (
            ControlActionType.ACTIVATE,
            "light_turn_on",
            SERVICE_TURN_ON,
        ),
        LightAction.TURN_OFF: (
            ControlActionType.DEACTIVATE,
            "light_turn_off",
            SERVICE_TURN_OFF,
        ),
    }
    mapped = service_map.get(action)
    if mapped is not None:
        action_type, reason, service = mapped
        return ControlGroupDecision(
            action_type=action_type,
            reason=reason,
            actions=(
                ControlAction(
                    domain=LIGHT_DOMAIN,
                    service=service,
                    target_entity_ids=(light_group_entity_id,),
                ),
            ),
        )

    return ControlGroupDecision(action_type=ControlActionType.NOOP, reason="light_noop")
