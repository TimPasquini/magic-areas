"""Platform file for Magic Area's media_player entities."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.group.media_player import MediaPlayerGroup
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.area_constants import (
    META_AREA_GLOBAL,
)
from custom_components.magic_areas.base.entities import MagicGroupEntity
from custom_components.magic_areas.config_keys import (
    CONF_NOTIFICATION_DEVICES,
    EMPTY_STRING,
)
from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoMediaPlayerGroups,
)
from custom_components.magic_areas.features import (
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_MEDIA_PLAYER_GROUPS,
)
from custom_components.magic_areas.media_player.area_aware_media_player import (
    AreaAwareMediaPlayer,
)
from custom_components.magic_areas.helpers.cleanup import cleanup_removed_entries

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area media player config entry."""

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        _LOGGER.debug("Skipping media player setup; coordinator data unavailable")
        return
    area_config = data.area_config
    coordinator = runtime_data.coordinator

    entities_to_add: list[Entity] = []

    # Media Player Groups
    if CONF_FEATURE_MEDIA_PLAYER_GROUPS in data.enabled_features:
        _LOGGER.debug("%s: Setting up media player groups.", area_config.name)
        entities_to_add.extend(setup_media_player_group(area_config, coordinator, data.entities))

    # Check if we are the Global Meta Area
    if area_config.is_meta() and area_config.id == META_AREA_GLOBAL.lower():
        # Try to setup AAMP
        _LOGGER.debug("%s: Setting up Area-Aware media player", area_config.name)
        entities_to_add.extend(
            await setup_area_aware_media_player(area_config, coordinator)
        )

    if entities_to_add:
        async_add_entities(entities_to_add)

    if MEDIA_PLAYER_DOMAIN in data.magic_entities:
        cleanup_removed_entries(
            hass, entities_to_add, data.magic_entities[MEDIA_PLAYER_DOMAIN]
        )


def setup_media_player_group(
    area_config: "AreaConfig",
    coordinator: "MagicAreasCoordinator",
    entities_by_domain: dict[str, list[dict[str, str]]],
) -> list[Entity]:
    """Create the media player groups."""
    # Check if there are any media player devices
    if MEDIA_PLAYER_DOMAIN not in entities_by_domain:
        _LOGGER.debug("%s: No %s entities.", area_config.name, MEDIA_PLAYER_DOMAIN)
        return []

    media_player_entities = [
        e["entity_id"] for e in entities_by_domain[MEDIA_PLAYER_DOMAIN]
    ]

    return [AreaMediaPlayerGroup(area_config, coordinator, media_player_entities)]


async def setup_area_aware_media_player(
    area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
) -> list[Entity]:
    """Create Area-aware media player."""
    hass = coordinator.hass
    entries = hass.config_entries.async_entries(DOMAIN)

    # Check if we have areas with MEDIA_PLAYER_DOMAIN entities
    areas_with_media_players = []

    for entry in entries:
        if entry.domain != DOMAIN:
            continue

        if not hasattr(entry, "runtime_data"):
            continue

        runtime_data = entry.runtime_data
        if runtime_data.coordinator.data is None:
            await runtime_data.coordinator.async_refresh()
        data = runtime_data.coordinator.data
        if data is None:
            _LOGGER.debug("Skipping area %s; no coordinator data", entry.entry_id)
            continue
        current_area = data.area
        entities_by_domain = data.entities

        # Skip meta areas
        if current_area.is_meta():
            _LOGGER.debug("%s: Is meta-area, skipping.", current_area.name)
            continue

        # Skip areas with feature not enabled
        if CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER not in data.enabled_features:
            _LOGGER.debug(
                "%s: Does not have Area-aware media player feature enabled, skipping.",
                current_area.name,
            )
            continue

        # Skip areas without media player entities
        if MEDIA_PLAYER_DOMAIN not in entities_by_domain:
            _LOGGER.debug(
                "%s: Has no media player entities, skipping.", current_area.name
            )
            continue

        # Skip areas without notification devices set
        notification_devices = data.feature_configs.get(
            CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER, {}
        ).get(CONF_NOTIFICATION_DEVICES)

        if not notification_devices:
            _LOGGER.debug(
                "%s: Has no notification devices, skipping.", current_area.name
            )
            continue

        # If all passes, we add this valid area to the list
        areas_with_media_players.append(current_area)

    if not areas_with_media_players:
        _LOGGER.debug(
            "No areas with %s entities. Skipping creation of area-aware-media-player",
            MEDIA_PLAYER_DOMAIN,
        )
        return []

    area_names = [i.name for i in areas_with_media_players]

    _LOGGER.debug(
        "%s: Setting up area-aware media player with areas: %s",
        area_config.name,
        area_names,
    )

    return [AreaAwareMediaPlayer(area_config, coordinator, areas_with_media_players)]


class AreaMediaPlayerGroup(MagicGroupEntity, MediaPlayerGroup):
    """Media player group."""

    feature_info = MagicAreasFeatureInfoMediaPlayerGroups()

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator", entities: list[str]
    ) -> None:
        """Initialize media player group."""
        MagicGroupEntity.__init__(
            self,
            area_config=area_config,
            coordinator=coordinator,
            domain=MEDIA_PLAYER_DOMAIN,
            member_entity_ids=entities,
        )
        MediaPlayerGroup.__init__(
            self,
            name=EMPTY_STRING,
            unique_id=self._attr_unique_id,
            entities=self.member_entity_ids,
        )
