"""Unit tests for light-group policy behavior."""

import pytest

from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.light_groups import (
    ActOnMode,
    LightAction,
    LightGroupPolicy,
)
from custom_components.magic_areas.area_state import AreaStates


class TestLightGroupPolicy:
    """Tests for LightGroupPolicy."""

    def test_noop_when_area_clear(self) -> None:
        """Should noop with reset_control flag when area goes clear."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.CLEAR],
            lost_states=[AreaStates.OCCUPIED],
            current_states=[AreaStates.CLEAR],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "clear" in decision.reason
        assert decision.next_control_state is not None
        assert decision.next_control_state.controlling is True
        assert decision.next_control_state.awaiting_echo is False

    def test_turn_off_when_bright_not_assigned(self) -> None:
        """Should turn off when BRIGHT appears and not assigned to it."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],  # Not BRIGHT
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.BRIGHT],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.TURN_OFF
        assert "bright" in decision.reason
        assert decision.next_control_state is not None
        assert decision.next_control_state.controlling is True
        assert decision.next_control_state.awaiting_echo is True

    def test_noop_when_bright_and_occupied_added_together(self) -> None:
        """Should noop when BRIGHT and OCCUPIED added together (occupancy prevents bright turn-off)."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.BRIGHT, AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        # When OCCUPIED is in new_states along with BRIGHT, bright logic doesn't trigger turn-off
        assert decision.action == LightAction.NOOP
        assert "bright" in decision.reason  # bright_active_but_stable
        assert decision.next_control_state is None

    def test_noop_when_bright_stable(self) -> None:
        """Should noop when BRIGHT is active but not in new_states."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        # BRIGHT is in current but not new, so it's stable (not newly added)
        # This triggers bright_active_but_stable and returns NOOP
        assert decision.action == LightAction.NOOP
        assert "bright" in decision.reason

    def test_legacy_control_state_input_raises_type_error(self) -> None:
        """Legacy state objects should not be accepted by light policy."""

        class LegacyState:
            def __init__(self, controlling: bool, controlled: bool) -> None:
                self.controlling = controlling
                self.controlled = controlled

            def command_issued(self) -> "LegacyState":
                return LegacyState(controlling=True, controlled=True)

            def command_completed(self) -> "LegacyState":
                return LegacyState(controlling=self.controlling, controlled=False)

            def external_change(self) -> "LegacyState":
                return LegacyState(controlling=False, controlled=False)

            def set_controlled(self, controlled: bool) -> "LegacyState":
                return LegacyState(controlling=self.controlling, controlled=controlled)

            def set_controlling(self, controlling: bool) -> "LegacyState":
                return LegacyState(controlling=controlling, controlled=self.controlled)

        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        with pytest.raises(TypeError):
            policy.evaluate_control_context(
                new_states=[AreaStates.DARK],
                lost_states=[],
                current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
                control_state=LegacyState(controlling=True, controlled=False),
                is_primary=False,
            )

    def test_noop_when_not_occupied(self) -> None:
        """Should noop when area not occupied."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.DARK],  # Not occupied
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "not_occupied" in decision.reason

    def test_turn_on_when_valid_state_present(self) -> None:
        """Should turn on when assigned state is active."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.TURN_ON
        assert "valid_states" in decision.reason
        assert decision.next_control_state is not None
        assert decision.next_control_state.controlling is True
        assert decision.next_control_state.awaiting_echo is True

    def test_noop_when_occupancy_change_not_configured(self) -> None:
        """Should noop when occupancy changes but not configured to act on it."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],  # Not OCCUPANCY_CHANGE
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "not_configured" in decision.reason

    def test_noop_when_state_change_not_configured(self) -> None:
        """Should noop when state changes but not configured to act on it."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE],  # Not STATE_CHANGE
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "not_configured" in decision.reason

    def test_priority_filtering_applied(self) -> None:
        """Should filter by priority states when enabled."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK, AreaStates.SLEEP],
            act_on_modes=[ActOnMode.STATE_CHANGE],
            use_priority_filtering=True,
        )
        # SLEEP is priority, DARK is not
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.SLEEP],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK, AreaStates.SLEEP],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.TURN_ON
        assert "sleep" in decision.reason.lower()

    def test_turn_off_when_no_valid_states_entering_priority(self) -> None:
        """Should turn off when no valid states remain and a priority state is entering."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        # SLEEP (priority) is entering, DARK was lost — overhead/dark group should turn off
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.SLEEP],
            lost_states=[AreaStates.DARK],
            current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.TURN_OFF
        assert "no_valid_states" in decision.reason
        assert decision.next_control_state is not None
        assert decision.next_control_state.controlling is True
        assert decision.next_control_state.awaiting_echo is True

    def test_noop_when_no_valid_states_no_priority_transition(self) -> None:
        """Should noop when no valid states remain but no priority transition."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        # DARK was lost, nothing priority is entering — stable state, noop
        decision = policy.evaluate_control_context(
            new_states=[],
            lost_states=[AreaStates.DARK],
            current_states=[AreaStates.OCCUPIED],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "no_new_priority" in decision.reason

    def test_noop_when_no_valid_states_entering_dark(self) -> None:
        """Should noop when no valid states remain because DARK is just entering."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.EXTENDED],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        # DARK just entered, EXTENDED lost — don't turn off, dark mode takes over
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[AreaStates.EXTENDED],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "entering_dark" in decision.reason

    def test_turn_off_when_leaving_priority_state(self) -> None:
        """Should turn off when leaving an assigned priority state."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.SLEEP],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        # SLEEP mode ended, group was assigned to SLEEP — turn off
        decision = policy.evaluate_control_context(
            new_states=[],
            lost_states=[AreaStates.SLEEP],
            current_states=[AreaStates.OCCUPIED],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.TURN_OFF
        assert "leaving_priority" in decision.reason
        assert decision.next_control_state is not None
        assert decision.next_control_state.controlling is True
        assert decision.next_control_state.awaiting_echo is True

    def test_noop_when_no_changes(self) -> None:
        """Should noop when no state changes."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "no_state_changes" in decision.reason

    def test_noop_when_no_assigned_states(self) -> None:
        """Should noop when light group has no assigned states."""
        policy = LightGroupPolicy(
            assigned_states=[],  # No assigned states
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.NOOP
        assert "no_assigned_states" in decision.reason

    def test_turn_on_with_multiple_assigned_states(self) -> None:
        """Should turn on when any assigned state is present."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK, AreaStates.SLEEP],
            act_on_modes=[ActOnMode.STATE_CHANGE],
            use_priority_filtering=False,  # Disable priority filtering for this test
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.TURN_ON

    def test_acts_on_occupancy_when_configured(self) -> None:
        """Should act on occupancy change when configured."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.OCCUPIED],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision.action == LightAction.TURN_ON

    def test_acts_on_both_occupancy_and_state(self) -> None:
        """Should act on both occupancy and state changes when configured."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK, AreaStates.OCCUPIED],
            act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
        )
        # Test occupancy change
        decision1 = policy.evaluate_control_context(
            new_states=[AreaStates.OCCUPIED],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision1.action == LightAction.TURN_ON

        # Test state change
        decision2 = policy.evaluate_control_context(
            new_states=[AreaStates.DARK],
            lost_states=[],
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            is_primary=False,
        )
        assert decision2.action == LightAction.TURN_ON

    def test_primary_clear_turns_off(self) -> None:
        """Primary group should turn off when area clears."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=[ActOnMode.STATE_CHANGE],
        )
        decision = policy.evaluate_control_context(
            new_states=[AreaStates.CLEAR],
            lost_states=[AreaStates.OCCUPIED],
            current_states=[AreaStates.CLEAR],
            control_state=CommandEchoState(controlling=False, awaiting_echo=False),
            is_primary=True,
        )
        assert decision.action == LightAction.TURN_OFF
        assert decision.next_control_state is not None
        assert decision.next_control_state.controlling is True
        assert decision.next_control_state.awaiting_echo is False


class TestLightGroupPolicyConstruction:
    """Tests for direct LightGroupPolicy construction."""

    def test_constructs_policy_from_params(self) -> None:
        """Should construct policy with given parameters."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK, AreaStates.SLEEP],
            act_on_modes=["occupancy", "state"],
            use_priority_filtering=True,
        )
        assert set(policy.assigned_states) == {AreaStates.DARK, AreaStates.SLEEP}
        assert set(policy.act_on_modes) == {"occupancy", "state"}
        assert policy.use_priority_filtering is True

    def test_empty_assigned_states(self) -> None:
        """Should construct policy with empty assigned states."""
        policy = LightGroupPolicy(
            assigned_states=[],
            act_on_modes=["state"],
            use_priority_filtering=True,
        )
        assert policy.assigned_states == []

    def test_single_act_on_mode(self) -> None:
        """Should construct policy with single act-on mode."""
        policy = LightGroupPolicy(
            assigned_states=[AreaStates.DARK],
            act_on_modes=["occupancy"],
            use_priority_filtering=True,
        )
        assert "occupancy" in policy.act_on_modes


class TestLightActionEnum:
    """Tests for LightAction enum."""

    def test_action_values(self) -> None:
        """Should have correct action values."""
        assert {action.value for action in LightAction} == {"turn_on", "turn_off", "noop"}

    def test_all_actions_present(self) -> None:
        """Should have all three actions."""
        actions = {LightAction.TURN_ON, LightAction.TURN_OFF, LightAction.NOOP}
        assert len(actions) == 3
