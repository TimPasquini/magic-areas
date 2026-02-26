"""Fan group entities for Magic Areas."""

from typing import TYPE_CHECKING

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.group.fan import FanGroup

from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.const import EMPTY_STRING
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


class AreaFanGroup(MagicGroupEntity, FanGroup):
    """Fan Group."""

    feature_id = MagicAreasFeatures.FAN_GROUPS

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        entities: list[str],
    ) -> None:
        """Init the fan group for the area."""
        MagicGroupEntity.__init__(
            self,
            area_config,
            coordinator,
            domain=FAN_DOMAIN,
            member_entity_ids=entities,
        )
        FanGroup.__init__(
            self,
            entities=self.member_entity_ids,
            name=EMPTY_STRING,
            unique_id=self.unique_id,
        )

        delattr(self, "_attr_name")


__all__ = ["AreaFanGroup"]
