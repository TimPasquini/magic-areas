"""Occupancy transition helpers."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import STATE_ON

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_EXTENDED_TIME,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_EXTENDED_TIME,
)
from custom_components.magic_areas.const import ONE_MINUTE
from custom_components.magic_areas.policy import (
    INVALID_STATES,
    PRESENCE_SENSOR_VALID_ON_STATES,
)


def valid_on_states(is_meta: bool, additional_states: list[str] | None = None) -> list[str]:
    """Return valid ON states for presence sensors."""
    if is_meta:
        return [STATE_ON]

    valid = PRESENCE_SENSOR_VALID_ON_STATES.copy()
    if additional_states:
        valid.extend(additional_states)
    return valid


def compute_sensors_active(
    sensor_states: dict[str, str | None],
    keep_only: list[str],
    is_occupied: bool,
    valid_states: list[str],
) -> tuple[list[str], bool]:
    """Filter sensors and return (active_list, any_active)."""
    active: list[str] = []

    # Determine available sensors (filter keep-only when not occupied)
    if is_occupied:
        available = list(sensor_states.keys())
    else:
        available = [sid for sid in sensor_states if sid not in keep_only]

    for sensor_id in available:
        state = sensor_states.get(sensor_id)
        if state is None:
            continue
        if state in INVALID_STATES:
            continue
        if state in valid_states:
            active.append(sensor_id)

    return active, len(active) > 0


def build_state_list(
    occupied: bool,
    last_changed: datetime,
    now: datetime,
    config: dict,
    secondary_states: list[str],
) -> list[str]:
    """Build current area state list."""
    new_state_list: list[str] = []
    new_state_list.append(AreaStates.OCCUPIED if occupied else AreaStates.CLEAR)

    if occupied:
        seconds_since = (now - last_changed).total_seconds()
        extended_time = config.get(CONF_SECONDARY_STATES, {}).get(
            CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME
        )
        if (seconds_since / ONE_MINUTE) >= extended_time:
            new_state_list.append(AreaStates.EXTENDED)

    new_state_list.extend(secondary_states)
    return new_state_list


def diff_states(
    previous_states: list[str], new_state_list: list[str]
) -> tuple[set[str], set[str]]:
    """Return new/lost states given previous/current lists."""
    previous_set = set(previous_states)
    current_set = set(new_state_list)

    if previous_set == current_set:
        new_states: set[str] = set()
        lost_states: set[str] = set()
    else:
        new_states = current_set - previous_set
        lost_states = previous_set - current_set

    # If primary state changed, promote all current to new
    primary_changed = any(
        s in new_states for s in (AreaStates.OCCUPIED, AreaStates.CLEAR)
    )
    if primary_changed:
        new_states = set(new_state_list)
        lost_states = set()

    return new_states, lost_states
