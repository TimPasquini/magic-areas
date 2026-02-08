"""Unit tests for core/light_control.py."""

import pytest

from custom_components.magic_areas.core.light_control import (
    ActOnMode,
    LightAction,
    LightGroupPolicy,
    build_light_group_policy,
)
from custom_components.magic_areas.enums import AreaStates


class TestLightGroupPolicy:
    """Tests for LightGroupPolicy."""

    def test_noop_when_area_clear(self):
        """Should noop when area goes clear."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.CLEAR],
            lost_states=[AreaStates.OCCUPIED],
            current_states=[AreaStates.CLEAR],
        )
        assert decision.action == LightAction.NOOP
        assert "clear" in decision.reason

    def test_turn_off_when_bright_not_assigned(self):
        """Should turn off when BRIGHT appears and not assigned to it."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],  # Not BRIGHT
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.BRIGHT],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        )
        assert decision.action == LightAction.TURN_OFF
        assert "bright" in decision.reason
        assert decision.should_track_control is True

    def test_noop_when_bright_and_occupied_added_together(self):
        """Should noop when BRIGHT and OCCUPIED added together (occupancy prevents bright turn-off)."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.BRIGHT, AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        )
        # When OCCUPIED is in new_states along with BRIGHT, bright logic doesn't trigger turn-off
        assert decision.action == LightAction.NOOP
        assert "bright" in decision.reason  # bright_active_but_stable

    def test_noop_when_bright_stable(self):
        """Should noop when BRIGHT is active but not in new_states."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT, AreaStates.DARK],
        )
        # BRIGHT is in current but not new, so it's stable (not newly added)
        # This triggers bright_active_but_stable and returns NOOP
        assert decision.action == LightAction.NOOP
        assert "bright" in decision.reason

    def test_noop_when_not_occupied(self):
        """Should noop when area not occupied."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.DARK],  # Not occupied
        )
        assert decision.action == LightAction.NOOP
        assert "not_occupied" in decision.reason

    def test_turn_on_when_valid_state_present(self):
        """Should turn on when assigned state is active."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        )
        assert decision.action == LightAction.TURN_ON
        assert "valid_states" in decision.reason
        assert decision.should_track_control is True

    def test_noop_when_occupancy_change_not_configured(self):
        """Should noop when occupancy changes but not configured to act on it."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],  # Not OCCUPANCY_CHANGE
        )
        decision = policy.evaluate(
            new_states=[AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED],
        )
        assert decision.action == LightAction.NOOP
        assert "not_configured" in decision.reason

    def test_noop_when_state_change_not_configured(self):
        """Should noop when state changes but not configured to act on it."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE],  # Not STATE_CHANGE
        )
        decision = policy.evaluate(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        )
        assert decision.action == LightAction.NOOP
        assert "not_configured" in decision.reason

    def test_priority_filtering_applied(self):
        """Should filter by priority states when enabled."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK, AreaStates.SLEEP],
            act_on_modes=[ActOnMode.STATE_CHANGE],
            use_priority_filtering=True,
        )
        # SLEEP is priority, DARK is not
        decision = policy.evaluate(
            new_states=[AreaStates.SLEEP],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK, AreaStates.SLEEP],
        )
        assert decision.action == LightAction.TURN_ON
        assert "sleep" in decision.reason.lower()

    def test_turn_off_when_no_valid_states(self):
        """Should turn off when no valid states remain."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[],
            lost_states=[AreaStates.DARK],
            current_states=[AreaStates.OCCUPIED],  # DARK lost, only occupied remains
        )
        assert decision.action == LightAction.TURN_OFF
        assert "no_valid_states" in decision.reason

    def test_noop_when_no_changes(self):
        """Should noop when no state changes."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        )
        assert decision.action == LightAction.NOOP
        assert "no_state_changes" in decision.reason

    def test_noop_when_no_assigned_states(self):
        """Should noop when light group has no assigned states."""
        policy = LightGroupPolicy(
            assigned_states=[],  # No assigned states
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        )
        assert decision.action == LightAction.NOOP
        assert "no_assigned_states" in decision.reason

    def test_turn_on_with_multiple_assigned_states(self):
        """Should turn on when any assigned state is present."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK, AreaStates.SLEEP],
            act_on_modes=[ActOnMode.STATE_CHANGE],
            use_priority_filtering=False,  # Disable priority filtering for this test
        )
        decision = policy.evaluate(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        )
        assert decision.action == LightAction.TURN_ON

    def test_acts_on_occupancy_when_configured(self):
        """Should act on occupancy change when configured."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.OCCUPIED],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE],
        )
        decision = policy.evaluate(
            new_states=[AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED],
        )
        assert decision.action == LightAction.TURN_ON

    def test_acts_on_both_occupancy_and_state(self):
        """Should act on both occupancy and state changes when configured."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK, AreaStates.OCCUPIED],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
        )
        # Test occupancy change
        decision1 = policy.evaluate(
            new_states=[AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED],
        )
        assert decision1.action == LightAction.TURN_ON

        # Test state change
        decision2 = policy.evaluate(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        )
        assert decision2.action == LightAction.TURN_ON


class TestBuildLightGroupPolicy:
    """Tests for build_light_group_policy()."""

    def test_builds_policy_from_params(self):
        """Should build policy with given parameters."""
        policy = build_light_group_policy(
            assigned_states=[AreaStates.DARK, AreaStates.SLEEP],
            act_on_modes=["occupancy", "state"],
        )
        assert set(policy.assigned_states) == {AreaStates.DARK, AreaStates.SLEEP}
        assert set(policy.act_on_modes) == {"occupancy", "state"}
        assert policy.use_priority_filtering is True

    def test_empty_assigned_states(self):
        """Should handle empty assigned states."""
        policy = build_light_group_policy(
            assigned_states=[],
            act_on_modes=["state"],
        )
        assert policy.assigned_states == []

    def test_single_act_on_mode(self):
        """Should handle single act on mode."""
        policy = build_light_group_policy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=["occupancy"],
        )
        assert "occupancy" in policy.act_on_modes


class TestLightActionEnum:
    """Tests for LightAction enum."""

    def test_action_values(self):
        """Should have correct action values."""
        assert LightAction.TURN_ON != LightAction.TURN_OFF
        assert LightAction.TURN_OFF != LightAction.NOOP
        assert LightAction.NOOP != LightAction.TURN_ON

    def test_all_actions_present(self):
        """Should have all three actions."""
        actions = {LightAction.TURN_ON, LightAction.TURN_OFF, LightAction.NOOP}
        assert len(actions) == 3
