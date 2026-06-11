"""Timing and callback utilities for integration tests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow

from custom_components.magic_areas.area_state import AreaStates


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
