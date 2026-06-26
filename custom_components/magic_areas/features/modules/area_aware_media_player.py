"""Area-aware media player feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.area_state import META_AREA_GLOBAL
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.features.config.readers import (
    AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS,
    area_aware_media_player_config,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.media_player import (
    AreaAwareMediaPlayer,
    AreaMediaData,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
    keys_and_validators=(
        (AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[0], cv.entity_ids),
        (AREA_AWARE_MEDIA_PLAYER_OPTION_KEYS[1], [str]),
    ),
)


class AreaAwareMediaPlayerFeatureModule(BaseFeatureModule):
    """Feature module for area-aware media player config and entity setup."""

    id = MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
    domains = {MEDIA_PLAYER_DOMAIN}
    feature_schema = AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA
    supports_meta_area = False
    supports_global_meta_area = False

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Enable for configured regular areas and global meta area host."""
        area_config = data.area_config
        if area_config.is_meta() and area_config.id == META_AREA_GLOBAL.lower():
            return True
        return self.id in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build global area-aware media player from snapshot/config-entry data."""
        del data
        if not (area_config.is_meta() and area_config.id == META_AREA_GLOBAL.lower()):
            return []

        hass = coordinator.hass
        entries = hass.config_entries.async_entries(DOMAIN)
        areas_with_media_players: dict[str, AreaMediaData] = {}

        for entry in entries:
            if entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
                continue

            runtime_data = entry.runtime_data
            snapshot = runtime_data.coordinator.data
            if snapshot is None:  # pragma: no cover
                _LOGGER.debug("Skipping area %s; no coordinator data", entry.entry_id)
                continue

            area_snapshot = snapshot.area_config
            entities_by_domain = snapshot.entities

            if area_snapshot.is_meta():
                continue

            if (
                MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER
                not in snapshot.enabled_features
            ):
                continue

            if MEDIA_PLAYER_DOMAIN not in entities_by_domain:
                continue

            config = area_aware_media_player_config(snapshot.feature_configs)
            notification_devices = config.notify_devices
            if not notification_devices:
                continue

            areas_with_media_players[area_snapshot.id] = {
                "entities_by_domain": entities_by_domain,
                "notification_devices": notification_devices,
                "notification_states": config.notify_states,
            }

        if not areas_with_media_players:
            _LOGGER.debug(
                "No areas with %s entities. Skipping creation of area-aware-media-player",
                MEDIA_PLAYER_DOMAIN,
            )
            return []

        _LOGGER.debug(
            "%s: Setting up area-aware media player with areas: %s",
            area_config.name,
            list(areas_with_media_players),
        )
        return [
            AreaAwareMediaPlayer(area_config, coordinator, areas_with_media_players)
        ]


__all__ = ["AreaAwareMediaPlayerFeatureModule"]
