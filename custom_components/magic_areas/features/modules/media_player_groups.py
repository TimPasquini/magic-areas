"""Media player groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_media_player_group_id,
)
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
)
from custom_components.magic_areas.features.control_builders import (
    build_primary_group_entities,
)
from custom_components.magic_areas.group_entities import AreaMediaPlayerGroup
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


class MediaPlayerGroupsFeatureModule(BaseFeatureModule):
    """Feature module for media player groups."""

    id = MagicAreasFeatures.MEDIA_PLAYER_GROUPS
    domains = {MEDIA_PLAYER_DOMAIN, SWITCH_DOMAIN}

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the media player groups feature."""
        return build_primary_group_entities(
            area_config=area_config,
            coordinator=coordinator,
            source_domain=MEDIA_PLAYER_DOMAIN,
            entities_by_domain=data.entities,
            feature_id=MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
            policy_id=str(ControlGroupPolicyId.MEDIA_PLAYER_GROUPS),
            build_group_id=lambda area_id: build_media_player_group_id(area_id=area_id),
            group_entity_factory=lambda member_ids: AreaMediaPlayerGroup(
                area_config, coordinator, member_ids
            ),
            control_switch_factory=lambda: switch_platform.MediaPlayerControlSwitch(
                area_config, coordinator
            ),
            group_registry=data.group_registry,
            logger=_LOGGER,
            group_label="media player group",
        )

__all__ = ["MediaPlayerGroupsFeatureModule"]
