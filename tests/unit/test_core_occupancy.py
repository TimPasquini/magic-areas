"""Unit tests for AreaOccupancyTracker occupancy computation paths."""
# ruff: noqa: D102

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_PLAYING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.const import ONE_MINUTE
from custom_components.magic_areas.defaults import (
    DEFAULT_CLEAR_TIMEOUT,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_SLEEP_TIMEOUT,
)
from custom_components.magic_areas.policy import PRESENCE_SENSOR_VALID_ON_STATES

from .core_occupancy_testkit import NOW, make_tracker, occupy


class TestValidOnStates:
    """Test valid_on_states method."""

    def test_meta_area_returns_state_on_only(self) -> None:
        tracker = make_tracker(is_meta=True)
        assert tracker.valid_on_states() == [STATE_ON]

    def test_regular_area_returns_presence_sensor_states(self) -> None:
        tracker = make_tracker()
        assert tracker.valid_on_states() == PRESENCE_SENSOR_VALID_ON_STATES

    def test_additional_states_appended(self) -> None:
        tracker = make_tracker()
        result = tracker.valid_on_states(additional_states=["above_horizon"])
        assert "above_horizon" in result
        assert STATE_ON in result

    def test_meta_ignores_additional_states(self) -> None:
        tracker = make_tracker(is_meta=True)
        assert tracker.valid_on_states(additional_states=["above_horizon"]) == [
            STATE_ON
        ]


class TestComputeSensorsActive:
    """Test compute_sensors_active."""

    def test_returns_active_sensors_matching_valid_states(self) -> None:
        tracker = make_tracker()
        active, any_active = tracker.compute_sensors_active(
            {"s1": STATE_ON, "s2": STATE_OFF}, keep_only=[]
        )
        assert active == ["s1"]
        assert any_active is True

    def test_filters_keep_only_when_not_occupied(self) -> None:
        tracker = make_tracker()
        assert not tracker.is_occupied
        active, any_active = tracker.compute_sensors_active(
            {"s1": STATE_ON, "s2": STATE_ON}, keep_only=["s1"]
        )
        assert active == ["s2"]
        assert any_active is True

    def test_includes_keep_only_when_occupied(self) -> None:
        tracker = make_tracker()
        occupy(tracker)
        assert tracker.is_occupied

        active, any_active = tracker.compute_sensors_active(
            {"s1": STATE_ON, "s2": STATE_OFF}, keep_only=["s1"]
        )
        assert "s1" in active
        assert any_active is True

    def test_skips_none_states(self) -> None:
        tracker = make_tracker()
        active, any_active = tracker.compute_sensors_active({"s1": None}, keep_only=[])
        assert active == []
        assert any_active is False

    def test_skips_invalid_states(self) -> None:
        tracker = make_tracker()
        active, any_active = tracker.compute_sensors_active(
            {"s1": STATE_UNAVAILABLE, "s2": STATE_UNKNOWN}, keep_only=[]
        )
        assert active == []
        assert any_active is False

    def test_empty_sensor_dict(self) -> None:
        tracker = make_tracker()
        active, any_active = tracker.compute_sensors_active({}, keep_only=[])
        assert active == []
        assert any_active is False

    def test_open_state_is_valid(self) -> None:
        tracker = make_tracker()
        active, _ = tracker.compute_sensors_active({"door": STATE_OPEN}, keep_only=[])
        assert active == ["door"]

    def test_playing_state_is_valid(self) -> None:
        tracker = make_tracker()
        active, _ = tracker.compute_sensors_active(
            {"media": STATE_PLAYING}, keep_only=[]
        )
        assert active == ["media"]

    def test_keep_only_all_filtered_returns_no_active(self) -> None:
        tracker = make_tracker()
        active, any_active = tracker.compute_sensors_active(
            {"s1": STATE_ON}, keep_only=["s1"]
        )
        assert active == []
        assert any_active is False


class TestComputeOccupancy:
    """Test compute_occupancy."""

    def test_sensors_active_returns_occupied_and_cancel(self) -> None:
        tracker = make_tracker()
        occupied, timeout, cancel = tracker.compute_occupancy(True, NOW)
        assert occupied is True
        assert timeout is None
        assert cancel is True

    def test_not_active_not_occupied_returns_clear(self) -> None:
        tracker = make_tracker()
        occupied, timeout, cancel = tracker.compute_occupancy(False, NOW)
        assert occupied is False
        assert timeout is None
        assert cancel is False

    def test_not_active_occupied_no_timeout_requests_timeout(self) -> None:
        tracker = make_tracker()
        occupy(tracker)

        occupied, timeout, cancel = tracker.compute_occupancy(False, NOW)
        assert occupied is True
        assert timeout == DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE
        assert cancel is False

    def test_not_active_occupied_on_timeout_not_exceeded(self) -> None:
        tracker = make_tracker()
        occupy(tracker)
        tracker.record_sensor_off(NOW)
        tracker.on_timeout_set()

        future = NOW + timedelta(seconds=30)
        occupied, timeout, cancel = tracker.compute_occupancy(False, future)
        assert occupied is True
        assert timeout is None
        assert cancel is False

    def test_not_active_occupied_on_timeout_exceeded(self) -> None:
        tracker = make_tracker()
        occupy(tracker)
        tracker.record_sensor_off(NOW)
        tracker.on_timeout_set()

        future = NOW + timedelta(seconds=DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE + 1)
        occupied, timeout, cancel = tracker.compute_occupancy(False, future)
        assert occupied is False
        assert timeout is None
        assert cancel is True


class TestClearTimeout:
    """Test get_clear_timeout."""

    def test_default_clear_timeout(self) -> None:
        tracker = make_tracker()
        assert tracker.get_clear_timeout() == DEFAULT_CLEAR_TIMEOUT * ONE_MINUTE

    def test_configured_clear_timeout(self) -> None:
        tracker = make_tracker(config={CONF_CLEAR_TIMEOUT: 5})
        assert tracker.get_clear_timeout() == 5 * ONE_MINUTE

    def test_sleep_state_uses_sleep_timeout(self) -> None:
        tracker = make_tracker(config={CONF_SECONDARY_STATES: {CONF_SLEEP_TIMEOUT: 15}})
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[AreaStates.SLEEP],
            keep_only=[],
            now=NOW,
        )
        assert tracker.has_state(AreaStates.SLEEP)
        assert tracker.get_clear_timeout() == 15 * ONE_MINUTE

    def test_extended_state_uses_extended_timeout(self) -> None:
        tracker = make_tracker(
            config={
                CONF_SECONDARY_STATES: {
                    CONF_EXTENDED_TIMEOUT: 20,
                    CONF_EXTENDED_TIME: 0,
                }
            }
        )
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        tracker.last_changed = NOW - timedelta(hours=1)
        tracker.update(
            sensor_states={"s1": STATE_ON},
            secondary_states=[],
            keep_only=[],
            now=NOW,
        )
        assert tracker.has_state(AreaStates.EXTENDED)
        assert tracker.get_clear_timeout() == 20 * ONE_MINUTE

    def test_sleep_takes_priority_over_extended(self) -> None:
        tracker = make_tracker(
            config={
                CONF_SECONDARY_STATES: {
                    CONF_SLEEP_TIMEOUT: 30,
                    CONF_EXTENDED_TIMEOUT: 20,
                    CONF_EXTENDED_TIME: 0,
                }
            }
        )
        tracker._states = [AreaStates.OCCUPIED, AreaStates.EXTENDED, AreaStates.SLEEP]
        assert tracker.get_clear_timeout() == 30 * ONE_MINUTE

    def test_default_sleep_timeout(self) -> None:
        tracker = make_tracker()
        tracker._states = [AreaStates.OCCUPIED, AreaStates.SLEEP]
        assert tracker.get_clear_timeout() == DEFAULT_SLEEP_TIMEOUT * ONE_MINUTE

    def test_default_extended_timeout(self) -> None:
        tracker = make_tracker()
        tracker._states = [AreaStates.OCCUPIED, AreaStates.EXTENDED]
        assert tracker.get_clear_timeout() == DEFAULT_EXTENDED_TIMEOUT * ONE_MINUTE
