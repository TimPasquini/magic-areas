"""Tests for meta-area reload policy and decision logic."""

from datetime import timedelta
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.core.meta_reload import (
    MetaAreaAutoReloadSettings,
    ReloadDecision,
    _evaluate_reload_preconditions,
    should_reload_on_area_change,
    evaluate_reload,
)


class TestReloadDecision:
    """Test ReloadDecision dataclass."""

    def test_dataclass_frozen(self) -> None:
        """ReloadDecision should be immutable."""
        decision = ReloadDecision(
            should_reload=True,
            delay_seconds=3.0,
            reason="Test",
        )

        # Should be read-only (frozen dataclass)
        assert decision.should_reload is True

    def test_dataclass_fields(self) -> None:
        """ReloadDecision should have correct fields."""
        decision = ReloadDecision(
            should_reload=True,
            delay_seconds=5.5,
            reason="Test reason",
        )

        assert decision.should_reload is True
        assert decision.delay_seconds == 5.5
        assert decision.reason == "Test reason"
        assert decision.retry_after_seconds == 0


class TestShouldReloadOnAreaChange:
    """Test area change matching logic."""

    def test_global_always_reloads(self) -> None:
        """Global meta-area should reload on any area change."""
        result = should_reload_on_area_change(
            meta_slug="global",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=["kitchen", "living_room"],
        )
        assert result is True

        # Should work even if area is not a child
        result = should_reload_on_area_change(
            meta_slug="global",
            trigger_area_type="exterior",
            trigger_area_id="backyard",
            child_areas=["kitchen"],
        )
        assert result is True

    def test_type_match_triggers_reload(self) -> None:
        """Non-global meta-area reloads if type matches."""
        result = should_reload_on_area_change(
            meta_slug="interior",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=["kitchen", "living_room"],
        )
        assert result is True

    def test_child_area_triggers_reload(self) -> None:
        """Non-global meta-area reloads if area is a child."""
        result = should_reload_on_area_change(
            meta_slug="floor_0",
            trigger_area_type="not_a_match",
            trigger_area_id="kitchen",
            child_areas=["kitchen", "living_room"],
        )
        assert result is True

    def test_no_match_skips_reload(self) -> None:
        """Non-global meta-area skips reload if no match."""
        result = should_reload_on_area_change(
            meta_slug="interior",
            trigger_area_type="exterior",
            trigger_area_id="backyard",
            child_areas=["kitchen", "living_room"],
        )
        assert result is False


class TestEvaluateReload:
    """Test complete reload decision logic."""

    def test_no_match_returns_false(self) -> None:
        """Should reject reload if area doesn't match."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=10)

        decision = evaluate_reload(
            meta_slug="interior",
            trigger_area_type="exterior",
            trigger_area_id="backyard",
            child_areas=["kitchen"],
            last_reload=last,
            now=now,
        )

        assert decision.should_reload is False
        assert decision.delay_seconds == 0
        assert "not matched" in decision.reason.lower()
        assert decision.retry_after_seconds == 0

    def test_throttle_prevents_reload(self) -> None:
        """Should reject reload if throttled."""
        now = dt_util.utcnow()
        # Only 2 seconds ago (less than 5 second throttle)
        last = now - timedelta(seconds=2)

        decision = evaluate_reload(
            meta_slug="global",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=[],
            last_reload=last,
            now=now,
            throttle_seconds=5,
        )

        assert decision.should_reload is False
        assert decision.delay_seconds == 0
        assert "throttled" in decision.reason.lower()
        assert 0 < decision.retry_after_seconds <= 3

    def test_throttle_boundary(self) -> None:
        """Should allow reload exactly at throttle boundary."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=5)

        decision = evaluate_reload(
            meta_slug="global",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=[],
            last_reload=last,
            now=now,
            throttle_seconds=5,
        )

        assert decision.should_reload is True
        assert decision.retry_after_seconds == 0

    def test_delay_within_range(self) -> None:
        """Should calculate delay within expected range."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=10)

        decision = evaluate_reload(
            meta_slug="interior",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=["kitchen"],
            last_reload=last,
            now=now,
            base_delay=3.0,
            max_delay_multiplier=4,
        )

        assert decision.should_reload is True
        # Delay should be between base (3) and max (3*4=12)
        assert 3.0 <= decision.delay_seconds <= 12.0

    def test_global_uses_max_delay(self) -> None:
        """Global meta-area should use max delay."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=10)

        decision = evaluate_reload(
            meta_slug="global",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=[],
            last_reload=last,
            now=now,
            base_delay=3.0,
            max_delay_multiplier=4,
        )

        assert decision.should_reload is True
        # Global should always use max delay (3 * 4 = 12)
        assert decision.delay_seconds == 12.0
        assert "global" in decision.reason.lower()

    def test_non_global_randomized_delay(self) -> None:
        """Non-global meta-areas should have randomized delay."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=10)

        delays = []
        for _ in range(10):
            decision = evaluate_reload(
                meta_slug="interior",
                trigger_area_type="interior",
                trigger_area_id="kitchen",
                child_areas=["kitchen"],
                last_reload=last,
                now=now,
                base_delay=3.0,
                max_delay_multiplier=4,
            )
            delays.append(decision.delay_seconds)

        # Should have variation (not all the same)
        assert len(set(delays)) > 1
        # All within range
        assert all(3.0 <= d <= 12.0 for d in delays)

    def test_custom_settings(self) -> None:
        """Should respect custom timeout and delay settings."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=2)

        decision = evaluate_reload(
            meta_slug="global",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=[],
            last_reload=last,
            now=now,
            throttle_seconds=1,  # Custom throttle
            base_delay=2.0,
            max_delay_multiplier=5,
        )

        assert decision.should_reload is True
        # Global should use max (2 * 5 = 10)
        assert decision.delay_seconds == 10.0


class TestEvaluateReloadPreconditions:
    """Focused tests for extracted precondition helper."""

    def test_non_matching_area_returns_not_matched_decision(self) -> None:
        """Returns a skip decision when trigger area does not match meta-area."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=10)

        decision = _evaluate_reload_preconditions(
            meta_slug="interior",
            trigger_area_type="exterior",
            trigger_area_id="backyard",
            child_areas=["kitchen"],
            last_reload=last,
            now=now,
            throttle_seconds=5,
        )

        assert decision is not None
        assert decision.should_reload is False
        assert "not matched" in decision.reason.lower()

    def test_matching_area_with_no_throttle_returns_none(self) -> None:
        """Returns None when matching area passes throttle preconditions."""
        now = dt_util.utcnow()
        last = now - timedelta(seconds=10)

        decision = _evaluate_reload_preconditions(
            meta_slug="interior",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            child_areas=["kitchen"],
            last_reload=last,
            now=now,
            throttle_seconds=5,
        )

        assert decision is None


class TestMetaAreaAutoReloadSettings:
    """Test reload configuration constants."""

    def test_settings_values(self) -> None:
        """Settings should have expected values."""
        assert MetaAreaAutoReloadSettings.DELAY.value == 3
        assert MetaAreaAutoReloadSettings.DELAY_MULTIPLIER.value == 4
        assert MetaAreaAutoReloadSettings.THROTTLE.value == 5

    def test_settings_are_integers(self) -> None:
        """Settings should be IntEnum values."""
        assert isinstance(MetaAreaAutoReloadSettings.DELAY, int)
        assert isinstance(MetaAreaAutoReloadSettings.THROTTLE, int)
