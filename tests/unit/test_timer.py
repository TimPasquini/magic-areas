"""Tests for the reusable timer helper."""

from typing import Any, cast
from collections.abc import Callable
from datetime import datetime, UTC
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.helpers.timer import ReusableTimer


async def test_reusable_timer_skips_stale_callback(hass: HomeAssistant) -> None:
    """Test stale callbacks are skipped after restart."""
    calls: list[datetime] = []
    scheduled: dict[str, object] = {}

    async def _callback(now: datetime) -> None:
        calls.append(now)

    def _fake_async_call_later(hass_obj: Any, delay: Any, action: Any) -> Callable[[], None]:
        scheduled["action"] = action
        return lambda: None

    timer = ReusableTimer(hass, 1, _callback)

    with patch(
        "custom_components.magic_areas.helpers.timer.async_call_later",
        side_effect=_fake_async_call_later,
    ):
        timer.start()
        first_action = cast(Callable[[datetime], Any], scheduled["action"])
        timer.start()
        await first_action(datetime.now(UTC))

    assert calls == []
