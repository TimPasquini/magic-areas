"""Light group control policy for Magic Areas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON

from custom_components.magic_areas.core.state_priority import (
    filter_by_priority,
    LIGHT_PRIORITY_STATES,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.command_echo import CommandEchoState
from custom_components.magic_areas.core.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
    ControlRuntimeEffect,
    ControlRuntimeEffectType,
)

class LightAction(StrEnum):
    """Light group action to take."""

    TURN_ON = auto()
    TURN_OFF = auto()
    NOOP = auto()


class ActOnMode(StrEnum):
    """When light group should act."""

    OCCUPANCY_CHANGE = "occupancy"  # Act when occupancy changes
    STATE_CHANGE = "state"  # Act when secondary states change


@dataclass(slots=True)
class LightGroupDecision:
    """Light group control decision result."""

    action: LightAction
    reason: str  # For debugging/logging
    should_track_control: bool = False  # Whether to mark as "controlled by MA"
    reset_control: bool = False  # Whether to clear the "controlled" flag
    next_control_state: CommandEchoState | None = None  # Optional control state update


@dataclass(slots=True)
class LightGroupPolicyInput:
    """Policy input for an area state change."""

    new_states: Sequence[str]
    lost_states: Sequence[str]
    current_states: Sequence[str]
    control_state: Any
    is_primary: bool


@dataclass(slots=True)
class LightGroupPolicy:
    """Policy for controlling a light group based on area states.

    Attributes:
        assigned_states: States this light group reacts to (e.g., ["sleep", "dark"] for sleep lights)
        act_on_modes: When to act (["occupancy", "state"] or subset)
        use_priority_filtering: Whether to filter by priority states

    """

    assigned_states: Sequence[str]
    act_on_modes: Sequence[str]
    use_priority_filtering: bool = True

    def evaluate(
        self,
        new_states: Sequence[str],
        lost_states: Sequence[str],
        current_states: Sequence[str],
    ) -> LightGroupDecision:
        """Evaluate whether light group should turn on, off, or do nothing.

        Args:
            new_states: States just added
            lost_states: States just lost
            current_states: All currently active states

        Returns:
            LightGroupDecision with action and reason

        Logic:
            1. CLEAR → noop + reset_control flag
            2. BRIGHT (not assigned to it) → turn off if BRIGHT just added without OCCUPIED
            3. No changes → noop
            4. No assigned states → noop
            5. Not occupied → noop
            6. Filter to valid states (assigned & current)
            7. Apply priority filtering if enabled
            8. Check act-on modes (occupancy vs state change)
            9. If valid states remain → turn on
            10. If no valid states:
                a. DARK just entered → noop (dark mode takes its own control path)
                b. Leaving an assigned priority state → turn off, take control
                c. No new priority states → noop
                d. New priority state entered → turn off, take control

        """
        current_state_set = set(current_states)

        # (1) CLEAR state → noop; signal caller to reset control tracking
        if AreaStates.CLEAR in new_states:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="area_clear",
                reset_control=True,
            )

        # (2) BRIGHT state special logic
        if (
            AreaStates.BRIGHT in current_state_set
            and AreaStates.BRIGHT not in self.assigned_states
        ):
            # Only turn off if BRIGHT just added AND not occupancy change
            if (
                AreaStates.BRIGHT in new_states
                and AreaStates.OCCUPIED not in new_states
            ):
                return LightGroupDecision(
                    action=LightAction.TURN_OFF,
                    reason="bright_not_assigned",
                    should_track_control=True,
                )
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="bright_active_but_stable",
            )

        # (3) No changes → noop
        if not new_states and not lost_states:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="no_state_changes",
            )

        # (4) No assigned states → noop
        if not self.assigned_states:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="no_assigned_states",
            )

        # (5) Not occupied → noop
        if AreaStates.OCCUPIED not in current_state_set:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="not_occupied",
            )

        # (6) Filter to valid states
        valid_states = [
            state for state in self.assigned_states if state in current_state_set
        ]

        # (7) Apply priority filtering
        if self.use_priority_filtering:
            valid_states = filter_by_priority(valid_states, LIGHT_PRIORITY_STATES)

        # (8) Check act-on modes
        if AreaStates.OCCUPIED in new_states:
            # Occupancy change
            if ActOnMode.OCCUPANCY_CHANGE not in self.act_on_modes:
                return LightGroupDecision(
                    action=LightAction.NOOP,
                    reason="occupancy_change_not_configured",
                )
        else:
            # State change (not occupancy)
            if ActOnMode.STATE_CHANGE not in self.act_on_modes:
                return LightGroupDecision(
                    action=LightAction.NOOP,
                    reason="state_change_not_configured",
                )

        # (9) Valid states → turn on
        if valid_states:
            return LightGroupDecision(
                action=LightAction.TURN_ON,
                reason=f"valid_states_present ({', '.join(valid_states)})",
                should_track_control=True,
            )

        # (10) No valid states — determine whether and why to turn off
        # (10a) Don't turn off if entering dark (dark mode handles its own control path)
        if AreaStates.DARK in new_states:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="entering_dark",
            )

        # (10b) Turn off if leaving an assigned priority state
        out_of_priority = [
            s for s in LIGHT_PRIORITY_STATES
            if s in self.assigned_states and s in lost_states
        ]
        if out_of_priority:
            return LightGroupDecision(
                action=LightAction.TURN_OFF,
                reason=f"leaving_priority_states ({', '.join(out_of_priority)})",
                should_track_control=True,
            )

        # (10c) Don't turn off if no new priority states are being entered
        new_priority = [s for s in LIGHT_PRIORITY_STATES if s in new_states]
        if not new_priority:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="no_new_priority_states",
            )

        # (10d) Entering a new priority state this group isn't assigned to — turn off
        return LightGroupDecision(
            action=LightAction.TURN_OFF,
            reason="no_valid_states",
            should_track_control=True,
        )

    def evaluate_area_state_change(
        self, context: LightGroupPolicyInput
    ) -> LightGroupDecision:
        """Evaluate a light group decision for an area state change."""
        if context.is_primary:
            if AreaStates.CLEAR in context.new_states:
                return LightGroupDecision(
                    action=LightAction.TURN_OFF,
                    reason="area_clear",
                    next_control_state=CommandEchoState(
                        controlling=True, awaiting_echo=False
                    ),
                )
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="primary_noop",
            )

        decision = self.evaluate(
            new_states=context.new_states,
            lost_states=context.lost_states,
            current_states=context.current_states,
        )

        next_control_state: CommandEchoState | None = None
        if decision.should_track_control:
            next_control_state = _as_echo_state(context.control_state.command_issued())
        elif decision.reset_control:
            next_control_state = CommandEchoState(controlling=True, awaiting_echo=False)

        return LightGroupDecision(
            action=decision.action,
            reason=decision.reason,
            next_control_state=next_control_state,
        )


def resolve_light_category_config(
    category: str,
    feature_config: dict,
    light_group_states_map: dict,
    light_group_act_on_map: dict,
    default_act_on: Sequence[str],
) -> tuple[list[str], list[str]]:
    """Resolve assigned states and act-on modes for a light category.

    Args:
        category: Light category (overhead, sleep, accent, task)
        feature_config: Feature configuration dict
        light_group_states_map: Map from category to config key for states
        light_group_act_on_map: Map from category to config key for act-on modes
        default_act_on: Default act-on modes to use

    Returns:
        Tuple of (assigned_states, act_on_modes)

    """
    # No states/act-on if category not in maps
    if category not in light_group_states_map or category not in light_group_act_on_map:
        return [], list(default_act_on)

    # Get config keys for this category
    states_key = light_group_states_map[category]
    act_on_key = light_group_act_on_map[category]

    # Get values from feature config, with defaults
    assigned_states = feature_config.get(states_key, [])
    act_on = feature_config.get(act_on_key, default_act_on)

    return assigned_states, list(act_on)


def build_light_group_policy(
    assigned_states: Sequence[str],
    act_on_modes: Sequence[str],
) -> LightGroupPolicy:
    """Build light group policy from configuration.

    Args:
        assigned_states: States this light group reacts to
        act_on_modes: When to act (occupancy/state change)

    Returns:
        Configured LightGroupPolicy

    """
    return LightGroupPolicy(
        assigned_states=assigned_states,
        act_on_modes=act_on_modes,
        use_priority_filtering=True,
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
        """Map canonical context into the legacy light policy input model."""
        signals = LightPolicySignals.from_signals(context.signals)
        return self.policy.evaluate_area_state_change(
            LightGroupPolicyInput(
                new_states=context.new_states,
                lost_states=context.lost_states,
                current_states=context.current_states,
                control_state=signals.control_state,
                is_primary=signals.is_primary,
            )
        )


def build_light_control_group_policy(
    *,
    assigned_states: Sequence[str],
    act_on_modes: Sequence[str],
    light_group_entity_id: str,
) -> LightControlGroupPolicy:
    """Build canonical light control-group policy adapter."""
    return LightControlGroupPolicy(
        policy=build_light_group_policy(
            assigned_states=assigned_states,
            act_on_modes=act_on_modes,
        ),
        light_group_entity_id=light_group_entity_id,
    )


@dataclass(frozen=True, slots=True)
class LightPolicySignals:
    """Typed runtime inputs for light policy adapters."""

    is_primary: bool
    control_state: CommandEchoState

    @classmethod
    def from_signals(cls, signals: Any) -> LightPolicySignals:
        """Parse typed light signals from control-group context."""
        if isinstance(signals, cls):
            return signals
        return cls(
            is_primary=False,
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
        )


def reset_control_state() -> CommandEchoState:
    """Reset control state to allow immediate command handling."""
    return CommandEchoState(controlling=True, awaiting_echo=False)


def update_primary_control_state(
    control_state: CommandEchoState, child_controlling: bool
) -> CommandEchoState:
    """Update control state for the primary (ALL) light group."""
    return control_state.set_controlling(child_controlling)


def update_secondary_control_state(control_state: CommandEchoState) -> CommandEchoState:
    """Update control state for secondary light group state changes."""
    if control_state.awaiting_echo:
        return control_state.command_completed()
    return control_state.external_change()


def _as_echo_state(state: Any) -> CommandEchoState:
    """Normalize legacy control-state objects to command-echo state."""
    if state is None:
        return CommandEchoState(controlling=True, awaiting_echo=False)
    if isinstance(state, CommandEchoState):
        return state
    if hasattr(state, "controlling") and hasattr(state, "awaiting_echo"):
        return CommandEchoState(
            controlling=bool(state.controlling),
            awaiting_echo=bool(state.awaiting_echo),
        )
    return CommandEchoState(
        controlling=bool(state.controlling),
        awaiting_echo=bool(state.controlled),
    )


def light_action_to_control_group(
    action: LightAction, light_group_entity_id: str
) -> ControlGroupDecision:
    """Translate a light group action into control-group execution form."""
    if action == LightAction.TURN_ON:
        return ControlGroupDecision(
            action_type=ControlActionType.ACTIVATE,
            reason="light_turn_on",
            actions=(
                ControlAction(
                    domain=LIGHT_DOMAIN,
                    service=SERVICE_TURN_ON,
                    target_entity_ids=(light_group_entity_id,),
                ),
            ),
        )

    if action == LightAction.TURN_OFF:
        return ControlGroupDecision(
            action_type=ControlActionType.DEACTIVATE,
            reason="light_turn_off",
            actions=(
                ControlAction(
                    domain=LIGHT_DOMAIN,
                    service=SERVICE_TURN_OFF,
                    target_entity_ids=(light_group_entity_id,),
                ),
            ),
        )

    return ControlGroupDecision(action_type=ControlActionType.NOOP, reason="light_noop")
