"""Tests for deterministic HA dev simulation schedules."""

from __future__ import annotations

import pytest

from scripts.ha_dev_simulation_plan import (
    LIVING_ROOM_LUX_ENTITY,
    build_living_room_demo_plan,
    next_cycle_boundary,
    next_ramp_window,
)


def test_living_room_demo_plan_aligns_events_to_cycle_boundaries() -> None:
    """The default plan keeps state changes and ramp midpoint on cycle boundaries."""
    plan = build_living_room_demo_plan(
        started_at=100.0,
        cycle_seconds=30.0,
        ramp_seconds=10.0,
        state_period_cycles=2.0,
        final_cycles=2.0,
    )

    assert plan.setup_done_at == 102.0
    assert plan.occupancy_on_at == 120.0
    assert plan.observation_done_at == 180.0
    assert plan.lux_ramp.entity_id == LIVING_ROOM_LUX_ENTITY
    assert plan.lux_ramp.start_at == 205.0
    assert plan.lux_ramp.midpoint_at == 210.0
    assert plan.lux_ramp.end_at == 215.0
    assert plan.accent_on_at == 240.0
    assert plan.sleep_on_accent_off_at == 270.0
    assert plan.occupancy_off_at == 300.0
    assert plan.final_done_at == 360.0


def test_living_room_demo_plan_scales_state_period_cycles() -> None:
    """The observation and final windows scale from cycle count constants."""
    plan = build_living_room_demo_plan(
        started_at=100.0,
        cycle_seconds=30.0,
        ramp_seconds=10.0,
        state_period_cycles=3.0,
        final_cycles=1.5,
    )

    assert plan.observation_done_at == plan.occupancy_on_at + 90.0
    assert plan.final_done_at == plan.occupancy_off_at + 45.0


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (100.0, 120.0),
        (119.0, 120.0),
        (119.8, 150.0),
        (120.0, 150.0),
    ],
)
def test_next_cycle_boundary_uses_guard_window(now: float, expected: float) -> None:
    """A boundary too close to now is skipped so events are observable."""
    assert next_cycle_boundary(now, cycle_seconds=30.0) == expected


def test_next_ramp_window_aligns_midpoint_to_cycle_boundary() -> None:
    """Ramp windows center on a usable boundary even when called near one."""
    start_at, midpoint_at, end_at = next_ramp_window(
        119.8,
        cycle_seconds=30.0,
        ramp_seconds=10.0,
    )

    assert start_at == 145.0
    assert midpoint_at == 150.0
    assert end_at == 155.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cycle_seconds": 0.0},
        {"ramp_seconds": 0.0},
        {"state_period_cycles": -1.0},
        {"final_cycles": -1.0},
        {"setup_settle_seconds": -1.0},
    ],
)
def test_living_room_demo_plan_rejects_invalid_timing(kwargs: dict[str, float]) -> None:
    """Bad timing values fail before the live HA runner starts."""
    values = {
        "started_at": 100.0,
        "cycle_seconds": 30.0,
        "ramp_seconds": 10.0,
        "state_period_cycles": 2.0,
        "final_cycles": 2.0,
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        build_living_room_demo_plan(**values)
