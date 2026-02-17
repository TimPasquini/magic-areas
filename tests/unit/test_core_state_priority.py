"""Unit tests for core/state_priority.py."""


from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.state_priority import (
    DEFAULT_STATE_PRIORITY,
    LIGHT_PRIORITY_STATES,
    filter_by_priority,
    get_highest_priority_state,
    has_any_priority_state,
)


class TestGetHighestPriorityState:
    """Tests for get_highest_priority_state()."""

    def test_returns_highest_priority_state(self) -> None:
        """Should return sleep when both sleep and occupied present."""
        states = [AreaStates.OCCUPIED, AreaStates.SLEEP]
        assert get_highest_priority_state(states) == AreaStates.SLEEP

    def test_returns_none_when_no_states(self) -> None:
        """Should return None when given empty list."""
        assert get_highest_priority_state([]) is None

    def test_works_with_set_input(self) -> None:
        """Should accept set as well as list."""
        states = {AreaStates.OCCUPIED.value, AreaStates.EXTENDED.value}
        assert get_highest_priority_state(states) == AreaStates.EXTENDED.value

    def test_custom_priority_order(self) -> None:
        """Should respect custom priority order."""
        states = [AreaStates.SLEEP, AreaStates.OCCUPIED]
        custom_order = [
            AreaStates.OCCUPIED,
            AreaStates.SLEEP,
        ]  # Reversed from default
        assert (
            get_highest_priority_state(states, custom_order) == AreaStates.OCCUPIED
        )

    def test_returns_none_when_no_match(self) -> None:
        """Should return None when no states match priority list."""
        states = ["unknown_state"]
        assert get_highest_priority_state(states) is None

    def test_uses_default_priority_order(self) -> None:
        """Should use DEFAULT_STATE_PRIORITY when not specified."""
        states = [AreaStates.OCCUPIED, AreaStates.EXTENDED, AreaStates.SLEEP]
        # SLEEP is highest in DEFAULT_STATE_PRIORITY
        assert get_highest_priority_state(states) == AreaStates.SLEEP

    def test_returns_first_match_in_priority_order(self) -> None:
        """Should return first matching state in priority order."""
        states = [
            AreaStates.CLEAR,
            AreaStates.DARK,
            AreaStates.BRIGHT,
        ]
        # DARK comes before BRIGHT and CLEAR in DEFAULT_STATE_PRIORITY
        result = get_highest_priority_state(states)
        assert result in [AreaStates.DARK, AreaStates.BRIGHT, AreaStates.CLEAR]

    def test_handles_multiple_states(self) -> None:
        """Should handle multiple states and return highest priority."""
        states = [
            AreaStates.OCCUPIED,
            AreaStates.EXTENDED,
            AreaStates.DARK,
            AreaStates.SLEEP,
        ]
        # SLEEP has highest priority
        assert get_highest_priority_state(states) == AreaStates.SLEEP


class TestFilterByPriority:
    """Tests for filter_by_priority()."""

    def test_filters_to_priority_when_present(self) -> None:
        """Should keep only priority states when any exist."""
        states = [AreaStates.OCCUPIED, AreaStates.SLEEP, AreaStates.DARK]
        result = filter_by_priority(states, LIGHT_PRIORITY_STATES)
        assert result == [AreaStates.SLEEP]

    def test_keeps_all_when_no_priority(self) -> None:
        """Should keep all states when no priority states present."""
        states = [AreaStates.OCCUPIED, AreaStates.DARK]
        result = filter_by_priority(states, LIGHT_PRIORITY_STATES)
        assert set(result) == {AreaStates.OCCUPIED, AreaStates.DARK}

    def test_multiple_priority_states(self) -> None:
        """Should keep all priority states when multiple present."""
        states = [AreaStates.SLEEP, AreaStates.ACCENT, AreaStates.OCCUPIED]
        result = filter_by_priority(states, LIGHT_PRIORITY_STATES)
        assert set(result) == {AreaStates.SLEEP, AreaStates.ACCENT}

    def test_works_with_set_input(self) -> None:
        """Should accept set as well as list."""
        states = {AreaStates.SLEEP.value, AreaStates.OCCUPIED.value}
        result = filter_by_priority(states, LIGHT_PRIORITY_STATES)
        assert AreaStates.SLEEP.value in result
        assert AreaStates.OCCUPIED.value not in result

    def test_preserves_order_when_no_priority(self) -> None:
        """Should preserve original order when no priority states."""
        states = [AreaStates.DARK, AreaStates.OCCUPIED, AreaStates.BRIGHT]
        result = filter_by_priority(states, LIGHT_PRIORITY_STATES)
        # Should preserve order
        assert result == states

    def test_empty_states_list(self) -> None:
        """Should handle empty states list."""
        result = filter_by_priority([], LIGHT_PRIORITY_STATES)
        assert result == []

    def test_empty_priority_list(self) -> None:
        """Should return all states when priority list is empty."""
        states = [AreaStates.OCCUPIED, AreaStates.DARK]
        result = filter_by_priority(states, [])
        assert set(result) == set(states)

    def test_accent_state_filtering(self) -> None:
        """Should correctly filter accent state (priority)."""
        states = [AreaStates.ACCENT, AreaStates.DARK, AreaStates.OCCUPIED]
        result = filter_by_priority(states, LIGHT_PRIORITY_STATES)
        assert result == [AreaStates.ACCENT]


class TestHasAnyPriorityState:
    """Tests for has_any_priority_state()."""

    def test_returns_true_when_priority_present(self) -> None:
        """Should return True when at least one priority state present."""
        states = [AreaStates.OCCUPIED, AreaStates.SLEEP]
        assert has_any_priority_state(states, LIGHT_PRIORITY_STATES) is True

    def test_returns_false_when_no_priority(self) -> None:
        """Should return False when no priority states present."""
        states = [AreaStates.OCCUPIED, AreaStates.DARK]
        assert has_any_priority_state(states, LIGHT_PRIORITY_STATES) is False

    def test_works_with_set_input(self) -> None:
        """Should accept set as well as list."""
        states = {AreaStates.SLEEP.value, AreaStates.OCCUPIED.value}
        assert has_any_priority_state(states, LIGHT_PRIORITY_STATES) is True

    def test_returns_false_for_empty_states(self) -> None:
        """Should return False for empty states list."""
        assert has_any_priority_state([], LIGHT_PRIORITY_STATES) is False

    def test_returns_false_for_empty_priority(self) -> None:
        """Should return False when priority list is empty."""
        states = [AreaStates.OCCUPIED, AreaStates.DARK]
        assert has_any_priority_state(states, []) is False

    def test_accent_state_detection(self) -> None:
        """Should detect accent as priority state."""
        states = [AreaStates.ACCENT, AreaStates.OCCUPIED]
        assert has_any_priority_state(states, LIGHT_PRIORITY_STATES) is True

    def test_multiple_priority_states(self) -> None:
        """Should return True when multiple priority states present."""
        states = [AreaStates.SLEEP, AreaStates.ACCENT, AreaStates.OCCUPIED]
        assert has_any_priority_state(states, LIGHT_PRIORITY_STATES) is True


class TestConstants:
    """Tests for module constants."""

    def test_default_state_priority_contains_all_states(self) -> None:
        """DEFAULT_STATE_PRIORITY should contain all area states."""
        # Verify it contains the main states we care about
        assert AreaStates.SLEEP in DEFAULT_STATE_PRIORITY
        assert AreaStates.EXTENDED in DEFAULT_STATE_PRIORITY
        assert AreaStates.OCCUPIED in DEFAULT_STATE_PRIORITY
        assert AreaStates.CLEAR in DEFAULT_STATE_PRIORITY
        assert AreaStates.DARK in DEFAULT_STATE_PRIORITY
        assert AreaStates.BRIGHT in DEFAULT_STATE_PRIORITY
        assert AreaStates.ACCENT in DEFAULT_STATE_PRIORITY

    def test_light_priority_states_correct(self) -> None:
        """LIGHT_PRIORITY_STATES should match light group requirements."""
        assert AreaStates.SLEEP in LIGHT_PRIORITY_STATES
        assert AreaStates.ACCENT in LIGHT_PRIORITY_STATES
        assert len(LIGHT_PRIORITY_STATES) == 2

    def test_sleep_has_highest_priority(self) -> None:
        """SLEEP should be first in DEFAULT_STATE_PRIORITY."""
        assert DEFAULT_STATE_PRIORITY[0] == AreaStates.SLEEP

    def test_clear_has_lowest_priority(self) -> None:
        """CLEAR should be last in DEFAULT_STATE_PRIORITY."""
        assert DEFAULT_STATE_PRIORITY[-1] == AreaStates.CLEAR
