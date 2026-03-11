"""Contract tests for core.control_group abstractions."""

from dataclasses import FrozenInstanceError

import pytest

from custom_components.magic_areas.core.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupDefinition,
    ControlRuntimeEffect,
    ControlRuntimeEffectType,
    build_noop_decision,
)


def test_build_noop_decision_shape() -> None:
    """NOOP helper should create a stable decision contract."""
    decision = build_noop_decision("no_input")
    assert decision == ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        actions=(),
        reason="no_input",
    )


def test_control_group_definition_is_immutable() -> None:
    """Definitions should be frozen after creation."""
    definition = ControlGroupDefinition(
        group_id="light.overhead",
        members=("light.kitchen_main",),
        trigger_states=("occupied",),
        policy_id="light.default",
    )

    with pytest.raises(FrozenInstanceError):
        definition.group_id = "light.task"  # type: ignore[misc]


def test_policy_input_and_action_contract() -> None:
    """Context and action objects should preserve literal values."""
    context = ControlGroupContext(
        group_id="light.overhead",
        current_states=("occupied",),
        new_states=("occupied",),
        signals={"priority": "dark"},
    )
    action = ControlAction(
        domain="light",
        service="turn_on",
        target_entity_ids=("light.kitchen_main", "light.kitchen_sink"),
        service_data={"brightness_pct": 60},
    )

    assert context.group_id == "light.overhead"
    assert context.signals["priority"] == "dark"
    assert action.target_entity_ids[0] == "light.kitchen_main"
    assert action.service_data["brightness_pct"] == 60


def test_runtime_effect_contract_shape() -> None:
    """Runtime effect metadata should be carried by canonical decisions."""
    decision = ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        reason="set_runtime_state",
        runtime_effects=(
            ControlRuntimeEffect(
                effect_type=ControlRuntimeEffectType.SET_STATE,
                namespace="command_echo",
                key="state",
                value={"controlling": True, "awaiting_echo": False},
            ),
        ),
    )

    effect = decision.runtime_effects[0]
    assert effect.effect_type == ControlRuntimeEffectType.SET_STATE
    assert effect.namespace == "command_echo"
