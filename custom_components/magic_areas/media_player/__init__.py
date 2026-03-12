"""Platform file for Magic Area's media_player entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.area_state import META_AREA_GLOBAL
from custom_components.magic_areas.features.dispatch import collect_feature_entities
from custom_components.magic_areas.config_keys.features import (
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
)
from custom_components.magic_areas.core.feature_defaults import (
    DEFAULT_NOTIFY_STATES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.media_player.area_aware_media_player import (
    AreaAwareMediaPlayer,
)
from custom_components.magic_areas.helpers.cleanup import cleanup_removed_entries

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.models import MagicAreasConfigEntry
    from custom_components.magic_areas.features.registry import FeatureRegistry

_LOGGER = logging.getLogger(__name__)
FEATURE_REGISTRY: FeatureRegistry | None = None


def _get_feature_registry() -> FeatureRegistry:
    if FEATURE_REGISTRY is not None:
        return FEATURE_REGISTRY
    from custom_components.magic_areas.features.registry import FEATURE_REGISTRY as registry

    return registry


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
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

    registry = _get_feature_registry()
    entities_to_add = collect_feature_entities(
        domain=MEDIA_PLAYER_DOMAIN,
        registry=registry,
        data=data,
        area_config=area_config,
        coordinator=coordinator,
        logger=_LOGGER,
    )

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


async def setup_area_aware_media_player(
    area_config: AreaConfig, coordinator: MagicAreasCoordinator
) -> list[Entity]:
    """Create Area-aware media player."""
    hass = coordinator.hass
    entries = hass.config_entries.async_entries(DOMAIN)

    # Check if we have areas with MEDIA_PLAYER_DOMAIN entities
    # Collect area data (config + snapshot info) instead of MagicArea objects
    areas_with_media_players: dict[str, dict] = {}

    for entry in entries:
        if entry.domain != DOMAIN:
            continue

        if not hasattr(entry, "runtime_data"):  # pragma: no cover
            continue

        runtime_data = entry.runtime_data
        if runtime_data.coordinator.data is None:
            await runtime_data.coordinator.async_refresh()
        data = runtime_data.coordinator.data
        if data is None:  # pragma: no cover
            _LOGGER.debug("Skipping area %s; no coordinator data", entry.entry_id)
            continue

        area_config_data = data.area_config
        entities_by_domain = data.entities

        # Skip meta areas
        if area_config_data.is_meta():
            _LOGGER.debug("%s: Is meta-area, skipping.", area_config_data.name)
            continue

        # Skip areas with feature not enabled
        if MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER not in data.enabled_features:
            _LOGGER.debug(
                "%s: Does not have Area-aware media player feature enabled, skipping.",
                area_config_data.name,
            )
            continue

        # Skip areas without media player entities
        if MEDIA_PLAYER_DOMAIN not in entities_by_domain:
            _LOGGER.debug(
                "%s: Has no media player entities, skipping.", area_config_data.name
            )
            continue

        # Get feature config for this area
        aamp_config = data.feature_configs.get(MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER, {})
        notification_devices = aamp_config.get(CONF_NOTIFICATION_DEVICES)

        if not notification_devices:
            _LOGGER.debug(
                "%s: Has no notification devices, skipping.", area_config_data.name
            )
            continue

        # Get notification states from config, or use default
        notification_states = aamp_config.get(CONF_NOTIFY_STATES, DEFAULT_NOTIFY_STATES)

        # If all passes, store this area's data
        areas_with_media_players[area_config_data.id] = {
            "area_config": area_config_data,
            "entities_by_domain": entities_by_domain,
            "notification_devices": notification_devices,
            "notification_states": notification_states,
        }

    if not areas_with_media_players:
        _LOGGER.debug(
            "No areas with %s entities. Skipping creation of area-aware-media-player",
            MEDIA_PLAYER_DOMAIN,
        )
        return []

    area_names = [data["area_config"].name for data in areas_with_media_players.values()]

    _LOGGER.debug(
        "%s: Setting up area-aware media player with areas: %s",
        area_config.name,
        area_names,
    )

    return [AreaAwareMediaPlayer(area_config, coordinator, areas_with_media_players)]


__all__ = ["setup_area_aware_media_player"]
