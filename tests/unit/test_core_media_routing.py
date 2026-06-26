"""Tests for media routing policy functions."""

from custom_components.magic_areas.core.controls.policies.media import (
    evaluate_area_routing,
    has_valid_notification_states,
    should_skip_sleep_state,
)
from custom_components.magic_areas.area_state import AreaStates


class TestHasValidNotificationStates:
    """Tests for has_valid_notification_states function."""

    def test_empty_notification_states(self) -> None:
        """Test with no notification states configured - should allow all."""
        assert has_valid_notification_states([AreaStates.OCCUPIED.value], []) is True

    def test_no_area_states(self) -> None:
        """Test with area having no states."""
        assert (
            has_valid_notification_states(
                [],
                [AreaStates.OCCUPIED.value],
            )
            is False
        )

    def test_matching_notification_state(self) -> None:
        """Test area with matching notification state."""
        assert (
            has_valid_notification_states(
                [AreaStates.OCCUPIED.value, AreaStates.BRIGHT.value],
                [AreaStates.OCCUPIED.value],
            )
            is True
        )

    def test_no_matching_notification_state(self) -> None:
        """Test area without matching notification state."""
        assert (
            has_valid_notification_states(
                [AreaStates.OCCUPIED.value],
                [AreaStates.SLEEP.value, AreaStates.DARK.value],
            )
            is False
        )

    def test_multiple_notification_states(self) -> None:
        """Test with multiple valid notification states."""
        assert (
            has_valid_notification_states(
                [AreaStates.OCCUPIED.value, AreaStates.DARK.value],
                [AreaStates.DARK.value, AreaStates.BRIGHT.value],
            )
            is True
        )

    def test_all_states_match(self) -> None:
        """Test when area has all notification states."""
        area_states = [
            AreaStates.OCCUPIED.value,
            AreaStates.SLEEP.value,
            AreaStates.DARK.value,
        ]
        notification_states = [
            AreaStates.OCCUPIED.value,
            AreaStates.SLEEP.value,
            AreaStates.DARK.value,
        ]
        assert has_valid_notification_states(area_states, notification_states) is True


class TestShouldSkipSleepState:
    """Tests for should_skip_sleep_state function."""

    def test_no_sleep_state(self) -> None:
        """Test when area is not in sleep state."""
        assert (
            should_skip_sleep_state(
                [AreaStates.OCCUPIED.value, AreaStates.BRIGHT.value],
                [AreaStates.OCCUPIED.value],
            )
            is False
        )

    def test_sleep_state_not_in_notification_states(self) -> None:
        """Test when area is in sleep but sleep not in notification states."""
        assert (
            should_skip_sleep_state(
                [AreaStates.SLEEP.value, AreaStates.DARK.value],
                [AreaStates.OCCUPIED.value],
            )
            is True
        )

    def test_sleep_state_in_notification_states(self) -> None:
        """Test when area is in sleep and sleep in notification states."""
        assert (
            should_skip_sleep_state(
                [AreaStates.SLEEP.value, AreaStates.DARK.value],
                [AreaStates.SLEEP.value],
            )
            is False
        )

    def test_empty_notification_states(self) -> None:
        """Test with empty notification states."""
        assert (
            should_skip_sleep_state(
                [AreaStates.SLEEP.value],
                [],
            )
            is True
        )


class TestEvaluateAreaRouting:
    """Tests for evaluate_area_routing function."""

    def test_not_occupied_area(self) -> None:
        """Test unoccupied area should not receive media."""
        assert (
            evaluate_area_routing(
                is_occupied=False,
                area_states=[],
                notification_states=[AreaStates.OCCUPIED.value],
            )
            is False
        )

    def test_occupied_valid_state(self) -> None:
        """Test occupied area with valid notification state."""
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[AreaStates.OCCUPIED.value, AreaStates.BRIGHT.value],
                notification_states=[AreaStates.OCCUPIED.value],
            )
            is True
        )

    def test_occupied_invalid_state(self) -> None:
        """Test occupied area without valid notification state."""
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[AreaStates.OCCUPIED.value],
                notification_states=[AreaStates.SLEEP.value],
            )
            is False
        )

    def test_occupied_sleep_not_allowed(self) -> None:
        """Test occupied area in sleep state when sleep not allowed."""
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[AreaStates.OCCUPIED.value, AreaStates.SLEEP.value],
                notification_states=[AreaStates.OCCUPIED.value],
            )
            is False
        )

    def test_occupied_sleep_allowed(self) -> None:
        """Test occupied area in sleep state when sleep allowed."""
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[AreaStates.OCCUPIED.value, AreaStates.SLEEP.value],
                notification_states=[AreaStates.OCCUPIED.value, AreaStates.SLEEP.value],
            )
            is True
        )

    def test_empty_notification_states_accepts_all(self) -> None:
        """Test that empty notification states accepts all occupied areas."""
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[AreaStates.OCCUPIED.value],
                notification_states=[],
            )
            is True
        )

    def test_multiple_valid_states(self) -> None:
        """Test area with multiple valid states."""
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[
                    AreaStates.OCCUPIED.value,
                    AreaStates.BRIGHT.value,
                    AreaStates.EXTENDED.value,
                ],
                notification_states=[
                    AreaStates.OCCUPIED.value,
                    AreaStates.BRIGHT.value,
                    AreaStates.EXTENDED.value,
                ],
            )
            is True
        )

    def test_comprehensive_scenario_1(self) -> None:
        """Test comprehensive scenario: daytime occupied area."""
        # Daytime, occupied, bright - should receive media
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[AreaStates.OCCUPIED.value, AreaStates.BRIGHT.value],
                notification_states=[
                    AreaStates.OCCUPIED.value,
                    AreaStates.BRIGHT.value,
                    AreaStates.DARK.value,
                ],
            )
            is True
        )

    def test_comprehensive_scenario_2(self) -> None:
        """Test comprehensive scenario: nighttime sleeping area."""
        # Nighttime, sleeping, dark - should not receive media
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[
                    AreaStates.OCCUPIED.value,
                    AreaStates.SLEEP.value,
                    AreaStates.DARK.value,
                ],
                notification_states=[
                    AreaStates.OCCUPIED.value,
                    AreaStates.BRIGHT.value,
                    AreaStates.DARK.value,
                ],
            )
            is False
        )

    def test_comprehensive_scenario_3(self) -> None:
        """Test comprehensive scenario: guest area in sleep state allowed."""
        # Area in sleep state but notifications allowed during sleep
        assert (
            evaluate_area_routing(
                is_occupied=True,
                area_states=[AreaStates.OCCUPIED.value, AreaStates.SLEEP.value],
                notification_states=[
                    AreaStates.OCCUPIED.value,
                    AreaStates.SLEEP.value,
                    AreaStates.EXTENDED.value,
                ],
            )
            is True
        )
