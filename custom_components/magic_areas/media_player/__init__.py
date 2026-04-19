"""Platform file for Magic Area's media_player entities."""

from __future__ import annotations

import logging

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.platform_dispatch import (
    async_setup_platform_via_features,
)
from custom_components.magic_areas.components import MagicAreasConfigEntry
from custom_components.magic_areas.media_player.area_aware_media_player import (
    AreaAwareMediaPlayer,
    AreaMediaData,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area media player config entry."""
    await async_setup_platform_via_features(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain=MEDIA_PLAYER_DOMAIN,
        logger=_LOGGER,
    )


__all__ = ["AreaAwareMediaPlayer", "AreaMediaData"]
