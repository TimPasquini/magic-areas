"""Unit tests for core/occupancy.py — AreaOccupancyTracker."""

from __future__ import annotations

from datetime import datetime, timedelta, UTC


from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_OPEN,
    STATE_PLAYING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from custom_components.magic_areas.config_keys import (
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIME,
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
from custom_components.magic_areas.core.occupancy import (
    AreaOccupancyTracker,
    OccupancyUpdate,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.policy import PRESENCE_SENSOR_VALID_ON_STATES


UTC = UTC
NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _make_tracker(
    config: dict | None = None, is_meta: bool = False
) -> AreaOccupancyTracker:
    """Create a tracker with default config."""
    return AreaOccupancyTracker(config=config or {}, is_meta=is_meta)


def _occupy(
    tracker: AreaOccupancyTracker,
    now: datetime = NOW,
) -> OccupancyUpdate:
    """Drive tracker to occupied state with a single active sensor."""
    return tracker.update(
        sensor_states={"sensor.motion": STATE_ON},
        secondary_states=[],
        keep_only=[],
        now=now,
    )


# ---------------------------------------------------------------------------
# TestValidOnStates
# ---------------------------------------------------------------------------


class TestValidOnStates:
    """Test valid_on_states method."""

    def test_meta_area_returns_state_on_only(self) -> None:
        """Meta area returns state on only."""
        tracker = _make_tracker(is_meta=True)
        assert tracker.valid_on_states() == [STATE_ON]

    def test_regular_area_returns_presence_sensor_states(self) -> None:
        """Regular area returns presence sensor states."""
        tracker = _make_tracker()
        assert tracker.valid_on_states() == PRESENCE_SENSOR_VALID_ON_STATES

    def test_additional_states_appended(self) -> None:
        """Additional states appended."""
        tracker = _make_tracker()
        result = tracker.valid_on_states(additional_states=["above_horizon"])
        assert "above_horizon" in result
        # Original states still present
        assert STATE_ON in result

    def test_meta_ignores_additional_states(self) -> None:
        """Meta areas always return [STATE_ON] regardless of additional."""
        tracker = _make_tracker(is_meta=True)
        assert tracker.valid_on_states(additional_states=["above_horizon"]) == [STATE_ON]


# ---------------------------------------------------------------------------
# TestComputeSensorsActive
# ---------------------------------------------------------------------------


class TestComputeSensorsActive:
    """Test _compute_sensors_active."""

    def test_returns_active_sensors_matching_valid_states(self) -> None:
        """Returns active sensors matching valid states."""
        tracker = _make_tracker()
        active, any_active = tracker._compute_sensors_active(
            {"s1": STATE_ON, "s2": STATE_OFF}, keep_only=[]
        )
        assert active == ["s1"]
        assert any_active is True

    def test_filters_keep_only_when_not_occupied(self) -> None:
        """Filters keep only when not occupied."""
        tracker = _make_tracker()
        assert not tracker.is_occupied
        active, any_active = tracker._compute_sensors_active(
            {"s1": STATE_ON, "s2": STATE_ON}, keep_only=["s1"]
        )
        # s1 is keep-only and area not occupied → filtered out
        assert active == ["s2"]
        assert any_active is True

    def test_includes_keep_only_when_occupied(self) -> None:
        """Includes keep only when occupied."""
        tracker = _make_tracker()
        # Drive to occupied first
        _occupy(tracker)
        assert tracker.is_occupied

        active, any_active = tracker._compute_sensors_active(
            {"s1": STATE_ON, "s2": STATE_OFF}, keep_only=["s1"]
        )
        # s1 included because area is occupied
        assert "s1" in active
        assert any_active is True

    def test_skips_none_states(self) -> None:
        """Skips none states."""
        tracker = _make_tracker()
        active, any_active = tracker._compute_sensors_active(
            {"s1": None}, keep_only=[]
        )
        assert active == []
        assert any_active is False

    def test_skips_invalid_states(self) -> None:
        """Skips invalid states."""
        tracker = _make_tracker()
        active, any_active = tracker._compute_sensors_active(
            {"s1": STATE_UNAVAILABLE, "s2": STATE_UNKNOWN}, keep_only=[]
        )
        assert active == []
        assert any_active is False

    def test_empty_sensor_dict(self) -> None:
        """Empty sensor dict."""
        tracker = _make_tracker()
        active, any_active = tracker._compute_sensors_active({}, keep_only=[])
        assert active == []
        assert any_active is False

    def test_open_state_is_valid(self) -> None:
        """Open state is valid."""
        tracker = _make_tracker()
        active, _ = tracker._compute_sensors_active(
            {"door": STATE_OPEN}, keep_only=[]
        )
        assert active == ["door"]

    def test_playing_state_is_valid(self) -> None:
        """Playing state is valid."""
        tracker = _make_tracker()
        active, _ = tracker._compute_sensors_active(
            {"media": STATE_PLAYING}, keep_only=[]
        )
        assert active == ["media"]

    def test_keep_only_all_filtered_returns_no_active(self) -> None:
        """When all sensors are keep-only and area not occupied, nothing active."""
        tracker = _make_tracker()
        active, any_active = tracker._compute_sensors_active(
            {"s1": STATE_ON}, keep_only=["s1"]
        )
        assert active == []
        assert any_active is False


# ---------------------------------------------------------------------------
# TestComputeOccupancy
# ---------------------------------------------------------------------------


class TestComputeOccupancy:
    """Test _compute_occupancy."""

    def test_sensors_active_returns_occupied_and_cancel(self) -> None:
        """Sensors active returns occupied and cancel."""
        tracker = _make_tracker()
        occupied, timeout, cancel = tracker._compute_occupancy(True, NOW)
        assert occupied is True
        assert timeout is None
        assert cancel is True

    def test_not_active_not_occupied_returns_clear(self) -> None:
        """Not active not occupied returns clear."""
        tracker = _make_tracker()
        occupied, timeout, cancel = tracker._compute_occupancy(False, NOW)
        assert occupied is False
        assert timeout is None
        assert cancel is False

    def test_not_active_occupied_no_timeout_requests_timeout(self) -> None:
        """Not active occupied no timeout requests timeout."""
        tracker = _make_tracker()
        _occupy(tracker)

        occupied, timeout, cancel = tracker._compute_occupancy(False, NOW)
        assert occupied is True
        assert timeout == DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE
        assert cancel is False

    def test_not_active_occupied_on_timeout_not_exceeded(self) -> None:
        """Not active occupied on timeout not exceeded."""
        tracker = _make_tracker()
        _occupy(tracker)
        tracker.record_sensor_off(NOW)
        tracker.on_timeout_set()

        # Check 30s later (timeout is 1 min default)
        future = NOW + timedelta(seconds=30)
        occupied, timeout, cancel = tracker._compute_occupancy(False, future)
        assert occupied is True
        assert timeout is None
        assert cancel is False

    def test_not_active_occupied_on_timeout_exceeded(self) -> None:
        """Not active occupied on timeout exceeded."""
        tracker = _make_tracker()
        _occupy(tracker)
        tracker.record_sensor_off(NOW)
        tracker.on_timeout_set()

        # Check past timeout
        future = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 1)
        occupied, timeout, cancel = tracker._compute_occupancy(False, future)
        assert occupied is False
        assert timeout is None
        assert cancel is True


# ---------------------------------------------------------------------------
# TestClearTimeout
# ---------------------------------------------------------------------------


class TestClearTimeout:
    """Test get_clear_timeout."""

    def test_default_clear_timeout(self) -> None:
        """Default clear timeout."""
        tracker = _make_tracker()
        assert tracker.get_clear_timeout() == DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE

    def test_configured_clear_timeout(self) -> None:
        """Configured clear timeout."""
        tracker = _make_tracker(config={CONF_CLEAR_TIMEOUT: 5})
        assert tracker.get_clear_timeout() == 5 * ONE_MINUTE

    def test_sleep_state_uses_sleep_timeout(self) -> None:
        """Sleep state uses sleep timeout."""
        tracker = _make_tracker(
            config={
                CONF_SECONDARY_STATES: {CONF_SLEEP_TIMEOUT: 15},
            }
        )
        # Drive to occupied + sleep state
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.SLEEP],
            keep_only=[],
            now=NOW,
        )
        assert tracker.has_state(AreaStates.SLEEP)
        assert tracker.get_clear_timeout() == 15 * ONE_MINUTE

    def test_extended_state_uses_extended_timeout(self) -> None:
        """Extended state uses extended timeout."""
        tracker = _make_tracker(
            config={
                CONF_SECONDARY_STATES: {
                    CONF_EXTENDED_TIMEOUT: 20,
                    CONF_EXTENDED_TIME: 0,  # immediate extended
                },
            }
        )
        # Drive to occupied + extended
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        # Extended requires time to pass — set last_changed far in the past
        tracker._last_changed = NOW - timedelta(hours=1)
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        assert tracker.has_state(AreaStates.EXTENDED)
        assert tracker.get_clear_timeout() == 20 * ONE_MINUTE

    def test_sleep_takes_priority_over_extended(self) -> None:
        """Sleep timeout is checked before extended."""
        tracker = _make_tracker(
            config={
                CONF_SECONDARY_STATES: {
                    CONF_SLEEP_TIMEOUT: 30,
                    CONF_EXTENDED_TIMEOUT: 20,
                    CONF_EXTENDED_TIME: 0,
                },
            }
        )
        # Give it both sleep and extended
        tracker._states = [AreaStates.OCCUPIED, AreaStates.EXTENDED, AreaStates.SLEEP]
        assert tracker.get_clear_timeout() == 30 * ONE_MINUTE

    def test_default_sleep_timeout(self) -> None:
        """Sleep timeout defaults when not configured."""
        tracker = _make_tracker()
        tracker._states = [AreaStates.OCCUPIED, AreaStates.SLEEP]
        assert tracker.get_clear_timeout() == DEFAULT_SLEEP_TIMEOUT * ONE_MINUTE

    def test_default_extended_timeout(self) -> None:
        """Extended timeout defaults when not configured."""
        tracker = _make_tracker()
        tracker._states = [AreaStates.OCCUPIED, AreaStates.EXTENDED]
        assert tracker.get_clear_timeout() == DEFAULT_EXTENDED_TIMEOUT * ONE_MINUTE


# ---------------------------------------------------------------------------
# TestUpdate (end-to-end)
# ---------------------------------------------------------------------------


class TestUpdate:
    """Test the full update cycle."""

    def test_sensor_on_produces_occupied(self) -> None:
        """Sensor on produces occupied."""
        tracker = _make_tracker()
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        assert AreaStates.OCCUPIED in result.current_states
        assert AreaStates.CLEAR not in result.current_states
        assert tracker.is_occupied
        assert result.cancel_timeout is True  # sensors active → cancel

    def test_sensor_off_still_occupied_timeout_requested(self) -> None:
        """Sensor off still occupied timeout requested."""
        tracker = _make_tracker()
        _occupy(tracker)

        result = tracker.update(
            sensor_states={"s1": STATE_OFF},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        assert AreaStates.OCCUPIED in result.current_states
        assert result.request_timeout is not None
        assert result.request_timeout == DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE
        assert tracker.is_occupied

    def test_timeout_exceeded_clears(self) -> None:
        """Timeout exceeded clears."""
        tracker = _make_tracker()
        _occupy(tracker)

        # Simulate sensor off + timeout
        tracker.record_sensor_off(NOW)
        tracker.on_timeout_set()

        future = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 1)
        result = tracker.update(
            sensor_states={"s1": STATE_OFF},
            secondary_states=[],
            keep_only=[],
            now=future,
        )
        assert AreaStates.CLEAR in result.current_states
        assert AreaStates.OCCUPIED not in result.current_states
        assert not tracker.is_occupied
        assert result.cancel_timeout is True

    def test_secondary_states_included(self) -> None:
        """Secondary states included."""
        tracker = _make_tracker()
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK, AreaStates.SLEEP],
            keep_only=[],
            now=NOW,
        )
        assert AreaStates.DARK in result.current_states
        assert AreaStates.SLEEP in result.current_states

    def test_extended_state_after_time(self) -> None:
        """Extended state after time."""
        tracker = _make_tracker(
            config={CONF_SECONDARY_STATES: {CONF_EXTENDED_TIME: 5}}
        )
        _occupy(tracker, NOW)

        # 6 minutes later, still occupied
        future = NOW + timedelta(minutes=6)
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=future,
        )
        assert AreaStates.EXTENDED in result.current_states

    def test_no_extended_before_time(self) -> None:
        """No extended before time."""
        tracker = _make_tracker(
            config={CONF_SECONDARY_STATES: {CONF_EXTENDED_TIME: 5}}
        )
        _occupy(tracker, NOW)

        # 3 minutes later
        future = NOW + timedelta(minutes=3)
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=future,
        )
        assert AreaStates.EXTENDED not in result.current_states

    def test_state_diff_new_and_lost(self) -> None:
        """State diff new and lost."""
        tracker = _make_tracker()
        # Start with occupied + dark
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=NOW,
        )

        # Now change to occupied + sleep (lose dark, gain sleep)
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.SLEEP],
            keep_only=[],
            now=NOW + timedelta(seconds=1),
        )
        assert AreaStates.SLEEP in result.new_states
        assert AreaStates.DARK in result.lost_states

    def test_primary_change_promotes_all_to_new(self) -> None:
        """Primary change promotes all to new."""
        tracker = _make_tracker()
        _occupy(tracker, NOW)

        # Simulate sensor off + timeout to drive to clear
        tracker.record_sensor_off(NOW)
        tracker.on_timeout_set()

        future = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 1)
        result = tracker.update(
            sensor_states={},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=future,
        )
        # Primary changed to CLEAR → all current states promoted to new_states
        assert AreaStates.CLEAR in result.current_states
        assert set(result.current_states) == result.new_states
        assert result.lost_states == set()

    def test_no_change_returns_empty_sets(self) -> None:
        """No change returns empty sets."""
        tracker = _make_tracker()
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=NOW,
        )

        # Same state again
        result2 = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=NOW + timedelta(seconds=1),
        )
        assert result2.new_states == set()
        assert result2.lost_states == set()
        assert result2.states_changed is False

    def test_last_changed_updates_on_transition(self) -> None:
        """Last changed updates on transition."""
        tracker = _make_tracker()
        t1 = NOW
        _occupy(tracker, t1)
        assert tracker.last_changed == t1

        # Drive through full timeout cycle to clear
        tracker.record_sensor_off(t1)
        tracker.on_timeout_set()

        t2 = t1 + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 1)
        tracker.update(
            sensor_states={}, secondary_states=[], keep_only=[], now=t2
        )
        assert tracker.last_changed == t2
        assert not tracker.is_occupied

    def test_last_changed_does_not_update_without_transition(self) -> None:
        """Last changed does not update without transition."""
        tracker = _make_tracker()
        _occupy(tracker, NOW)
        lc1 = tracker.last_changed

        # Still occupied — no transition
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW + timedelta(seconds=10),
        )
        assert tracker.last_changed == lc1

    def test_active_sensors_rotated(self) -> None:
        """Active sensors rotated."""
        tracker = _make_tracker()
        tracker.update(
            sensor_states={"s1": STATE_ON, "s2": STATE_OFF},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        assert tracker.active_sensors == ["s1"]
        assert tracker.last_active_sensors == []

        tracker.update(
            sensor_states={"s1": STATE_OFF, "s2": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW + timedelta(seconds=1),
        )
        assert tracker.active_sensors == ["s2"]
        assert tracker.last_active_sensors == ["s1"]


# ---------------------------------------------------------------------------
# TestMetaArea
# ---------------------------------------------------------------------------


class TestMetaArea:
    """Test meta-area specific behavior."""

    def test_valid_on_states_meta(self) -> None:
        """Valid on states meta."""
        tracker = _make_tracker(is_meta=True)
        assert tracker.valid_on_states() == [STATE_ON]

    def test_occupancy_works_same_as_regular(self) -> None:
        """Occupancy works same as regular."""
        tracker = _make_tracker(is_meta=True)
        result = _occupy(tracker, NOW)
        assert tracker.is_occupied
        assert AreaStates.OCCUPIED in result.current_states


# ---------------------------------------------------------------------------
# TestRecordSensorOff
# ---------------------------------------------------------------------------


class TestRecordSensorOff:
    """Test record_sensor_off."""

    def test_updates_last_off_time(self) -> None:
        """Updates last off time."""
        tracker = _make_tracker()
        t = NOW + timedelta(minutes=5)
        tracker.record_sensor_off(t)
        assert tracker._last_off_time == t


# ---------------------------------------------------------------------------
# TestTimeoutCallbacks
# ---------------------------------------------------------------------------


class TestTimeoutCallbacks:
    """Test on_timeout_set / on_timeout_cleared."""

    def test_on_timeout_set(self) -> None:
        """On timeout set."""
        tracker = _make_tracker()
        assert tracker._is_on_timeout is False
        tracker.on_timeout_set()
        assert tracker._is_on_timeout is True

    def test_on_timeout_cleared(self) -> None:
        """On timeout cleared."""
        tracker = _make_tracker()
        tracker.on_timeout_set()
        tracker.on_timeout_cleared()
        assert tracker._is_on_timeout is False


# ---------------------------------------------------------------------------
# TestOccupancyUpdate dataclass
# ---------------------------------------------------------------------------


class TestOccupancyUpdate:
    """Test OccupancyUpdate dataclass defaults."""

    def test_defaults(self) -> None:
        """Defaults."""
        update = OccupancyUpdate(
            states_changed=False,
            new_states=set(),
            lost_states=set(),
            current_states=[],
        )
        assert update.request_timeout is None
        assert update.cancel_timeout is False

    def test_with_values(self) -> None:
        """With values."""
        update = OccupancyUpdate(
            states_changed=True,
            new_states={AreaStates.OCCUPIED},
            lost_states={AreaStates.CLEAR},
            current_states=[AreaStates.OCCUPIED, AreaStates.DARK],
            request_timeout=60.0,
            cancel_timeout=True,
        )
        assert update.request_timeout == 60.0
        assert update.cancel_timeout is True


# ---------------------------------------------------------------------------
# TestCheckTimeoutExceeded
# ---------------------------------------------------------------------------


class TestCheckTimeoutExceeded:
    """Test _check_timeout_exceeded."""

    def test_not_exceeded(self) -> None:
        """Not exceeded."""
        tracker = _make_tracker()
        tracker.record_sensor_off(NOW)
        # 30s later, default timeout is 60s
        assert tracker._check_timeout_exceeded(NOW + timedelta(seconds=30)) is False

    def test_exactly_at_boundary(self) -> None:
        """Exactly at boundary."""
        tracker = _make_tracker()
        tracker.record_sensor_off(NOW)
        boundary = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE)
        assert tracker._check_timeout_exceeded(boundary) is True

    def test_exceeded(self) -> None:
        """Exceeded."""
        tracker = _make_tracker()
        tracker.record_sensor_off(NOW)
        future = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 10)
        assert tracker._check_timeout_exceeded(future) is True


# ---------------------------------------------------------------------------
# TestLastChangedSetter
# ---------------------------------------------------------------------------


class TestLastChangedSetter:
    """Test last_changed property setter."""

    def test_set_last_changed(self) -> None:
        """Set last changed."""
        tracker = _make_tracker()
        t = NOW + timedelta(hours=1)
        tracker.last_changed = t
        assert tracker.last_changed == t


# ---------------------------------------------------------------------------
# TestProperties
# ---------------------------------------------------------------------------


class TestProperties:
    """Test read-only properties."""

    def test_states_returns_copy(self) -> None:
        """States returns copy."""
        tracker = _make_tracker()
        _occupy(tracker, NOW)
        states = tracker.states
        states.append("garbage")
        assert "garbage" not in tracker.states

    def test_active_sensors_returns_copy(self) -> None:
        """Active sensors returns copy."""
        tracker = _make_tracker()
        _occupy(tracker, NOW)
        sensors = tracker.active_sensors
        sensors.append("garbage")
        assert "garbage" not in tracker.active_sensors

    def test_last_active_sensors_returns_copy(self) -> None:
        """Last active sensors returns copy."""
        tracker = _make_tracker()
        sensors = tracker.last_active_sensors
        sensors.append("garbage")
        assert "garbage" not in tracker.last_active_sensors

    def test_initial_states(self) -> None:
        """Initial states."""
        tracker = _make_tracker()
        assert tracker.states == []
        assert tracker.is_occupied is False
        assert tracker.active_sensors == []
        assert tracker.last_active_sensors == []

    def test_has_state_false_initially(self) -> None:
        """Has state false initially."""
        tracker = _make_tracker()
        assert tracker.has_state(AreaStates.OCCUPIED) is False
        assert tracker.has_state(AreaStates.CLEAR) is False

    def test_zero_clear_timeout_immediately_clears(self) -> None:
        """Test that clear_timeout of 0 immediately clears instead of requesting timeout."""
        tracker = _make_tracker(config={CONF_CLEAR_TIMEOUT: 0})
        _occupy(tracker)

        # When sensors go inactive with zero timeout, should immediately clear
        occupied, timeout, cancel = tracker._compute_occupancy(False, NOW)
        assert occupied is False
        assert timeout is None
        assert cancel is False

    def test_zero_clear_timeout_with_secondary_states(self) -> None:
        """Test that zero timeout still clears even with secondary states present."""
        tracker = _make_tracker(
            config={
                CONF_CLEAR_TIMEOUT: 0,
                CONF_SECONDARY_STATES: {CONF_SLEEP_TIMEOUT: 0},
            }
        )
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.SLEEP],
            keep_only=[],
            now=NOW,
        )
        assert tracker.is_occupied is True

        # When sensors go inactive, should immediately clear even in sleep state
        occupied, timeout, cancel = tracker._compute_occupancy(False, NOW)
        assert occupied is False
        assert timeout is None
        assert cancel is False
