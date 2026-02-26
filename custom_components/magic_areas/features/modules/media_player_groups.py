"""Media player groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)
from custom_components.magic_areas.media_player_group_entities import AreaMediaPlayerGroup
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


class MediaPlayerGroupsFeatureModule(BaseFeatureModule):
    """Feature module for media player groups."""

    id = MagicAreasFeatures.MEDIA_PLAYER_GROUPS
    domains = {MEDIA_PLAYER_DOMAIN, SWITCH_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return None

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.MEDIA_PLAYER_GROUPS in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the media player groups feature."""
        entities: list[Entity] = []

        if MEDIA_PLAYER_DOMAIN not in data.entities:
            _LOGGER.debug(
                "%s: No %s entities.",
                area_config.name,
                MEDIA_PLAYER_DOMAIN,
            )
        else:
            media_player_entities = [
                e["entity_id"] for e in data.entities[MEDIA_PLAYER_DOMAIN]
            ]
            if media_player_entities:
                try:
                    entities.append(
                        AreaMediaPlayerGroup(
                            area_config, coordinator, media_player_entities
                        )
                    )
                except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
                    _LOGGER.error(
                        "%s: Error creating media player group: %s",
                        area_config.slug,
                        str(exc),
                    )

        if not area_config.is_meta():
            try:
                entities.append(
                    switch_platform.MediaPlayerControlSwitch(area_config, coordinator)
                )
            except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
                _LOGGER.error(
                    "%s: Error loading media player control switch: %s",
                    area_config.name,
                    str(exc),
                )

        return entities

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return []


__all__ = ["MediaPlayerGroupsFeatureModule"]
