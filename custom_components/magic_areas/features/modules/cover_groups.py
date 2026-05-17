"""Cover groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.cover import DEVICE_CLASSES as COVER_DEVICE_CLASSES
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import CONF_ENTITIES, CONF_NAME
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ControlGroupPolicyId,
    ManagedSurface,
    ManagedSurfaceKind,
    GroupMetadataKey,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import BaseFeatureModule
from custom_components.magic_areas.features.control_builders import (
    build_control_group_definition,
    register_area_default_groups,
)
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)
GROUP_DOMAIN = "group"


class CoverGroupsFeatureModule(BaseFeatureModule):
    """Feature module for cover groups."""

    id = MagicAreasFeatures.COVER_GROUPS
    domains = {COVER_DOMAIN, SWITCH_DOMAIN}

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the cover groups feature."""
        definitions = [
            build_control_group_definition(
                group_id=_cover_group_surface_unique_id(
                    area_config=area_config,
                    data=data,
                    role=role,
                ),
                members=member_ids,
                trigger_states=(),
                policy_id=str(ControlGroupPolicyId.COVER_GROUPS),
                feature_id=MagicAreasFeatures.COVER_GROUPS,
                role=None,
                metadata={str(GroupMetadataKey.CATEGORY): role},
            )
            for role, _title_suffix, member_ids in _cover_group_specs(area_config, data)
        ]
        register_area_default_groups(
            area_id=area_config.id,
            definitions=definitions,
            policy_id=str(ControlGroupPolicyId.COVER_GROUPS),
            group_registry=data.group_registry,
        )
        if area_config.is_meta():
            return []
        return [switch_platform.CoverControlSwitch(area_config, coordinator)]

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
        for role, title_suffix, member_ids in _cover_group_specs(area_config, data):
            surfaces.append(
                ConfigEntryHelperSurface(
                    unique_id=_cover_group_surface_unique_id(
                        area_config=area_config,
                        data=data,
                        role=role,
                    ),
                    domain=GROUP_DOMAIN,
                    title=f"Magic Areas Cover Groups {area_config.name} {title_suffix}",
                    options={
                        "group_type": COVER_DOMAIN,
                        CONF_NAME: (
                            f"Magic Areas Cover Groups {area_config.name} {title_suffix}"
                        ),
                        CONF_ENTITIES: member_ids,
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


def _cover_group_specs(
    area_config: AreaConfig,
    data: MagicAreasData,
) -> list[tuple[str, str, list[str]]]:
    """Return role, title suffix, and member entity IDs for cover group helpers."""
    del area_config
    specs: list[tuple[str, str, list[str]]] = []
    for device_class in [*COVER_DEVICE_CLASSES, None]:
        partition_entities = [
            entity
            for entity in data.entities.get(COVER_DOMAIN, [])
            if entity.get("device_class") == device_class
        ]
        if not partition_entities:
            continue
        role = "cover_group" if device_class is None else f"cover_group_{device_class}"
        title_suffix = (
            "Cover Group"
            if device_class is None
            else f"Cover Group {str(device_class).replace('_', ' ').title()}"
        )
        specs.append(
            (
                role,
                title_suffix,
                [entity["entity_id"] for entity in partition_entities],
            )
        )
    return specs


def _cover_group_surface_unique_id(
    *,
    area_config: AreaConfig,
    data: MagicAreasData,
    role: str,
) -> str:
    """Return managed helper unique ID for an area cover group role."""
    return build_managed_surface_unique_id(
        entry_id=area_config.hass_config.entry_id,
        area_id=area_config.id,
        feature_id=MagicAreasFeatures.COVER_GROUPS,
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role=role,
    )


__all__ = ["CoverGroupsFeatureModule"]
