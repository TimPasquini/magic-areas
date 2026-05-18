"""Deterministic schedules for Home Assistant dev-house simulations."""

from __future__ import annotations

import math
from dataclasses import dataclass

BOUNDARY_GUARD_SECONDS = 0.25
DEFAULT_SETUP_SETTLE_SECONDS = 2.0
LIVING_ROOM_LUX_ENTITY = "input_number.living_room_lux"


@dataclass(frozen=True, slots=True)
class RampPlan:
    """A numeric ramp whose midpoint is aligned to a simulation cycle boundary."""

    name: str
    entity_id: str
    start_at: float
    midpoint_at: float
    end_at: float
    start_value: float
    end_value: float


@dataclass(frozen=True, slots=True)
class LivingRoomDemoPlan:
    """Absolute wall-clock schedule for the living-room demo scenario."""

    started_at: float
    setup_done_at: float
    occupancy_on_at: float
    observation_done_at: float
    lux_ramp: RampPlan
    accent_on_at: float
    sleep_on_accent_off_at: float
    occupancy_off_at: float
    final_done_at: float
    cycle_seconds: float
    ramp_seconds: float
    state_period_cycles: float
    final_cycles: float


def next_cycle_boundary(
    now: float,
    *,
    cycle_seconds: float,
    guard_seconds: float = BOUNDARY_GUARD_SECONDS,
) -> float:
    """Return the next usable cycle boundary at or after ``now``."""
    _validate_positive("cycle_seconds", cycle_seconds)
    if guard_seconds < 0:
        raise ValueError("guard_seconds must be >= 0")

    boundary = math.ceil(now / cycle_seconds) * cycle_seconds
    if boundary <= now + guard_seconds:
        boundary += cycle_seconds
    return boundary


def next_ramp_window(
    now: float,
    *,
    cycle_seconds: float,
    ramp_seconds: float,
    guard_seconds: float = BOUNDARY_GUARD_SECONDS,
) -> tuple[float, float, float]:
    """Return a ramp start/midpoint/end whose midpoint is a cycle boundary."""
    _validate_positive("ramp_seconds", ramp_seconds)
    midpoint = next_cycle_boundary(
        now + (ramp_seconds / 2),
        cycle_seconds=cycle_seconds,
        guard_seconds=guard_seconds,
    )
    start_at = midpoint - (ramp_seconds / 2)
    end_at = midpoint + (ramp_seconds / 2)
    if start_at <= now + guard_seconds:
        midpoint += cycle_seconds
        start_at = midpoint - (ramp_seconds / 2)
        end_at = midpoint + (ramp_seconds / 2)
    return start_at, midpoint, end_at


def build_living_room_demo_plan(
    *,
    started_at: float,
    cycle_seconds: float,
    ramp_seconds: float,
    state_period_cycles: float,
    final_cycles: float,
    setup_settle_seconds: float = DEFAULT_SETUP_SETTLE_SECONDS,
    guard_seconds: float = BOUNDARY_GUARD_SECONDS,
) -> LivingRoomDemoPlan:
    """Build the living-room demo schedule without touching Home Assistant."""
    _validate_positive("cycle_seconds", cycle_seconds)
    _validate_positive("ramp_seconds", ramp_seconds)
    _validate_non_negative("state_period_cycles", state_period_cycles)
    _validate_non_negative("final_cycles", final_cycles)
    _validate_non_negative("setup_settle_seconds", setup_settle_seconds)

    setup_done_at = started_at + setup_settle_seconds
    occupancy_on_at = next_cycle_boundary(
        setup_done_at,
        cycle_seconds=cycle_seconds,
        guard_seconds=guard_seconds,
    )
    observation_done_at = occupancy_on_at + (cycle_seconds * state_period_cycles)
    ramp_start_at, ramp_midpoint_at, ramp_end_at = next_ramp_window(
        observation_done_at,
        cycle_seconds=cycle_seconds,
        ramp_seconds=ramp_seconds,
        guard_seconds=guard_seconds,
    )
    accent_on_at = next_cycle_boundary(
        ramp_end_at,
        cycle_seconds=cycle_seconds,
        guard_seconds=guard_seconds,
    )
    sleep_on_accent_off_at = next_cycle_boundary(
        accent_on_at,
        cycle_seconds=cycle_seconds,
        guard_seconds=guard_seconds,
    )
    occupancy_off_at = next_cycle_boundary(
        sleep_on_accent_off_at,
        cycle_seconds=cycle_seconds,
        guard_seconds=guard_seconds,
    )
    final_done_at = occupancy_off_at + (cycle_seconds * final_cycles)

    return LivingRoomDemoPlan(
        started_at=started_at,
        setup_done_at=setup_done_at,
        occupancy_on_at=occupancy_on_at,
        observation_done_at=observation_done_at,
        lux_ramp=RampPlan(
            name="living-room lux ramp",
            entity_id=LIVING_ROOM_LUX_ENTITY,
            start_at=ramp_start_at,
            midpoint_at=ramp_midpoint_at,
            end_at=ramp_end_at,
            start_value=350.0,
            end_value=1300.0,
        ),
        accent_on_at=accent_on_at,
        sleep_on_accent_off_at=sleep_on_accent_off_at,
        occupancy_off_at=occupancy_off_at,
        final_done_at=final_done_at,
        cycle_seconds=cycle_seconds,
        ramp_seconds=ramp_seconds,
        state_period_cycles=state_period_cycles,
        final_cycles=final_cycles,
    )


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be > 0")


def _validate_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
