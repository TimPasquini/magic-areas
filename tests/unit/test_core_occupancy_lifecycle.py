"""Unit tests for AreaOccupancyTracker lifecycle/update contracts."""
# ruff: noqa: D102

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIME,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.const import ONE_MINUTE
from custom_components.magic_areas.defaults import DEFAULT_CLEAR_TIMEOUT
from custom_components.magic_areas.core.occupancy import OccupancyUpdate

from .core_occupancy_testkit import NOW, make_tracker, occupy


class TestUpdate:
    """Test the full update cycle."""

    def test_sensor_on_produces_occupied(self) -> None:
        tracker = make_tracker()
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        assert AreaStates.OCCUPIED in result.current_states
        assert AreaStates.CLEAR not in result.current_states
        assert tracker.is_occupied
        assert result.cancel_timeout is True

    def test_sensor_off_still_occupied_timeout_requested(self) -> None:
        tracker = make_tracker()
        occupy(tracker)

        result = tracker.update(
            sensor_states={"s1": STATE_OFF},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        assert AreaStates.OCCUPIED in result.current_states
        assert result.request_timeout == DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE
        assert tracker.is_occupied

    def test_timeout_exceeded_clears(self) -> None:
        tracker = make_tracker()
        occupy(tracker)
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
        tracker = make_tracker()
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK, AreaStates.SLEEP],
            keep_only=[],
            now=NOW,
        )
        assert AreaStates.DARK in result.current_states
        assert AreaStates.SLEEP in result.current_states

    def test_extended_state_after_time(self) -> None:
        tracker = make_tracker(config={CONF_SECONDARY_STATES: {CONF_EXTENDED_TIME: 5}})
        occupy(tracker, NOW)

        future = NOW + timedelta(minutes=6)
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=future,
        )
        assert AreaStates.EXTENDED in result.current_states

    def test_no_extended_before_time(self) -> None:
        tracker = make_tracker(config={CONF_SECONDARY_STATES: {CONF_EXTENDED_TIME: 5}})
        occupy(tracker, NOW)

        future = NOW + timedelta(minutes=3)
        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=future,
        )
        assert AreaStates.EXTENDED not in result.current_states

    def test_state_diff_new_and_lost(self) -> None:
        tracker = make_tracker()
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=NOW,
        )

        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.SLEEP],
            keep_only=[],
            now=NOW + timedelta(seconds=1),
        )
        assert AreaStates.SLEEP in result.new_states
        assert AreaStates.DARK in result.lost_states

    def test_primary_change_promotes_all_to_new(self) -> None:
        tracker = make_tracker()
        occupy(tracker, NOW)
        tracker.record_sensor_off(NOW)
        tracker.on_timeout_set()

        future = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 1)
        result = tracker.update(
            sensor_states={},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=future,
        )
        assert AreaStates.CLEAR in result.current_states
        assert set(result.current_states) == result.new_states
        assert result.lost_states == set()

    def test_no_change_returns_empty_sets(self) -> None:
        tracker = make_tracker()
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=NOW,
        )

        result = tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.DARK],
            keep_only=[],
            now=NOW + timedelta(seconds=1),
        )
        assert result.new_states == set()
        assert result.lost_states == set()
        assert result.states_changed is False

    def test_last_changed_updates_on_transition(self) -> None:
        tracker = make_tracker()
        t1 = NOW
        occupy(tracker, t1)
        assert tracker.last_changed == t1

        tracker.record_sensor_off(t1)
        tracker.on_timeout_set()

        t2 = t1 + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 1)
        tracker.update(sensor_states={}, secondary_states=[], keep_only=[], now=t2)
        assert tracker.last_changed == t2
        assert not tracker.is_occupied

    def test_last_changed_does_not_update_without_transition(self) -> None:
        tracker = make_tracker()
        occupy(tracker, NOW)
        lc1 = tracker.last_changed

        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW + timedelta(seconds=10),
        )
        assert tracker.last_changed == lc1

    def test_active_sensors_rotated(self) -> None:
        tracker = make_tracker()
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


class TestMetaArea:
    """Test meta-area specific behavior."""

    def test_valid_on_states_meta(self) -> None:
        tracker = make_tracker(is_meta=True)
        assert tracker.valid_on_states() == [STATE_ON]

    def test_occupancy_works_same_as_regular(self) -> None:
        tracker = make_tracker(is_meta=True)
        result = occupy(tracker, NOW)
        assert tracker.is_occupied
        assert AreaStates.OCCUPIED in result.current_states


class TestRecordSensorOff:
    """Test record_sensor_off."""

    def test_updates_last_off_time(self) -> None:
        tracker = make_tracker()
        t = NOW + timedelta(minutes=5)
        tracker.record_sensor_off(t)
        assert tracker._last_off_time == t


class TestTimeoutCallbacks:
    """Test on_timeout_set / on_timeout_cleared."""

    def test_on_timeout_set(self) -> None:
        tracker = make_tracker()
        assert tracker._is_on_timeout is False
        tracker.on_timeout_set()
        assert tracker._is_on_timeout is True

    def test_on_timeout_cleared(self) -> None:
        tracker = make_tracker()
        tracker.on_timeout_set()
        tracker.on_timeout_cleared()
        assert tracker._is_on_timeout is False


class TestOccupancyUpdate:
    """Test OccupancyUpdate dataclass defaults."""

    def test_defaults(self) -> None:
        update = OccupancyUpdate(
            states_changed=False,
            new_states=set(),
            lost_states=set(),
            current_states=[],
        )
        assert update.request_timeout is None
        assert update.cancel_timeout is False

    def test_with_values(self) -> None:
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


class TestCheckTimeoutExceeded:
    """Test check_timeout_exceeded."""

    def test_not_exceeded(self) -> None:
        tracker = make_tracker()
        tracker.record_sensor_off(NOW)
        assert tracker.check_timeout_exceeded(NOW + timedelta(seconds=30)) is False

    def test_exactly_at_boundary(self) -> None:
        tracker = make_tracker()
        tracker.record_sensor_off(NOW)
        boundary = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE)
        assert tracker.check_timeout_exceeded(boundary) is True

    def test_exceeded(self) -> None:
        tracker = make_tracker()
        tracker.record_sensor_off(NOW)
        future = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 10)
        assert tracker.check_timeout_exceeded(future) is True


class TestLastChangedSetter:
    """Test last_changed property setter."""

    def test_set_last_changed(self) -> None:
        tracker = make_tracker()
        t = NOW + timedelta(hours=1)
        tracker.last_changed = t
        assert tracker.last_changed == t


class TestProperties:
    """Test read-only properties."""

    def test_states_returns_copy(self) -> None:
        tracker = make_tracker()
        occupy(tracker, NOW)
        states = tracker.states
        states.append("garbage")
        assert "garbage" not in tracker.states

    def test_active_sensors_returns_copy(self) -> None:
        tracker = make_tracker()
        occupy(tracker, NOW)
        sensors = tracker.active_sensors
        sensors.append("garbage")
        assert "garbage" not in tracker.active_sensors

    def test_last_active_sensors_returns_copy(self) -> None:
        tracker = make_tracker()
        sensors = tracker.last_active_sensors
        sensors.append("garbage")
        assert "garbage" not in tracker.last_active_sensors

    def test_initial_states(self) -> None:
        tracker = make_tracker()
        assert tracker.states == []
        assert tracker.is_occupied is False
        assert tracker.active_sensors == []
        assert tracker.last_active_sensors == []

    def test_has_state_false_initially(self) -> None:
        tracker = make_tracker()
        assert tracker.has_state(AreaStates.OCCUPIED) is False
        assert tracker.has_state(AreaStates.CLEAR) is False

    def test_zero_clear_timeout_immediately_clears(self) -> None:
        tracker = make_tracker(config={CONF_CLEAR_TIMEOUT: 0})
        occupy(tracker)

        occupied, timeout, cancel = tracker.compute_occupancy(False, NOW)
        assert occupied is False
        assert timeout is None
        assert cancel is False

    def test_zero_clear_timeout_with_secondary_states(self) -> None:
        tracker = make_tracker(
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

        occupied, timeout, cancel = tracker.compute_occupancy(False, NOW)
        assert occupied is False
        assert timeout is None
        assert cancel is False
