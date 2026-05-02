"""Cover groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.cover import DEVICE_CLASSES as COVER_DEVICE_CLASSES
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.const import CONF_ENTITIES, CONF_NAME
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model.managed_surfaces import (
    ConfigEntryHelperSurface,
    ManagedSurface,
    ManagedSurfaceKind,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import BaseFeatureModule

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)
GROUP_DOMAIN = "group"


class CoverGroupsFeatureModule(BaseFeatureModule):
    """Feature module for cover groups."""

    id = MagicAreasFeatures.COVER_GROUPS
    domains = {COVER_DOMAIN}

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the cover groups feature."""
        _ = (area_config, coordinator, data)
        return []

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Build desired native HA cover group helpers."""
        if COVER_DOMAIN not in data.entities:
            _LOGGER.debug("%s: No cover entities for area.", area_config.name)
            return []

        surfaces: list[ManagedSurface] = []
        for device_class in [*COVER_DEVICE_CLASSES, None]:
            partition_entities = [
                entity
                for entity in data.entities[COVER_DOMAIN]
                if entity.get("device_class") == device_class
            ]
            if not partition_entities:
                continue
            role = (
                "cover_group"
                if device_class is None
                else f"cover_group_{device_class}"
            )
            title_suffix = (
                "Cover Group"
                if device_class is None
                else f"Cover Group {str(device_class).replace('_', ' ').title()}"
            )
            surfaces.append(
                ConfigEntryHelperSurface(
                    unique_id=build_managed_surface_unique_id(
                        entry_id=data.area_config.hass_config.entry_id,
                        area_id=area_config.id,
                        feature_id=self.id,
                        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
                        role=role,
                    ),
                    domain=GROUP_DOMAIN,
                    title=f"Magic Areas Cover Groups {area_config.name} {title_suffix}",
                    options={
                        "group_type": COVER_DOMAIN,
                        CONF_NAME: (
                            f"Magic Areas Cover Groups {area_config.name} {title_suffix}"
                        ),
                        CONF_ENTITIES: [
                            entity["entity_id"] for entity in partition_entities
                        ],
                        "hide_members": False,
                    },
                    area_id=area_config.id,
                    device_identifier=(
                        DOMAIN,
                        f"{MAGIC_DEVICE_ID_PREFIX}{area_config.id}",
                    ),
                    device_name=area_config.name,
                )
            )
        return surfaces


__all__ = ["CoverGroupsFeatureModule"]
