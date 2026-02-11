"""Media routing policy for area-aware media player."""

from custom_components.magic_areas.enums import AreaStates


def has_valid_notification_states(
    area_states: list[str], notification_states: list[str]
) -> bool:
    """Check if area has any valid notification states.

    Args:
        area_states: Current states of the area
        notification_states: Allowed notification states

    Returns:
        True if area has at least one valid notification state

    """
    if not notification_states:
        return True

    for notification_state in notification_states:
        if notification_state in area_states:
            return True

    return False


def should_skip_sleep_state(
    area_states: list[str], notification_states: list[str]
) -> bool:
    """Check if area should be skipped due to sleep state.

    Args:
        area_states: Current states of the area
        notification_states: Allowed notification states

    Returns:
        True if area is in sleep state and sleep is not in notification_states

    """
    if AreaStates.SLEEP in area_states:
        if AreaStates.SLEEP not in notification_states:
            return True

    return False


def evaluate_area_routing(
    is_occupied: bool,
    area_states: list[str],
    notification_states: list[str],
) -> bool:
    """Evaluate if area should receive media.

    Args:
        is_occupied: Whether area is occupied
        area_states: Current states of the area
        notification_states: Allowed notification states

    Returns:
        True if area should receive media

    """
    # Area must be occupied
    if not is_occupied:
        return False

    # Check if sleep state should skip
    if should_skip_sleep_state(area_states, notification_states):
        return False

    # Must have at least one valid notification state
    return has_valid_notification_states(area_states, notification_states)
