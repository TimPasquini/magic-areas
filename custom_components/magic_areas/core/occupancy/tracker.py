"""Area occupancy state machine for Magic Areas.

Encapsulates all occupancy tracking state and computation as a cohesive
domain object. The tracker receives pre-built sensor state dicts and returns
OccupancyUpdate results — consistent with the existing policy pattern
(LightGroupPolicy, FanControlPolicy, ClimatePresetPolicy).

No Home Assistant entity classes are imported.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from datetime import timedelta

from homeassistant.const import STATE_ON

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
)
from custom_components.magic_areas.const import ONE_MINUTE
from custom_components.magic_areas.core.config import (
    extended_time_minutes,
    extended_timeout_minutes,
    sleep_timeout_minutes,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_CLEAR_TIMEOUT,
)
from custom_components.magic_areas.policy import (
    INVALID_STATES,
    PRESENCE_SENSOR_VALID_ON_STATES,
)


@dataclass(slots=True)
class OccupancyUpdate:
    """Result of an occupancy state update cycle."""

    states_changed: bool
    new_states: set[str]
    lost_states: set[str]
    current_states: list[str]
    request_timeout: float | None = None
    cancel_timeout: bool = False


class AreaOccupancyTracker:
    """Owns all occupancy state and computation for an area.

    Receives pre-built sensor state dicts (same pattern as existing core/
    modules). Returns OccupancyUpdate results (same pattern as
    LightGroupDecision, FanControlDecision).
    """

    def __init__(self, config: dict[str, object], is_meta: bool) -> None:
        """Initialize occupancy tracker with config and area type."""
        self._config = config
        self._is_meta = is_meta

        self._states: list[str] = []
        self._last_changed: datetime = datetime.min.replace(tzinfo=UTC)
        self._last_off_time: datetime = datetime.min.replace(tzinfo=UTC)
        self._active_sensors: list[str] = []
        self._last_active_sensors: list[str] = []
        self._is_on_timeout: bool = False

    # -- Read-only properties --

    @property
    def states(self) -> list[str]:
        """Return current area states."""
        return list(self._states)

    @property
    def is_occupied(self) -> bool:
        """Return whether the area is currently occupied."""
        return AreaStates.OCCUPIED in self._states

    @property
    def last_changed(self) -> datetime:
        """Return timestamp of last occupancy transition."""
        return self._last_changed

    @last_changed.setter
    def last_changed(self, value: datetime) -> None:
        """Set last_changed (for initialization from restored state)."""
        self._last_changed = value

    @property
    def active_sensors(self) -> list[str]:
        """Return currently active presence sensors."""
        return list(self._active_sensors)

    @property
    def last_active_sensors(self) -> list[str]:
        """Return previously active presence sensors."""
        return list(self._last_active_sensors)

    # -- Public methods --

    def has_state(self, state: str) -> bool:
        """Check if area has a given state."""
        return state in self._states

    def valid_on_states(self, additional_states: list[str] | None = None) -> list[str]:
        """Return valid ON states for presence sensors."""
        return valid_on_states(self._is_meta, additional_states)

    def get_clear_timeout(self) -> float:
        """Return current timeout value in seconds."""
        return get_clear_timeout(self._config, self._states)

    def record_sensor_off(self, now: datetime) -> None:
        """Record sensor-off timestamp."""
        self._last_off_time = now

    def on_timeout_set(self) -> None:
        """Record that entity scheduled a timeout."""
        self._is_on_timeout = True

    def on_timeout_cleared(self) -> None:
        """Record that entity cancelled a timeout."""
        self._is_on_timeout = False

    def update(
        self,
        sensor_states: dict[str, str | None],
        secondary_states: list[str],
        keep_only: list[str],
        now: datetime,
    ) -> OccupancyUpdate:
        """Run the full occupancy state update cycle.

        Args:
            sensor_states: Map of sensor_id → current state (or None if not found).
            secondary_states: Secondary states computed by the entity (dark, sleep, etc.).
            keep_only: Entity IDs that should only count when already occupied.
            now: Current UTC timestamp.

        Returns:
            OccupancyUpdate with state diff and timeout instructions.

        """
        # 1. Compute which sensors are active
        active_list, any_active = compute_sensors_active(
            sensor_states,
            keep_only,
            self.is_occupied,
            self.valid_on_states(),
        )

        # 2. Track active sensors (rotate current → last)
        if self._active_sensors:
            self._last_active_sensors = list(self._active_sensors)
        self._active_sensors = active_list

        # 3. Compute occupancy
        was_occupied = self.is_occupied
        occupied, timeout_to_request, should_cancel = compute_occupancy(
            any_active,
            self.is_occupied,
            self._is_on_timeout,
            self._last_off_time,
            now,
            self.get_clear_timeout(),
        )

        # 4. Track last_changed on occupancy transition
        if occupied != was_occupied:
            self._last_changed = now

        # 5. Build state list
        new_state_list = build_state_list(
            occupied,
            self._last_changed,
            now,
            self._config,
            secondary_states,
        )

        # 6. Diff against previous states
        new_states, lost_states = diff_states(self._states, new_state_list)

        # Update internal state
        self._states = list(new_state_list)

        return OccupancyUpdate(
            states_changed=bool(new_states or lost_states),
            new_states=new_states,
            lost_states=lost_states,
            current_states=list(new_state_list),
            request_timeout=timeout_to_request,
            cancel_timeout=should_cancel,
        )

    # -- Public computation helpers --

    def compute_sensors_active(
        self,
        sensor_states: dict[str, str | None],
        keep_only: list[str],
    ) -> tuple[list[str], bool]:
        """Compute active sensors against current tracker state."""
        return compute_sensors_active(
            sensor_states,
            keep_only,
            self.is_occupied,
            self.valid_on_states(),
        )

    def compute_occupancy(
        self, any_active: bool, now: datetime
    ) -> tuple[bool, float | None, bool]:
        """Compute occupancy transition for current tracker state."""
        return compute_occupancy(
            any_active,
            self.is_occupied,
            self._is_on_timeout,
            self._last_off_time,
            now,
            self.get_clear_timeout(),
        )

    def check_timeout_exceeded(self, now: datetime) -> bool:
        """Check if clear timeout has elapsed for current tracker state."""
        return check_timeout_exceeded(
            self._last_off_time,
            self.get_clear_timeout(),
            now,
        )


def get_clear_timeout(config: dict[str, object], states: list[str]) -> float:
    """Return current timeout value in seconds."""
    if AreaStates.SLEEP in states:
        return sleep_timeout_minutes(config) * ONE_MINUTE

    if AreaStates.EXTENDED in states:
        return extended_timeout_minutes(config) * ONE_MINUTE

    configured_timeout = config.get(CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT)
    if isinstance(configured_timeout, (int, float)):
        return float(configured_timeout) * ONE_MINUTE
    return DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE


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
    """Compute occupancy from sensor activity."""
    if any_active:
        return True, None, True

    if not is_occupied:
        return False, None, False

    if is_on_timeout:
        if check_timeout_exceeded(last_off_time, clear_timeout, now):
            return False, None, True
        return True, None, False

    if clear_timeout == 0:
        return False, None, False

    return True, clear_timeout, False


def valid_on_states(
    is_meta: bool, additional_states: list[str] | None = None
) -> list[str]:
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
    config: dict[str, object],
    secondary_states: list[str],
) -> list[str]:
    """Build current area state list."""
    new_state_list: list[str] = []
    new_state_list.append(AreaStates.OCCUPIED if occupied else AreaStates.CLEAR)

    if occupied:
        seconds_since = (now - last_changed).total_seconds()
        extended_time = extended_time_minutes(config)
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

    primary_changed = any(
        s in new_states for s in (AreaStates.OCCUPIED, AreaStates.CLEAR)
    )
    if primary_changed:
        new_states = set(new_state_list)
        lost_states = set()

    return new_states, lost_states
