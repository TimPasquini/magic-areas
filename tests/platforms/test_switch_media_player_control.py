"""Tests for the media player control switch."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.magic_areas.switch.media_player_control import (
    MediaPlayerControlSwitch,
)


async def test_media_player_control_ignores_other_area() -> None:
    """Test area mismatch skips service calls."""
    area = MagicMock()
    area.slug = "test-area"
    area.id = "area-one"

    switch = MediaPlayerControlSwitch(area)
    switch._attr_translation_key = None
    switch._attr_name = "Media player control"
    switch.hass = MagicMock()
    switch.hass.services.async_call = AsyncMock()
    switch._attr_is_on = True

    await switch.area_state_changed("area-two", ([], []))

    switch.hass.services.async_call.assert_not_called()
