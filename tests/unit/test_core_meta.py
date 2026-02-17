"""Tests for core meta area helpers."""


from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.meta import aggregate_secondary_states


class TestAggregateSecondaryStates:
    """Tests for aggregate_secondary_states function."""

    def test_empty_child_state_lists(self) -> None:
        """Test with empty child state lists - should return only BRIGHT."""
        result = aggregate_secondary_states(
            child_state_lists=[],
            mode="any",
            configurable_states=[AreaStates.DARK, AreaStates.SLEEP],
        )
        assert result == [AreaStates.BRIGHT]

    def test_single_child_any_mode(self) -> None:
        """Test with single child in ANY mode."""
        result = aggregate_secondary_states(
            child_state_lists=[[AreaStates.DARK, AreaStates.SLEEP]],
            mode="any",
            configurable_states=[AreaStates.DARK, AreaStates.SLEEP],
        )
        assert AreaStates.DARK in result
        assert AreaStates.SLEEP in result
        # BRIGHT should not be added when DARK is present
        assert AreaStates.BRIGHT not in result

    def test_multiple_children_any_mode(self) -> None:
        """Test with multiple children in ANY mode - any presence counts."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.DARK],
                [AreaStates.BRIGHT],
                [AreaStates.SLEEP],
            ],
            mode="any",
            configurable_states=[AreaStates.DARK, AreaStates.SLEEP],
        )
        assert AreaStates.DARK in result
        assert AreaStates.SLEEP in result
        assert AreaStates.BRIGHT not in result

    def test_multiple_children_all_mode(self) -> None:
        """Test with multiple children in ALL mode - all must have."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.DARK, AreaStates.OCCUPIED],
                [AreaStates.DARK, AreaStates.OCCUPIED],
                [AreaStates.DARK, AreaStates.OCCUPIED],
            ],
            mode="all",
            configurable_states=[AreaStates.DARK, AreaStates.OCCUPIED],
        )
        assert AreaStates.DARK in result
        assert AreaStates.OCCUPIED in result
        assert AreaStates.BRIGHT not in result

    def test_multiple_children_all_mode_partial(self) -> None:
        """Test ALL mode where not all children have state."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.DARK],
                [AreaStates.BRIGHT],
            ],
            mode="all",
            configurable_states=[AreaStates.DARK],
        )
        # DARK not in all children, so shouldn't be included
        assert AreaStates.DARK not in result
        assert AreaStates.BRIGHT in result

    def test_multiple_children_majority_mode(self) -> None:
        """Test MAJORITY mode - >= 50% must have."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.DARK],
                [AreaStates.DARK],
                [AreaStates.BRIGHT],
            ],
            mode="majority",
            configurable_states=[AreaStates.DARK],
        )
        # 2 out of 3 have DARK (66% > 50%)
        assert AreaStates.DARK in result
        assert AreaStates.BRIGHT not in result

    def test_majority_mode_exactly_50_percent(self) -> None:
        """Test MAJORITY mode with exactly 50% - should include."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.DARK],
                [AreaStates.BRIGHT],
            ],
            mode="majority",
            configurable_states=[AreaStates.DARK],
        )
        # 1 out of 2 have DARK (50%)
        assert AreaStates.DARK in result
        assert AreaStates.BRIGHT not in result

    def test_dark_state_prevents_bright(self) -> None:
        """Test that DARK state prevents BRIGHT from being added."""
        result = aggregate_secondary_states(
            child_state_lists=[[AreaStates.DARK]],
            mode="any",
            configurable_states=[AreaStates.DARK],
        )
        assert AreaStates.DARK in result
        assert AreaStates.BRIGHT not in result

    def test_bright_added_when_no_dark(self) -> None:
        """Test that BRIGHT is added when DARK is not present."""
        result = aggregate_secondary_states(
            child_state_lists=[[AreaStates.SLEEP]],
            mode="any",
            configurable_states=[AreaStates.SLEEP],
        )
        assert AreaStates.SLEEP in result
        assert AreaStates.BRIGHT in result

    def test_states_not_in_configurable_ignored(self) -> None:
        """Test that states not in configurable_states are ignored."""
        result = aggregate_secondary_states(
            child_state_lists=[[AreaStates.SLEEP, AreaStates.OCCUPIED]],
            mode="any",
            configurable_states=[AreaStates.DARK],  # SLEEP, OCCUPIED not here
        )
        assert AreaStates.SLEEP not in result
        assert AreaStates.OCCUPIED not in result
        assert AreaStates.BRIGHT in result

    def test_mixed_states_any_mode(self) -> None:
        """Test ANY mode with mixed states across children."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.DARK, AreaStates.SLEEP],
                [AreaStates.BRIGHT, AreaStates.OCCUPIED],
                [AreaStates.DARK],
            ],
            mode="any",
            configurable_states=[
                AreaStates.DARK,
                AreaStates.SLEEP,
                AreaStates.OCCUPIED,
            ],
        )
        assert AreaStates.DARK in result
        assert AreaStates.SLEEP in result
        assert AreaStates.OCCUPIED in result
        assert AreaStates.BRIGHT not in result

    def test_empty_configurable_states(self) -> None:
        """Test with empty configurable_states list."""
        result = aggregate_secondary_states(
            child_state_lists=[[AreaStates.DARK, AreaStates.SLEEP]],
            mode="any",
            configurable_states=[],
        )
        # No configurable states to aggregate
        assert AreaStates.BRIGHT in result
        assert len(result) == 1

    def test_comprehensive_scenario_1(self) -> None:
        """Test comprehensive scenario: daytime bright areas."""
        # 3 areas, 2 are bright, looking for dark state
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.BRIGHT],
                [AreaStates.BRIGHT],
                [AreaStates.DARK],
            ],
            mode="majority",
            configurable_states=[AreaStates.DARK],
        )
        # DARK in 1/3 (33% < 50%)
        assert AreaStates.DARK not in result
        assert AreaStates.BRIGHT in result

    def test_comprehensive_scenario_2(self) -> None:
        """Test comprehensive scenario: all areas dark."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.DARK, AreaStates.OCCUPIED],
                [AreaStates.DARK, AreaStates.OCCUPIED],
                [AreaStates.DARK, AreaStates.OCCUPIED],
            ],
            mode="all",
            configurable_states=[AreaStates.DARK, AreaStates.OCCUPIED],
        )
        assert AreaStates.DARK in result
        assert AreaStates.OCCUPIED in result
        assert AreaStates.BRIGHT not in result

    def test_comprehensive_scenario_3(self) -> None:
        """Test comprehensive scenario: mixed occupancy and darkness."""
        result = aggregate_secondary_states(
            child_state_lists=[
                [AreaStates.OCCUPIED, AreaStates.DARK],
                [AreaStates.OCCUPIED, AreaStates.BRIGHT],
                [AreaStates.CLEAR, AreaStates.DARK],
            ],
            mode="any",
            configurable_states=[AreaStates.OCCUPIED, AreaStates.DARK],
        )
        assert AreaStates.OCCUPIED in result
        assert AreaStates.DARK in result
        assert AreaStates.BRIGHT not in result
