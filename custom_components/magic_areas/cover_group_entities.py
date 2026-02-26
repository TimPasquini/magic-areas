"""Cover group entities for Magic Areas."""

from typing import TYPE_CHECKING

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.group.cover import CoverGroup

from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.const import EMPTY_STRING
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


class AreaCoverGroup(MagicGroupEntity, CoverGroup):
    """Cover group for handling all the covers in the area."""

    feature_id = MagicAreasFeatures.COVER_GROUPS

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        device_class: str | None,
        entities: list[dict[str, str]],
    ) -> None:
        """Initialize the cover group."""
        entity_ids = [e["entity_id"] for e in entities]
        MagicGroupEntity.__init__(
            self,
            area_config,
            coordinator,
            domain=COVER_DOMAIN,
            member_entity_ids=entity_ids,
            translation_key=device_class,
        )
        sensor_device_class: CoverDeviceClass | None = (
            CoverDeviceClass(device_class) if device_class else None
        )
        self._attr_device_class = sensor_device_class
        self._entities = entities
        CoverGroup.__init__(
            self,
            entities=self.member_entity_ids,
            name=EMPTY_STRING,
            unique_id=self._attr_unique_id,
        )
        delattr(self, "_attr_name")


__all__ = ["AreaCoverGroup"]
