"""Unit tests for core.wasp_state_machine module."""

from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.magic_areas.core.wasp_state_machine import (
    WaspStateMachine,
    WaspStateUpdate,
)


class TestWaspStateUpdate:
    """Tests for WaspStateUpdate dataclass."""

    def test_wasp_state_update_creation(self) -> None:
        """Test creating a WaspStateUpdate."""
        update = WaspStateUpdate(
            is_present=True,
            wasp_active=True,
            box_open=False,
            request_timer=None,
            cancel_timer=False,
        )
        assert update.is_present is True
        assert update.wasp_active is True
        assert update.box_open is False
        assert update.request_timer is None
        assert update.cancel_timer is False

    def test_wasp_state_update_with_timer(self) -> None:
        """Test WaspStateUpdate with timer request."""
        update = WaspStateUpdate(
            is_present=True,
            wasp_active=True,
            box_open=False,
            request_timer=300.0,
            cancel_timer=False,
        )
        assert update.request_timer == 300.0


class TestWaspStateMachineInitialization:
    """Tests for WaspStateMachine initialization."""

    def test_init_with_timeout(self) -> None:
        """Test machine initialization with timeout."""
        machine = WaspStateMachine(wasp_timeout=300)
        assert machine._wasp_timeout == 300
        assert machine.wasp is False
        assert machine._timeout_requested is False

    def test_init_no_timeout(self) -> None:
        """Test machine initialization without timeout."""
        machine = WaspStateMachine(wasp_timeout=0)
        assert machine._wasp_timeout == 0
        assert machine.wasp is False

    def test_is_present_initial(self) -> None:
        """Test initial is_present state."""
        machine = WaspStateMachine(wasp_timeout=300)
        assert machine.is_present is False

    def test_wasp_active_initial(self) -> None:
        """Test initial wasp_active state."""
        machine = WaspStateMachine(wasp_timeout=300)
        assert machine.wasp is False


class TestWaspUpdate:
    """Tests for wasp sensor state updates."""

    def test_update_wasp_sensor_on(self) -> None:
        """Test wasp sensor turning ON → motion detected."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_wasp({
            "motion_sensor_1": STATE_ON,
            "motion_sensor_2": STATE_OFF,
        })
        assert result.wasp_active is True
        assert result.is_present is True
        assert result.box_open is False
        assert result.cancel_timer is True
        assert machine.wasp is True

    def test_update_wasp_sensor_off(self) -> None:
        """Test wasp sensor turning OFF when box also OFF."""
        machine = WaspStateMachine(wasp_timeout=300)
        # First set wasp active
        machine.update_wasp({
            "motion_sensor": STATE_ON,
        })
        # Then all OFF with timeout configured
        result = machine.update_wasp({
            "motion_sensor": STATE_OFF,
        })
        # Should request timer to eventually clear wasp
        assert result.wasp_active is True  # Still active, waiting for timeout
        assert result.request_timer == 300.0
        assert machine.wasp is True

    def test_update_wasp_empty_dict(self) -> None:
        """Test update with empty sensor dict → all OFF."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_wasp({})
        assert result.wasp_active is False
        assert result.box_open is False


class TestBoxUpdate:
    """Tests for box sensor state updates."""

    def test_update_box_open(self) -> None:
        """Test box sensor turning ON → door open."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_box({
            "door_sensor_1": STATE_ON,
            "door_sensor_2": STATE_OFF,
        })
        assert result.box_open is True
        assert result.wasp_active is False
        assert result.cancel_timer is True

    def test_update_box_open_clears_wasp(self) -> None:
        """Test box opening clears wasp and cancels timer.

        When the box (door) opens, the wasp must have exited, so clear it.
        """
        machine = WaspStateMachine(wasp_timeout=300)
        # Set wasp active first
        machine.wasp = True
        machine._timeout_requested = True

        # Then box opens (sensor ON)
        result = machine.update_box({
            "door_sensor": STATE_ON,
        })
        assert result.wasp_active is False
        assert result.box_open is True
        assert result.cancel_timer is True
        assert machine.wasp is False

    def test_update_box_empty_dict(self) -> None:
        """Test update with empty sensor dict → box OFF."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_box({})
        assert result.box_open is False


class TestCombinedUpdate:
    """Tests for update_all() with both sensors."""

    def test_wasp_on_box_off(self) -> None:
        """Test motion detected while door is closed."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_all(
            {"motion": STATE_ON},
            {"door": STATE_OFF},
        )
        assert result.wasp_active is True
        assert result.box_open is False
        assert result.is_present is True

    def test_wasp_off_box_on(self) -> None:
        """Test no motion while door is open."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_ON},
        )
        assert result.wasp_active is False
        assert result.box_open is True
        assert result.is_present is False  # box open but no wasp

    def test_wasp_on_box_on(self) -> None:
        """Test motion detected while door is open."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_all(
            {"motion": STATE_ON},
            {"door": STATE_ON},
        )
        assert result.wasp_active is True
        assert result.box_open is True
        assert result.is_present is True

    def test_wasp_off_box_off_no_timeout(self) -> None:
        """Test both OFF with no previous state → stay OFF."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert result.wasp_active is False
        assert result.box_open is False
        assert result.is_present is False
        assert result.request_timer is None

    def test_wasp_off_box_off_after_motion(self) -> None:
        """Test both OFF after motion detected → request timer."""
        machine = WaspStateMachine(wasp_timeout=300)
        # First detect motion
        machine.update_all(
            {"motion": STATE_ON},
            {"door": STATE_OFF},
        )
        # Then both OFF
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert result.wasp_active is True  # Waiting for timeout
        assert result.request_timer == 300.0

    def test_wasp_timeout_zero(self) -> None:
        """Test with timeout=0 → no timer requested."""
        machine = WaspStateMachine(wasp_timeout=0)
        # Detect motion
        machine.update_all(
            {"motion": STATE_ON},
            {"door": STATE_OFF},
        )
        # Then both OFF
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert result.wasp_active is True
        assert result.request_timer is None  # No timer with timeout=0


class TestWaspTimeout:
    """Tests for wasp timeout handling."""

    def test_on_wasp_timeout(self) -> None:
        """Test timeout expiration clears wasp."""
        machine = WaspStateMachine(wasp_timeout=300)
        machine.wasp = True
        machine._timeout_requested = True

        result = machine.on_wasp_timeout()
        assert result.wasp_active is False
        assert result.is_present is False
        assert result.cancel_timer is True
        assert machine.wasp is False

    def test_on_wasp_timeout_idempotent(self) -> None:
        """Test timeout can be called multiple times safely."""
        machine = WaspStateMachine(wasp_timeout=300)
        machine.wasp = True
        machine._timeout_requested = True

        result1 = machine.on_wasp_timeout()
        result2 = machine.on_wasp_timeout()

        assert result1.wasp_active is False
        assert result2.wasp_active is False

    def test_is_present_reflects_timeout_state(self) -> None:
        """Test is_present changes when timeout clears wasp."""
        machine = WaspStateMachine(wasp_timeout=300)
        machine.update_all({"motion": STATE_ON}, {"door": STATE_OFF})
        assert machine.is_present is True

        machine.on_wasp_timeout()
        assert machine.is_present is False


class TestDelayComplete:
    """Tests for box-close delay completion."""

    def test_on_delay_complete_motion_on(self) -> None:
        """Test delay completion with motion still detected."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.on_delay_complete(
            {"motion": STATE_ON},
            {"door": STATE_OFF},
        )
        assert result.wasp_active is True
        assert result.cancel_timer is True

    def test_on_delay_complete_motion_off(self) -> None:
        """Test delay completion with no motion."""
        machine = WaspStateMachine(wasp_timeout=300)
        machine.wasp = True  # Simulate prior state
        result = machine.on_delay_complete(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert result.wasp_active is True
        assert result.request_timer == 300.0

    def test_on_delay_complete_door_still_open(self) -> None:
        """Test delay completion with door still open."""
        machine = WaspStateMachine(wasp_timeout=300)
        machine.wasp = True
        result = machine.on_delay_complete(
            {"motion": STATE_OFF},
            {"door": STATE_ON},
        )
        assert result.box_open is True
        assert result.wasp_active is False
        assert result.cancel_timer is True


class TestTimerRequests:
    """Tests for timer request/cancel fields."""

    def test_request_timer_value(self) -> None:
        """Test request_timer field matches timeout."""
        machine = WaspStateMachine(wasp_timeout=600)
        machine.wasp = True
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert result.request_timer == 600.0

    def test_cancel_timer_on_motion(self) -> None:
        """Test cancel_timer is True when motion detected."""
        machine = WaspStateMachine(wasp_timeout=300)
        machine._timeout_requested = True
        result = machine.update_all(
            {"motion": STATE_ON},
            {"door": STATE_OFF},
        )
        assert result.cancel_timer is True

    def test_cancel_timer_on_box_open(self) -> None:
        """Test cancel_timer is True when box opens."""
        machine = WaspStateMachine(wasp_timeout=300)
        machine._timeout_requested = True
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_ON},
        )
        assert result.cancel_timer is True

    def test_no_cancel_timer_when_already_off(self) -> None:
        """Test cancel_timer is False when no timeout pending."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert result.cancel_timer is False


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_no_sensors_all_empty(self) -> None:
        """Test with completely empty sensor dicts."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_all({}, {})
        assert result.wasp_active is False
        assert result.box_open is False

    def test_all_sensors_off(self) -> None:
        """Test with all sensors explicitly OFF."""
        machine = WaspStateMachine(wasp_timeout=300)
        result = machine.update_all(
            {"m1": STATE_OFF, "m2": STATE_OFF, "m3": STATE_OFF},
            {"d1": STATE_OFF, "d2": STATE_OFF},
        )
        assert result.wasp_active is False
        assert result.box_open is False

    def test_aggregate_multiple_wasp_sensors(self) -> None:
        """Test aggregation of multiple wasp sensors (OR logic)."""
        machine = WaspStateMachine(wasp_timeout=300)
        # One of many sensors ON → ON
        result = machine.update_all(
            {"m1": STATE_OFF, "m2": STATE_ON, "m3": STATE_OFF},
            {"d1": STATE_OFF},
        )
        assert result.wasp_active is True

    def test_aggregate_multiple_box_sensors(self) -> None:
        """Test aggregation of multiple box sensors (OR logic)."""
        machine = WaspStateMachine(wasp_timeout=300)
        # One of many sensors ON → ON
        result = machine.update_all(
            {"m1": STATE_OFF},
            {"d1": STATE_OFF, "d2": STATE_ON, "d3": STATE_OFF},
        )
        assert result.box_open is True

    def test_state_transition_sequence(self) -> None:
        """Test realistic state transition sequence."""
        machine = WaspStateMachine(wasp_timeout=300)

        # Scenario: Person enters room (motion detected)
        result = machine.update_all(
            {"motion": STATE_ON},
            {"door": STATE_OFF},
        )
        assert result.wasp_active is True
        assert result.is_present is True

        # Person exits (door opens)
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_ON},
        )
        assert result.box_open is True
        assert result.wasp_active is False  # Cleared by box open

        # Door closes, motion sensor still off
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert result.box_open is False
        assert result.wasp_active is False  # Never turned on again
        assert result.request_timer is None  # No timeout

    def test_rapid_open_close_prevents_false_negative(self) -> None:
        """Test wasp persistence prevents false negatives on door bounce."""
        machine = WaspStateMachine(wasp_timeout=300)

        # Motion detected while door is open
        result = machine.update_all(
            {"motion": STATE_ON},
            {"door": STATE_ON},
        )
        assert result.wasp_active is True

        # Door bounces (closes momentarily)
        result = machine.update_all(
            {"motion": STATE_OFF},  # Motion ends during door bounce
            {"door": STATE_OFF},
        )
        # Wasp persists, waiting for timeout
        assert result.wasp_active is True
        assert result.request_timer == 300.0

        # Door opens again before timeout
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_ON},
        )
        # Wasp clears because door is now open
        assert result.wasp_active is False

    def test_timeout_value_conversion(self) -> None:
        """Test timeout values are converted to floats correctly."""
        machine = WaspStateMachine(wasp_timeout=600)
        machine.wasp = True
        result = machine.update_all(
            {"motion": STATE_OFF},
            {"door": STATE_OFF},
        )
        assert isinstance(result.request_timer, float)
        assert result.request_timer == 600.0
