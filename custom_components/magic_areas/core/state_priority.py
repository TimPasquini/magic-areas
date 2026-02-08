"""State priority resolution for Magic Areas."""

from __future__ import annotations

from collections.abc import Sequence

from custom_components.magic_areas.enums import AreaStates

# Default priority order (most important first)
# Unified ordering for all features
DEFAULT_STATE_PRIORITY: list[str] = [
    AreaStates.SLEEP,  # Highest priority
    AreaStates.EXTENDED,
    AreaStates.OCCUPIED,
    AreaStates.ACCENT,
    AreaStates.DARK,
    AreaStates.BRIGHT,
    AreaStates.CLEAR,  # Lowest priority
]

# Legacy light group priority states (for backward compatibility)
LIGHT_PRIORITY_STATES: list[str] = [
    AreaStates.SLEEP,
    AreaStates.ACCENT,
]


def get_highest_priority_state(
    states: Sequence[str] | set[str],
    priority_order: Sequence[str] | None = None,
) -> str | None:
    """Return highest priority state from list.

    Args:
        states: List or set of active area states
        priority_order: Custom priority order (defaults to DEFAULT_STATE_PRIORITY)

    Returns:
        Highest priority state or None if no states match

    Example:
        >>> get_highest_priority_state(["occupied", "sleep"])
        "sleep"  # sleep has higher priority
    """
    if priority_order is None:
        priority_order = DEFAULT_STATE_PRIORITY

    state_set = set(states) if isinstance(states, list) else states

    for priority_state in priority_order:
        if priority_state in state_set:
            return priority_state

    return None


def filter_by_priority(
    states: Sequence[str] | set[str],
    priority_states: Sequence[str],
) -> list[str]:
    """Filter states to only include priority states if any exist.

    Implements the pattern: "If any priority state is present, ignore all non-priority states."
    This is the behavior used by light groups.

    Args:
        states: List or set of states to filter
        priority_states: List of priority state identifiers

    Returns:
        Filtered state list (priority states only if any exist, otherwise all states)

    Example:
        >>> filter_by_priority(["occupied", "sleep", "dark"], ["sleep", "accent"])
        ["sleep"]  # Only priority state

        >>> filter_by_priority(["occupied", "dark"], ["sleep", "accent"])
        ["occupied", "dark"]  # No priority states, return all
    """
    state_list = list(states)
    state_set = set(states)

    has_priority = any(s in state_set for s in priority_states)

    if not has_priority:
        return state_list

    return [s for s in state_list if s in priority_states]


def has_any_priority_state(
    states: Sequence[str] | set[str],
    priority_states: Sequence[str],
) -> bool:
    """Check if any priority state is present.

    Args:
        states: List or set of states to check
        priority_states: List of priority state identifiers

    Returns:
        True if any priority state is present
    """
    state_set = set(states) if isinstance(states, list) else states
    return any(s in state_set for s in priority_states)
