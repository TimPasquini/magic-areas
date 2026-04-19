"""Timing and callback utilities for integration tests."""

from __future__ import annotations

import functools
from asyncio import get_running_loop
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow

from custom_components.magic_areas.area_state import AreaStates


class VirtualClock:
    """Provide a virtual clock for an asyncio event loop."""

    def __init__(self) -> None:
        """Initialize the clock with a simple time."""
        self.vtime = 0.0

    def virtual_time(self) -> float:
        """Return the current virtual time."""
        return self.vtime

    def _virtual_select(
        self,
        orig_select: Callable[[float | None], object],
        timeout: float | None,
    ) -> object:
        """Override select() to advance virtual time without blocking."""
        if timeout is not None:
            self.vtime += timeout
        return orig_select(0)

    @contextmanager
    def patch_loop(self) -> Iterator[None]:
        """Override methods of the current event loop for virtual time."""
        loop = get_running_loop()
        with (
            patch.object(
                loop._selector,  # type: ignore[attr-defined]  # pylint: disable=protected-access
                "select",
                new=functools.partial(
                    self._virtual_select,
                    loop._selector.select,  # type: ignore[attr-defined]  # pylint: disable=protected-access
                ),
            ),
            patch.object(
                loop,
                "time",
                new=self.virtual_time,
            ),
            patch.object(
                loop,
                "_clock_resolution",
                new=0.1,
            ),
        ):
            yield


def immediate_call_factory(
    hass: HomeAssistant, callback_key: str = "callback"
) -> Callable[
    [HomeAssistant, float, Callable[[datetime], Awaitable[object] | None]],
    Callable[[], None],
]:
    """Create a callback factory for testing delayed callbacks without delays."""

    def immediate_call(
        hass_arg: HomeAssistant,
        delay_arg: float,
        callback_arg: Callable[[datetime], Awaitable[object] | None],
    ) -> Callable[[], None]:
        canceled = False

        def cancel() -> None:
            nonlocal canceled
            canceled = True

        async def run_callback() -> None:
            if not canceled:
                result = callback_arg(utcnow())
                if result is not None:
                    await result

        hass.loop.create_task(run_callback())
        return cancel

    return immediate_call


def create_area_state_change_event(
    new_states: list[AreaStates] | None = None,
    lost_states: list[AreaStates] | None = None,
    current_states: list[AreaStates] | None = None,
) -> tuple[list[AreaStates], list[AreaStates], list[AreaStates]]:
    """Create an AREA_STATE_CHANGED event payload tuple."""
    return (
        new_states if new_states is not None else [],
        lost_states if lost_states is not None else [],
        current_states if current_states is not None else [],
    )

