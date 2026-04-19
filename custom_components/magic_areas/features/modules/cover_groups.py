"""Cover groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.cover import DEVICE_CLASSES as COVER_DEVICE_CLASSES
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import BaseFeatureModule
from custom_components.magic_areas.features.control_builders import (
    build_partitioned_group_entities,
)
from custom_components.magic_areas.group_entities import AreaCoverGroup

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


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
        return build_partitioned_group_entities(
            area_config=area_config,
            coordinator=coordinator,
            source_domain=COVER_DOMAIN,
            entities_by_domain=data.entities,
            partitions=[*COVER_DEVICE_CLASSES, None],
            partition_key="device_class",
            group_entity_factory=lambda device_class, partition_entities: AreaCoverGroup(
                area_config,
                coordinator,
                device_class,
                partition_entities,
            ),
            logger=_LOGGER,
            group_label="cover group",
        )


__all__ = ["CoverGroupsFeatureModule"]
