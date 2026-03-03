"""Contract tests for core.control_group abstractions."""

from dataclasses import FrozenInstanceError

import pytest

from custom_components.magic_areas.core.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupDefinition,
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
