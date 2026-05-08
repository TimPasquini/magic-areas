"""Tests for the pure control intent engine skeleton."""

from __future__ import annotations

import ast
from pathlib import Path

from custom_components.magic_areas.core.control_intents import (
    ConstraintEffect,
    ControlIntent,
    ControlTargetKind,
    ControlTargetPrecision,
    ControlTargetSource,
    IntentAction,
    IntentConstraint,
    IntentReason,
    RoleTarget,
    evaluate_intent,
)


def _target(*entity_ids: str) -> RoleTarget:
    """Build an explicit target for pure engine tests."""
    return RoleTarget(
        role="sleep",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.RECONCILED_LABEL,
        entity_ids=entity_ids,
    )


def test_evaluate_intent_allows_executable_target_without_constraints() -> None:
    """Unconstrained intents should pass through unchanged."""
    target = _target("light.lamp", "light.soft_lamp")
    decision = evaluate_intent(
        ControlIntent(
            intent_id="sleep_light",
            action=IntentAction.ACTIVATE,
            target=target,
            reason="sleep_state_active",
        )
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.target is target
    assert decision.target_entity_ids == ("light.lamp", "light.soft_lamp")
    assert decision.reason is IntentReason.INTENT_ALLOWED
    assert decision.reason_detail == "sleep_state_active"


def test_evaluate_intent_noops_when_constraint_blocks_control() -> None:
    """NOOP constraints should win before target mutation."""
    target = _target("light.lamp")
    decision = evaluate_intent(
        ControlIntent(
            intent_id="regular_light",
            action=IntentAction.ACTIVATE,
            target=target,
        ),
        constraints=(
            IntentConstraint(
                constraint_id="manual_override",
                effect=ConstraintEffect.NOOP,
                reason="manual_override_active",
                priority=100,
            ),
        ),
    )

    assert decision.is_noop
    assert decision.reason is IntentReason.CONSTRAINT_NOOP
    assert decision.reason_detail == "manual_override_active"
    assert decision.applied_constraints == ("manual_override",)


def test_evaluate_intent_force_off_returns_deactivate_for_target_subset() -> None:
    """Force-off constraints should emit a deactivate subset decision."""
    target = _target("light.lamp", "light.overhead")
    decision = evaluate_intent(
        ControlIntent(
            intent_id="accent_light",
            action=IntentAction.ACTIVATE,
            target=target,
        ),
        constraints=(
            IntentConstraint(
                constraint_id="brightness_guard",
                effect=ConstraintEffect.FORCE_OFF,
                reason="room_bright",
                target_entity_ids=("light.overhead",),
            ),
        ),
    )

    assert decision.action is IntentAction.DEACTIVATE
    assert decision.reason is IntentReason.FORCE_OFF
    assert decision.reason_detail == "room_bright"
    assert decision.target_entity_ids == ("light.overhead",)


def test_evaluate_intent_suppresses_entire_target() -> None:
    """Suppressing all target members should become a noop."""
    target = _target("light.overhead", "light.task")
    decision = evaluate_intent(
        ControlIntent(
            intent_id="regular_light",
            action=IntentAction.ACTIVATE,
            target=target,
        ),
        constraints=(
            IntentConstraint(
                constraint_id="sleep_suppression",
                effect=ConstraintEffect.SUPPRESS,
                reason="sleep_active",
                target_entity_ids=("light.overhead", "light.task"),
            ),
        ),
    )

    assert decision.is_noop
    assert decision.reason is IntentReason.TARGET_SUPPRESSED
    assert decision.target_entity_ids == ()
    assert decision.applied_constraints == ("sleep_suppression",)


def test_evaluate_intent_returns_surviving_subset_after_suppression() -> None:
    """Partial suppression should keep the allowed entity subset explicit."""
    target = _target("light.sleep_accent_lamp", "light.sleep_lamp", "light.accent_lamp")
    decision = evaluate_intent(
        ControlIntent(
            intent_id="sleep_accent_light",
            action=IntentAction.ACTIVATE,
            target=target,
        ),
        constraints=(
            IntentConstraint(
                constraint_id="sleep_suppression",
                effect=ConstraintEffect.SUPPRESS,
                reason="not_sleep_member",
                target_entity_ids=("light.accent_lamp",),
                priority=20,
            ),
            IntentConstraint(
                constraint_id="accent_suppression",
                effect=ConstraintEffect.SUPPRESS,
                reason="not_accent_member",
                target_entity_ids=("light.sleep_lamp",),
                priority=10,
            ),
        ),
    )

    assert decision.action is IntentAction.ACTIVATE
    assert decision.reason is IntentReason.TARGET_PARTIALLY_SUPPRESSED
    assert decision.target_entity_ids == ("light.sleep_accent_lamp",)
    assert decision.applied_constraints == (
        "sleep_suppression",
        "accent_suppression",
    )


def test_engine_module_has_no_homeassistant_imports() -> None:
    """The pure engine module must not import Home Assistant."""
    engine_path = (
        Path(__file__).parents[2]
        / "custom_components"
        / "magic_areas"
        / "core"
        / "control_intents"
        / "engine.py"
    )
    parsed = ast.parse(engine_path.read_text(encoding="utf-8"))

    imported_modules = {
        alias.name
        for node in ast.walk(parsed)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module or ""
        for node in ast.walk(parsed)
        if isinstance(node, ast.ImportFrom)
    )

    assert not any(module.startswith("homeassistant") for module in imported_modules)
