"""Tests for the light-group control intent adapter."""

from __future__ import annotations

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.control_intents import (
    ControlTargetKind,
    ControlTargetPrecision,
    ControlTargetSource,
    IntentAction,
    IntentReason,
    RoleTarget,
)
from custom_components.magic_areas.light_groups.intent_adapter import (
    evaluate_light_member_suppression,
    evaluate_light_policy_with_intent_engine,
    light_decision_from_intent_decision,
)
from custom_components.magic_areas.light_groups.policy import (
    ActOnMode,
    CommandEchoState,
    LightAction,
    LightGroupPolicy,
)


def _target() -> RoleTarget:
    """Build a light target for adapter tests."""
    return RoleTarget(
        role="light_group",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.RECONCILED_LABEL,
        entity_ids=("light.lamp",),
    )


def _multi_light_target() -> RoleTarget:
    """Build a target containing all overlap matrix members."""
    return RoleTarget(
        role="all_lights",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.CONFIG_RECONCILIATION,
        entity_ids=(
            "light.sleep_accent_lamp",
            "light.sleep_lamp",
            "light.accent_lamp",
            "light.neither_lamp",
        ),
    )


def test_adapter_preserves_turn_on_behavior_for_valid_light_state() -> None:
    """Adapter should represent current turn-on decisions as activate intents."""
    light_decision, intent_decision = evaluate_light_policy_with_intent_engine(
        LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        ),
        target=_target(),
        new_states=[AreaStates.DARK],
        lost_states=[],
        current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        control_state=CommandEchoState(controlling=True),
        is_primary=False,
    )

    assert light_decision.action is LightAction.TURN_ON
    assert intent_decision is not None
    assert intent_decision.action is IntentAction.ACTIVATE
    assert intent_decision.reason is IntentReason.INTENT_ALLOWED
    assert intent_decision.reason_detail == light_decision.reason
    assert intent_decision.target_entity_ids == ("light.lamp",)


def test_adapter_preserves_sleep_suppression_noop() -> None:
    """Sleep suppression remains current policy behavior in Phase 3."""
    light_decision, intent_decision = evaluate_light_policy_with_intent_engine(
        LightGroupPolicy(
            assigned_states=[AreaStates.OCCUPIED],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
        ),
        target=_target(),
        new_states=[AreaStates.OCCUPIED],
        lost_states=[],
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
        control_state=CommandEchoState(controlling=True),
        is_primary=False,
    )

    assert light_decision.action is LightAction.NOOP
    assert light_decision.reason == "sleep_active_not_assigned"
    assert intent_decision is None


def test_adapter_preserves_accent_turn_off_behavior() -> None:
    """Accent suppression turn-off decisions should translate to deactivate."""
    light_decision, intent_decision = evaluate_light_policy_with_intent_engine(
        LightGroupPolicy(
            assigned_states=[AreaStates.OCCUPIED],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        ),
        target=_target(),
        new_states=[AreaStates.ACCENT],
        lost_states=[],
        current_states=[AreaStates.OCCUPIED, AreaStates.ACCENT],
        control_state=CommandEchoState(controlling=True),
        is_primary=False,
    )

    assert light_decision.action is LightAction.TURN_OFF
    assert light_decision.reason == "accent_not_assigned"
    assert intent_decision is not None
    assert intent_decision.action is IntentAction.DEACTIVATE
    assert intent_decision.reason_detail == "accent_not_assigned"


def test_adapter_preserves_manual_override_noop() -> None:
    """Manual override remains a legacy policy noop before engine migration."""
    light_decision, intent_decision = evaluate_light_policy_with_intent_engine(
        LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        ),
        target=_target(),
        new_states=[AreaStates.DARK],
        lost_states=[],
        current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        control_state=CommandEchoState(controlling=False),
        is_primary=False,
    )

    assert light_decision.action is LightAction.NOOP
    assert light_decision.reason == "manual_override_active"
    assert intent_decision is None


def test_adapter_preserves_brightness_noop() -> None:
    """Brightness inhibit behavior remains unchanged in Phase 3."""
    light_decision, intent_decision = evaluate_light_policy_with_intent_engine(
        LightGroupPolicy(
            assigned_states=[AreaStates.OCCUPIED],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE],
            brightness_mode="advisory",
        ),
        target=_target(),
        new_states=[AreaStates.OCCUPIED],
        lost_states=[],
        current_states=[AreaStates.OCCUPIED],
        control_state=CommandEchoState(controlling=True),
        is_primary=False,
        inside_bright_met=True,
    )

    assert light_decision.action is LightAction.NOOP
    assert light_decision.reason == "bright_advisory_inhibit_turn_on"
    assert intent_decision is None


def test_adaptive_brightness_blocks_stable_bright_turn_on() -> None:
    """Adaptive mode should not re-enable lights on state changes while already bright."""
    light_decision, intent_decision = evaluate_light_policy_with_intent_engine(
        LightGroupPolicy(
            assigned_states=[AreaStates.OCCUPIED, AreaStates.EXTENDED],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
            brightness_mode="adaptive",
        ),
        target=_target(),
        new_states=[AreaStates.EXTENDED],
        lost_states=[],
        current_states=[AreaStates.OCCUPIED, AreaStates.EXTENDED, AreaStates.BRIGHT],
        control_state=CommandEchoState(controlling=True),
        is_primary=False,
    )

    assert light_decision.action is LightAction.NOOP
    assert light_decision.reason == "bright_adaptive_inhibit_turn_on"
    assert intent_decision is None


def test_light_decision_from_intent_decision_preserves_legacy_reason() -> None:
    """Adapter should round-trip allowed intent reasons into light decisions."""
    _light_decision, intent_decision = evaluate_light_policy_with_intent_engine(
        LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        ),
        target=_target(),
        new_states=[AreaStates.DARK],
        lost_states=[],
        current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        control_state=CommandEchoState(controlling=True),
        is_primary=False,
    )
    assert intent_decision is not None

    converted = light_decision_from_intent_decision(
        intent_decision,
        should_track_control=True,
    )

    assert converted.action is LightAction.TURN_ON
    assert converted.reason == "valid_states_present (dark)"
    assert converted.should_track_control


def test_member_suppression_sleep_state_allows_only_sleep_members() -> None:
    """Sleep state should suppress non-sleep members at entity level."""
    decision = evaluate_light_member_suppression(
        target=_multi_light_target(),
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
        sleep_entity_ids=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_entity_ids=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.reason is IntentReason.TARGET_PARTIALLY_SUPPRESSED
    assert decision.target_entity_ids == (
        "light.sleep_accent_lamp",
        "light.sleep_lamp",
    )
    assert decision.applied_constraints == ("sleep_suppression",)


def test_member_suppression_accent_state_allows_only_accent_members() -> None:
    """Accent state should suppress non-accent members at entity level."""
    decision = evaluate_light_member_suppression(
        target=_multi_light_target(),
        current_states=[AreaStates.OCCUPIED, AreaStates.ACCENT],
        sleep_entity_ids=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_entity_ids=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.reason is IntentReason.TARGET_PARTIALLY_SUPPRESSED
    assert decision.target_entity_ids == (
        "light.sleep_accent_lamp",
        "light.accent_lamp",
    )
    assert decision.applied_constraints == ("accent_suppression",)


def test_member_suppression_sleep_and_accent_allows_only_overlap() -> None:
    """Sleep plus accent should allow only members present in both roles."""
    decision = evaluate_light_member_suppression(
        target=_multi_light_target(),
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP, AreaStates.ACCENT],
        sleep_entity_ids=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_entity_ids=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.reason is IntentReason.TARGET_PARTIALLY_SUPPRESSED
    assert decision.target_entity_ids == ("light.sleep_accent_lamp",)
    assert decision.applied_constraints == (
        "sleep_suppression",
        "accent_suppression",
    )


def test_member_suppression_allows_target_already_in_overlap() -> None:
    """A target already in all active suppressive roles should remain allowed."""
    target = RoleTarget(
        role="sleep_accent",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.CONFIG_RECONCILIATION,
        entity_ids=("light.sleep_accent_lamp",),
    )

    decision = evaluate_light_member_suppression(
        target=target,
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP, AreaStates.ACCENT],
        sleep_entity_ids=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_entity_ids=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.reason is IntentReason.INTENT_ALLOWED
    assert decision.target_entity_ids == ("light.sleep_accent_lamp",)
    assert decision.applied_constraints == ()


def test_member_suppression_noops_when_no_target_members_survive() -> None:
    """Neither-members should be fully suppressed when suppressive states overlap."""
    target = RoleTarget(
        role="all_lights",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.RECONCILED_LABEL,
        entity_ids=("light.neither_lamp",),
    )

    decision = evaluate_light_member_suppression(
        target=target,
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP, AreaStates.ACCENT],
        sleep_entity_ids=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_entity_ids=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    assert decision.is_noop
    assert decision.reason is IntentReason.TARGET_SUPPRESSED
    assert decision.target_entity_ids == ()
    assert decision.applied_constraints == ("sleep_suppression",)


def test_member_suppression_without_suppressive_states_allows_full_target() -> None:
    """Without sleep/accent state, suppression should not narrow the target."""
    decision = evaluate_light_member_suppression(
        target=_multi_light_target(),
        current_states=[AreaStates.OCCUPIED],
        sleep_entity_ids=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_entity_ids=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.reason is IntentReason.INTENT_ALLOWED
    assert decision.target_entity_ids == _multi_light_target().entity_ids
    assert decision.applied_constraints == ()


def test_member_suppression_preserves_broad_label_target_when_safe() -> None:
    """Broad labels remain valid when no suppression subset is required."""
    target = RoleTarget(
        role="accent",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.LABEL,
        precision=ControlTargetPrecision.BROAD,
        source=ControlTargetSource.RECONCILED_LABEL,
        label_name="ma:accent",
        label_id="ma_accent",
    )

    decision = evaluate_light_member_suppression(
        target=target,
        current_states=[AreaStates.OCCUPIED],
        accent_entity_ids=("light.accent_lamp",),
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.reason is IntentReason.INTENT_ALLOWED
    assert decision.target is target
    assert decision.target_entity_ids == ()
