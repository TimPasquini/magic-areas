"""Media player group entities for Magic Areas."""

from typing import TYPE_CHECKING

from homeassistant.components.group.media_player import MediaPlayerGroup
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN

from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.config_keys import EMPTY_STRING
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


class AreaMediaPlayerGroup(MagicGroupEntity, MediaPlayerGroup):
    """Media player group."""

    feature_id = MagicAreasFeatures.MEDIA_PLAYER_GROUPS

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        entities: list[str],
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


__all__ = ["AreaMediaPlayerGroup"]
