"""Shared group entity classes for Magic Areas."""

from typing import TYPE_CHECKING

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.group.cover import CoverGroup
from homeassistant.components.group.fan import FanGroup
from homeassistant.components.group.media_player import MediaPlayerGroup
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN

from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


class AreaFanGroup(MagicGroupEntity, FanGroup):
    """Fan group."""

    feature_id = MagicAreasFeatures.FAN_GROUPS

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        entities: list[str],
    ) -> None:
        """Initialize fan group for the area."""
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
            name="",
            unique_id=self.unique_id,
        )
        delattr(self, "_attr_name")


class AreaCoverGroup(MagicGroupEntity, CoverGroup):
    """Cover group for handling all covers in the area."""

    feature_id = MagicAreasFeatures.COVER_GROUPS

    def __init__(
        self,
        area_config: "AreaConfig",
        coordinator: "MagicAreasCoordinator",
        device_class: str | None,
        entities: list[dict[str, str]],
    ) -> None:
        """Initialize cover group."""
        entity_ids = [entity["entity_id"] for entity in entities]
        MagicGroupEntity.__init__(
            self,
            area_config,
            coordinator,
            domain=COVER_DOMAIN,
            member_entity_ids=entity_ids,
            translation_key=device_class,
        )
        self._attr_device_class = (
            CoverDeviceClass(device_class) if device_class else None
        )
        self._entities = entities
        CoverGroup.__init__(
            self,
            entities=self.member_entity_ids,
            name="",
            unique_id=self._attr_unique_id,
        )
        delattr(self, "_attr_name")


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
            name="",
            unique_id=self._attr_unique_id,
            entities=self.member_entity_ids,
        )


__all__ = ["AreaCoverGroup", "AreaFanGroup", "AreaMediaPlayerGroup"]
