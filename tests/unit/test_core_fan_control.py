"""Unit tests for core/fan_control.py."""

import pytest

from custom_components.magic_areas.core.fan_control import (
    FanControlPolicy,
    build_fan_policy,
)
from custom_components.magic_areas.enums import AreaStates


class TestFanControlPolicy:
    """Tests for FanControlPolicy."""

    def test_turns_off_when_area_clear(self):
        """Should turn off when area is clear."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.CLEAR],
            sensor_value=30.0,  # Above setpoint but area clear
        )
        assert decision.should_turn_off is True
        assert decision.should_turn_on is False
        assert "clear" in decision.reason

    def test_turns_off_when_required_state_not_met(self):
        """Should turn off when required state not present."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.DARK],  # Not occupied
            sensor_value=30.0,
        )
        assert decision.should_turn_off is True
        assert decision.should_turn_on is False
        assert "required_state_not_met" in decision.reason

    def test_turns_on_when_setpoint_reached(self):
        """Should turn on when sensor >= setpoint and state met."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED],
            sensor_value=26.0,  # Above setpoint
        )
        assert decision.should_turn_on is True
        assert decision.should_turn_off is False
        assert "setpoint_reached" in decision.reason

    def test_turns_off_when_below_setpoint(self):
        """Should turn off when sensor < setpoint."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED],
            sensor_value=24.0,  # Below setpoint
        )
        assert decision.should_turn_off is True
        assert decision.should_turn_on is False
        assert "below_setpoint" in decision.reason

    def test_turns_off_when_sensor_unavailable(self):
        """Should turn off (safe default) when sensor unavailable."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED],
            sensor_value=None,  # Sensor unavailable
        )
        assert decision.should_turn_off is True
        assert decision.should_turn_on is False
        assert "unavailable" in decision.reason

    def test_setpoint_exact_match(self):
        """Should turn on when sensor value exactly equals setpoint."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED],
            sensor_value=25.0,  # Exactly at setpoint
        )
        assert decision.should_turn_on is True
        assert decision.should_turn_off is False

    def test_works_with_different_required_states(self):
        """Should work with different required states like EXTENDED."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.EXTENDED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED, AreaStates.EXTENDED],
            sensor_value=26.0,
        )
        assert decision.should_turn_on is True

    def test_requires_specific_state_not_just_occupied(self):
        """Should turn off if required state is EXTENDED but only OCCUPIED."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.EXTENDED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED],  # Not EXTENDED
            sensor_value=26.0,
        )
        assert decision.should_turn_off is True
        assert "required_state_not_met" in decision.reason

    def test_clear_overrides_everything(self):
        """CLEAR should turn off even if all other conditions met."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.CLEAR, AreaStates.OCCUPIED],
            sensor_value=30.0,  # Way above setpoint
        )
        assert decision.should_turn_off is True
        assert "clear" in decision.reason

    def test_high_setpoint(self):
        """Should handle high setpoint values."""
        policy = FanControlPolicy(setpoint=80.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED],
            sensor_value=85.0,
        )
        assert decision.should_turn_on is True

    def test_low_setpoint(self):
        """Should handle low setpoint values."""
        policy = FanControlPolicy(setpoint=15.0, required_state=AreaStates.OCCUPIED)
        decision = policy.evaluate(
            current_states=[AreaStates.OCCUPIED],
            sensor_value=10.0,
        )
        assert decision.should_turn_off is True


class TestBuildFanPolicy:
    """Tests for build_fan_policy()."""

    def test_builds_policy_from_config(self):
        """Should build policy from feature configuration."""
        config = {
            "setpoint": 28.5,
            "required_state": AreaStates.EXTENDED,
        }
        policy = build_fan_policy(config)
        assert policy.setpoint == 28.5
        assert policy.required_state == AreaStates.EXTENDED

    def test_uses_defaults_when_missing(self):
        """Should use default values when config keys missing."""
        config = {}
        policy = build_fan_policy(config)
        # Should have defaults
        assert isinstance(policy.setpoint, float)
        assert isinstance(policy.required_state, str)

    def test_converts_setpoint_to_float(self):
        """Should convert setpoint to float."""
        config = {
            "setpoint": "25",  # String
        }
        policy = build_fan_policy(config)
        assert isinstance(policy.setpoint, float)
        assert policy.setpoint == 25.0

    def test_partial_config(self):
        """Should use defaults for missing keys."""
        config = {
            "setpoint": 30.0,
        }
        policy = build_fan_policy(config)
        assert policy.setpoint == 30.0
        assert isinstance(policy.required_state, str)


class TestFanControlDecision:
    """Tests for FanControlDecision dataclass."""

    def test_decision_has_required_fields(self):
        """FanControlDecision should have all required fields."""
        from custom_components.magic_areas.core.fan_control import FanControlDecision

        decision = FanControlDecision(
            should_turn_on=True, should_turn_off=False, reason="test"
        )
        assert decision.should_turn_on is True
        assert decision.should_turn_off is False
        assert decision.reason == "test"

    def test_decision_mutually_exclusive(self):
        """Decision should never have both turn_on and turn_off True."""
        policy = FanControlPolicy(setpoint=25.0, required_state=AreaStates.OCCUPIED)

        # Test all scenarios
        test_cases = [
            ([AreaStates.OCCUPIED], 26.0),  # turn on
            ([AreaStates.OCCUPIED], 24.0),  # turn off
            ([AreaStates.CLEAR], 26.0),  # turn off (clear)
            ([AreaStates.OCCUPIED], None),  # turn off (no sensor)
        ]

        for states, sensor_value in test_cases:
            decision = policy.evaluate(states, sensor_value)
            # Should never be both True
            assert not (decision.should_turn_on and decision.should_turn_off)
