"""Parity tests for fan policy -> control-group conversion."""

from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.control_group import ControlActionType
from custom_components.magic_areas.core.fan_control import (
    FanControlPolicy,
    fan_decision_to_control_group,
)


def test_turn_on_mapping_matches_policy() -> None:
    """Policy turn_on should map to ACTIVATE fan turn_on action."""
    policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
    decision = policy.evaluate([AreaStates.OCCUPIED], 30.0)

    cg_decision = fan_decision_to_control_group(decision, "fan.room", STATE_OFF)

    assert cg_decision.action_type == ControlActionType.ACTIVATE
    assert cg_decision.actions[0].service == "turn_on"


def test_turn_off_mapping_respects_current_fan_state() -> None:
    """Policy turn_off should only create action when fan currently on."""
    policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
    decision = policy.evaluate([AreaStates.OCCUPIED], 20.0)

    cg_decision = fan_decision_to_control_group(decision, "fan.room", STATE_ON)
    assert cg_decision.action_type == ControlActionType.DEACTIVATE
    assert cg_decision.actions[0].service == "turn_off"

    noop_decision = fan_decision_to_control_group(decision, "fan.room", STATE_OFF)
    assert noop_decision.action_type == ControlActionType.NOOP
