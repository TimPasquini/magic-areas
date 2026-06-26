"""Media player groups feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import CONF_ENTITIES, CONF_NAME
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ManagedSurface,
    ManagedSurfaceKind,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
)
from custom_components.magic_areas.features.control_builders import (
    build_control_group_definition,
    register_area_default_groups,
)
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

GROUP_DOMAIN = "group"


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
        member_ids = [
            entity["entity_id"] for entity in data.entities.get(MEDIA_PLAYER_DOMAIN, [])
        ]
        definitions = []
        if member_ids:
            definitions.append(
                build_control_group_definition(
                    group_id=_media_player_group_surface_unique_id(area_config, data),
                    members=member_ids,
                    trigger_states=(),
                    policy_id=str(ControlGroupPolicyId.MEDIA_PLAYER_GROUPS),
                    feature_id=MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
                )
            )
        register_area_default_groups(
            area_id=area_config.id,
            definitions=definitions,
            policy_id=str(ControlGroupPolicyId.MEDIA_PLAYER_GROUPS),
            group_registry=data.group_registry,
        )
        if area_config.is_meta():
            return []
        return [switch_platform.MediaPlayerControlSwitch(area_config, coordinator)]

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Build desired native HA media-player group helper."""
        member_ids = [
            entity["entity_id"] for entity in data.entities.get(MEDIA_PLAYER_DOMAIN, [])
        ]
        if not member_ids:
            return []
        title = f"Magic Areas Media Player Groups {area_config.name} Media Player Group"
        return [
            ConfigEntryHelperSurface(
                unique_id=_media_player_group_surface_unique_id(area_config, data),
                domain=GROUP_DOMAIN,
                title=title,
                options={
                    "group_type": MEDIA_PLAYER_DOMAIN,
                    CONF_NAME: title,
                    CONF_ENTITIES: member_ids,
                    "hide_members": False,
                },
                area_id=area_config.id,
                device_identifier=(DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{area_config.id}"),
                device_name=area_config.name,
            )
        ]


def _media_player_group_surface_unique_id(
    area_config: AreaConfig,
    data: MagicAreasData,
) -> str:
    """Return managed helper unique ID for the area media-player group."""
    return build_managed_surface_unique_id(
        entry_id=area_config.hass_config.entry_id,
        area_id=area_config.id,
        feature_id=MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="media_player_group",
    )


__all__ = ["MediaPlayerGroupsFeatureModule"]
