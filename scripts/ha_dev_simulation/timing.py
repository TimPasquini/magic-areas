"""Real-time timing helpers for live fake-house simulation."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SimulationTiming:
    """Named real-time waits for live fake-house scenarios."""

    cycle_seconds: float
    state_period_cycles: float
    setup_settle_seconds: float
    checkpoint_settle_seconds: float

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> SimulationTiming:
        """Build scenario timing from CLI arguments."""
        return cls(
            cycle_seconds=float(args.cycle_seconds),
            state_period_cycles=float(args.state_period_cycles),
            setup_settle_seconds=float(args.setup_settle_seconds),
            checkpoint_settle_seconds=float(args.checkpoint_settle_seconds),
        )

    @property
    def seeded_minute_seconds(self) -> float:
        """Return real seconds used for seeded one-minute Magic Areas timing."""
        return self.cycle_seconds * self.state_period_cycles

    def configured_minutes_seconds(self, minutes: float) -> float:
        """Return wait seconds for minute-based seeded Magic Areas options."""
        return self.seeded_minute_seconds * minutes

    def configured_minutes_timeout(self, minutes: float) -> float:
        """Return a polling timeout for a minute-based behavior."""
        return self.configured_minutes_seconds(minutes) + self.checkpoint_settle_seconds

    def configured_seconds_timeout(self, seconds: float) -> float:
        """Return a polling timeout for a second-based runtime behavior."""
        return seconds + self.checkpoint_settle_seconds

    def configured_minutes_event_timeout(
        self,
        minutes: float,
        *,
        event_margin_seconds: float,
    ) -> float:
        """Return timeout for an event expected after a minute-based behavior."""
        return self.configured_minutes_timeout(minutes) + event_margin_seconds

    @property
    def runtime_poll_seconds(self) -> float:
        """Return a short poll interval for narrow real-time hold windows."""
        return min(0.5, max(0.1, self.checkpoint_settle_seconds / 10))

    async def settle_setup(self) -> None:
        """Wait for reset/control setup propagation before scenario events."""
        await asyncio.sleep(self.setup_settle_seconds)

    async def settle_checkpoint(self) -> None:
        """Wait for immediate HA propagation before evaluating a checkpoint."""
        await asyncio.sleep(self.checkpoint_settle_seconds)

    async def settle_immediate_guard(self) -> None:
        """Wait briefly to prove automation did not immediately reverse an action."""
        await asyncio.sleep(min(1.0, self.checkpoint_settle_seconds / 2))

    async def wait_configured_minutes(
        self,
        minutes: float,
        *,
        include_checkpoint_settle: bool = True,
    ) -> None:
        """Wait for a minute-based Magic Areas timer in real simulation time."""
        seconds = self.configured_minutes_seconds(minutes)
        if include_checkpoint_settle:
            seconds += self.checkpoint_settle_seconds
        await asyncio.sleep(seconds)

    async def wait_configured_seconds(
        self,
        seconds: float,
        *,
        include_checkpoint_settle: bool = True,
    ) -> None:
        """Wait for a second-based runtime hold in real simulation time."""
        if include_checkpoint_settle:
            seconds += self.checkpoint_settle_seconds
        await asyncio.sleep(seconds)
