"""Tests for the media player control switch."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.magic_areas.switch.media_player_control import (
    MediaPlayerControlSwitch,
)


async def test_media_player_control_ignores_other_area() -> None:
    """Test area mismatch skips service calls."""
    area_config = MagicMock()
    area_config.slug = "test-area"
    area_config.id = "area-one"
    area_config.name = "Test Area"
    area_config.icon = None
    area_config.is_meta.return_value = False

    coordinator = MagicMock()
    coordinator.last_update_success = True

    switch = MediaPlayerControlSwitch(area_config, coordinator)
    switch._attr_translation_key = None
    switch._attr_name = "Media player control"
    switch.hass = MagicMock()
    switch.hass.services.async_call = AsyncMock()
    switch._attr_is_on = True

    await switch.area_state_changed("area-two", ([], []))

    switch.hass.services.async_call.assert_not_called()
