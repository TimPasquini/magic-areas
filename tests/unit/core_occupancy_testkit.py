"""Shared test helpers for occupancy unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.const import STATE_ON

from custom_components.magic_areas.core.occupancy import (
    AreaOccupancyTracker,
    OccupancyUpdate,
)

UTC = UTC
NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def make_tracker(
    config: dict[str, object] | None = None, is_meta: bool = False
) -> AreaOccupancyTracker:
    """Create an occupancy tracker with default config."""
    return AreaOccupancyTracker(config=config or {}, is_meta=is_meta)


def occupy(
    tracker: AreaOccupancyTracker,
    now: datetime = NOW,
) -> OccupancyUpdate:
    """Drive tracker to occupied state with one active sensor."""
    return tracker.update(
        sensor_states={"sensor.motion": STATE_ON},
        secondary_states=[],
        keep_only=[],
        now=now,
    )
