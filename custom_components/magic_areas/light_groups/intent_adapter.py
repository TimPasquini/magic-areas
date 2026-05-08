"""Light-group adapter for the pure control intent engine."""

from __future__ import annotations

from collections.abc import Sequence

from custom_components.magic_areas.core.control_intents import (
    ControlIntent,
    IntentAction,
    IntentDecision,
    IntentReason,
    RoleTarget,
    evaluate_intent,
)
from custom_components.magic_areas.light_groups.policy import (
    CommandEchoState,
    LightAction,
    LightGroupDecision,
    LightGroupPolicy,
)


def evaluate_light_policy_with_intent_engine(
    policy: LightGroupPolicy,
    *,
    target: RoleTarget,
    new_states: Sequence[str],
    lost_states: Sequence[str],
    current_states: Sequence[str],
    control_state: CommandEchoState,
    is_primary: bool,
    bright_dwell_met: bool = True,
    min_on_met: bool = True,
    inside_bright_met: bool | None = None,
    outside_context_ok: bool = True,
    attribution_hold_met: bool = True,
    ambient_rise_met: bool = True,
) -> tuple[LightGroupDecision, IntentDecision | None]:
    """Evaluate legacy light policy and produce a matching intent decision.

    Phase 3 keeps the legacy light policy authoritative while proving the adapter
    can translate current decisions into engine-shaped records without behavior
    changes.
    """
    light_decision = policy.evaluate_control_context(
        new_states=new_states,
        lost_states=lost_states,
        current_states=current_states,
        control_state=control_state,
        is_primary=is_primary,
        bright_dwell_met=bright_dwell_met,
        min_on_met=min_on_met,
        inside_bright_met=inside_bright_met,
        outside_context_ok=outside_context_ok,
        attribution_hold_met=attribution_hold_met,
        ambient_rise_met=ambient_rise_met,
    )
    if light_decision.action is LightAction.NOOP:
        return light_decision, None

    intent_decision = evaluate_intent(
        ControlIntent(
            intent_id="light_group",
            action=_intent_action_for_light_action(light_decision.action),
            target=target,
            reason=light_decision.reason,
        )
    )
    return light_decision, intent_decision


def light_decision_from_intent_decision(
    intent_decision: IntentDecision,
    *,
    should_track_control: bool = False,
    reset_control: bool = False,
    next_control_state: CommandEchoState | None = None,
) -> LightGroupDecision:
    """Convert a pure intent decision back into the current light decision shape."""
    return LightGroupDecision(
        action=_light_action_for_intent_action(intent_decision.action),
        reason=_light_reason_from_intent_decision(intent_decision),
        should_track_control=should_track_control,
        reset_control=reset_control,
        next_control_state=next_control_state,
    )


def _intent_action_for_light_action(action: LightAction) -> IntentAction:
    """Map current light actions to generic intent actions."""
    if action is LightAction.TURN_ON:
        return IntentAction.ACTIVATE
    if action is LightAction.TURN_OFF:
        return IntentAction.DEACTIVATE
    return IntentAction.NOOP


def _light_action_for_intent_action(action: IntentAction) -> LightAction:
    """Map generic intent actions to current light actions."""
    if action is IntentAction.ACTIVATE:
        return LightAction.TURN_ON
    if action is IntentAction.DEACTIVATE:
        return LightAction.TURN_OFF
    return LightAction.NOOP


def _light_reason_from_intent_decision(intent_decision: IntentDecision) -> str:
    """Preserve legacy light reasons when the adapter carries one."""
    if intent_decision.reason is IntentReason.INTENT_ALLOWED:
        return intent_decision.reason_detail or intent_decision.reason.value
    if intent_decision.reason_detail:
        return f"{intent_decision.reason.value}: {intent_decision.reason_detail}"
    return intent_decision.reason.value


__all__ = [
    "evaluate_light_policy_with_intent_engine",
    "light_decision_from_intent_decision",
]
