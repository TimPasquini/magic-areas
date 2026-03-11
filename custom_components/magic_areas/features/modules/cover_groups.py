"""Cover groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.cover import DEVICE_CLASSES as COVER_DEVICE_CLASSES
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import BaseFeatureModule
from custom_components.magic_areas.cover_group_entities import AreaCoverGroup

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


class CoverGroupsFeatureModule(BaseFeatureModule):
    """Feature module for cover groups."""

    id = MagicAreasFeatures.COVER_GROUPS
    domains = {COVER_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return None

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.COVER_GROUPS in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the cover groups feature."""
        if COVER_DOMAIN not in data.entities:
            _LOGGER.debug("No %s entities for area %s", COVER_DOMAIN, area_config.name)
            return []

        entities: list[Entity] = []

        for device_class in [*COVER_DEVICE_CLASSES, None]:
            entities_in_device_class = [
                e
                for e in data.entities[COVER_DOMAIN]
                if e.get("device_class") == device_class
            ]
            cover_ids = [e["entity_id"] for e in entities_in_device_class]

            if not cover_ids:
                continue

            _LOGGER.debug(
                "Creating %s cover group for %s with covers: %s",
                device_class,
                area_config.name,
                cover_ids,
            )
            try:
                entities.append(
                    AreaCoverGroup(
                        area_config, coordinator, device_class, entities_in_device_class
                    )
                )
            except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
                _LOGGER.error(
                    "%s: Error creating cover group: %s",
                    area_config.slug,
                    str(exc),
                )

        return entities


__all__ = ["CoverGroupsFeatureModule"]
