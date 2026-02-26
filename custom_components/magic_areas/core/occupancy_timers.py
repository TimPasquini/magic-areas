"""Occupancy timeout calculations."""

from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIMEOUT,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_CLEAR_TIMEOUT,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.const import ONE_MINUTE


def get_clear_timeout(config: dict, states: list[str]) -> float:
    """Return current timeout value in seconds."""
    secondary = config.get(CONF_SECONDARY_STATES, {})

    if AreaStates.SLEEP in states:
        return secondary.get(CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT) * ONE_MINUTE

    if AreaStates.EXTENDED in states:
        return secondary.get(CONF_EXTENDED_TIMEOUT, DEFAULT_EXTENDED_TIMEOUT) * ONE_MINUTE

    return config.get(CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT) * ONE_MINUTE


def check_timeout_exceeded(
    last_off_time: datetime, clear_timeout: float, now: datetime
) -> bool:
    """Check if the clear timeout has been exceeded."""
    clear_delta = timedelta(seconds=clear_timeout)
    clear_time = last_off_time + clear_delta
    return now >= clear_time


def compute_occupancy(
    any_active: bool,
    is_occupied: bool,
    is_on_timeout: bool,
    last_off_time: datetime,
    now: datetime,
    clear_timeout: float,
) -> tuple[bool, float | None, bool]:
    """Compute occupancy from sensor activity.

    Returns:
        Tuple of (is_occupied, timeout_seconds_to_request, should_cancel_timeout).

    """
    if any_active:
        # Sensors active → occupied, cancel any pending timeout
        return True, None, True

    if not is_occupied:
        # Not active, not occupied → clear
        return False, None, False

    # Not active, but was occupied
    if is_on_timeout:
        if check_timeout_exceeded(last_off_time, clear_timeout, now):
            # Timeout exceeded → clear
            return False, None, True
        # Still within timeout → stay occupied
        return True, None, False

    # Occupied but no timeout running
    if clear_timeout == 0:
        # Immediate clear
        return False, None, False

    # Request timeout and stay occupied
    return True, clear_timeout, False
