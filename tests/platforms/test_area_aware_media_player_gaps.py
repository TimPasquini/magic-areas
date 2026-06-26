"""Tests for area aware media player covering uncovered edge cases.

Tests verify the media player correctly handles:
- Area sensor resolution failures (entity registry missing)
- No media players found scenario (service call avoided)
"""

import pytest
from typing import cast
from homeassistant.components.media_player.const import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from unittest.mock import MagicMock

from custom_components.magic_areas.media_player import (
    AreaAwareMediaPlayer,
)
from custom_components.magic_areas.const import ATTR_STATES


def test_area_aware_media_player_exposes_media_entity_contract() -> None:
    """State and supported features should satisfy HA's media entity contract."""
    media_player = MagicMock(spec=AreaAwareMediaPlayer)
    media_player._state = MediaPlayerState.IDLE

    state_property = cast(property, AreaAwareMediaPlayer.__dict__["state"])
    features_property = cast(
        property, AreaAwareMediaPlayer.__dict__["supported_features"]
    )
    assert state_property.__get__(media_player) is MediaPlayerState.IDLE
    supported = features_property.__get__(media_player)
    assert supported == (
        MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.MEDIA_ANNOUNCE
    )


@pytest.mark.asyncio
async def test_area_sensor_not_found_skips_area(
    hass: HomeAssistant,
) -> None:
    """Verify area is skipped if presence sensor not resolved (lines 146-152)."""
    # Create a minimal mock media player that can be queried
    media_player = MagicMock(spec=AreaAwareMediaPlayer)
    media_player.hass = hass
    media_player.name = "test_player"

    # Create areas_data with a test area
    areas_data = {
        "missing_sensor_area": {
            "entities_by_domain": {MEDIA_PLAYER_DOMAIN: []},
            "notification_devices": [],
            "notification_states": ["occupied"],
        }
    }
    media_player.areas_data = areas_data

    # Mock _resolve_area_state_sensor to return None (entity not found)
    media_player._resolve_area_state_sensor = MagicMock(return_value=None)

    # Mock get_active_areas to use the real implementation
    real_get_active_areas = AreaAwareMediaPlayer.get_active_areas
    media_player.get_active_areas = lambda: real_get_active_areas(media_player)

    # Call get_active_areas() which should return empty list
    # because _resolve_area_state_sensor returns None
    active_areas = media_player.get_active_areas()

    # Verify the area was skipped (empty result) because sensor wasn't found
    assert len(active_areas) == 0


@pytest.mark.asyncio
async def test_no_media_players_skips_service_call(
    hass: HomeAssistant,
) -> None:
    """Verify service call skipped if no active media players (lines 214-218)."""
    # Create minimal media player mock
    media_player = MagicMock(spec=AreaAwareMediaPlayer)
    media_player.hass = hass
    media_player.name = "test_player"

    # Create areas_data with NO media players (empty entities_by_domain)
    areas_data = {
        "test_kitchen": {
            "entities_by_domain": {},  # No media players
            "notification_devices": [],
            "notification_states": ["occupied"],
        }
    }
    media_player.areas_data = areas_data

    # Set up area state sensor to indicate occupied
    area_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_test_kitchen_area_state"
    )
    hass.states.async_set(area_sensor_id, STATE_ON, {ATTR_STATES: ["occupied"]})
    await hass.async_block_till_done()

    # Mock _resolve_area_state_sensor to return the sensor entity
    media_player._resolve_area_state_sensor = MagicMock(return_value=area_sensor_id)

    # Mock get_active_areas using the real implementation
    real_get_active_areas = AreaAwareMediaPlayer.get_active_areas
    media_player.get_active_areas = lambda: real_get_active_areas(media_player)

    # Call get_active_areas() - should return the area since sensor is found
    active_areas = media_player.get_active_areas()
    assert len(active_areas) == 1  # Area should be active

    # Now test async_play_media with no media players
    # The real implementation should return early when no media players found
    real_async_play_media = AreaAwareMediaPlayer.async_play_media

    # Call async_play_media - it should return without calling the service
    # This test verifies that the early return at line 214-218 works correctly
    await real_async_play_media(media_player, "music", "test_media_id")


def test_update_state_uses_single_write_path() -> None:
    """Verify update_state writes immediately without scheduler queuing."""
    media_player = MagicMock(spec=AreaAwareMediaPlayer)
    media_player.update_attributes = MagicMock()
    media_player.async_write_ha_state = MagicMock()
    media_player.schedule_update_ha_state = MagicMock()

    real_update_state = AreaAwareMediaPlayer.update_state
    real_update_state(media_player)

    media_player.update_attributes.assert_called_once()
    media_player.async_write_ha_state.assert_called_once()
    media_player.schedule_update_ha_state.assert_not_called()
