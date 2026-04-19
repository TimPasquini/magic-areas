"""Tests for the reusable timer helper."""

from collections.abc import Awaitable, Callable
from datetime import datetime, UTC
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.helpers import ReusableTimer


async def test_reusable_timer_skips_stale_callback(hass: HomeAssistant) -> None:
    """Test stale callbacks are skipped after restart."""
    calls: list[datetime] = []
    scheduled: dict[str, Callable[[datetime], Awaitable[None]]] = {}

    async def _callback(now: datetime) -> None:
        calls.append(now)

    def _fake_async_call_later(
        hass_obj: HomeAssistant,
        delay: float,
        action: Callable[[datetime], Awaitable[None]],
    ) -> Callable[[], None]:
        del hass_obj, delay
        scheduled["action"] = action
        return lambda: None

    timer = ReusableTimer(hass, 1, _callback)

    with patch(
        "custom_components.magic_areas.helpers.async_call_later",
        side_effect=_fake_async_call_later,
    ):
        timer.start()
        first_action = scheduled["action"]
        timer.start()
        await first_action(datetime.now(UTC))

    assert calls == []
