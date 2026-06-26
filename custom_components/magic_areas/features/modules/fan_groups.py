"""Fan groups feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import CONF_ENTITIES, CONF_NAME
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ManagedSurface,
    ManagedSurfaceKind,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.features.config.readers import (
    FAN_GROUPS_OPTION_KEYS,
    fan_groups_config,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
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


FAN_GROUP_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.FAN_GROUPS,
    keys_and_validators=(
        (FAN_GROUPS_OPTION_KEYS[0], str),
        (FAN_GROUPS_OPTION_KEYS[1], str),
        (FAN_GROUPS_OPTION_KEYS[2], vol.Coerce(float)),
    ),
)


class FanGroupsFeatureModule(BaseFeatureModule):
    """Feature module for fan groups."""

    id = MagicAreasFeatures.FAN_GROUPS
    domains = {FAN_DOMAIN, SWITCH_DOMAIN}
    feature_schema = FAN_GROUP_FEATURE_SCHEMA
    supports_meta_area = False
    supports_global_meta_area = False
    configurable_on_meta = False
    configurable_on_global_meta = False

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the fan groups feature."""
        config = fan_groups_config(data.feature_configs)
        member_ids = [
            entity["entity_id"] for entity in data.entities.get(FAN_DOMAIN, [])
        ]
        definitions = []
        if member_ids:
            definitions.append(
                build_control_group_definition(
                    group_id=_fan_group_surface_unique_id(area_config, data),
                    members=member_ids,
                    trigger_states=(config.required_state,),
                    policy_id=str(ControlGroupPolicyId.FAN_GROUPS),
                    feature_id=MagicAreasFeatures.FAN_GROUPS,
                )
            )
        register_area_default_groups(
            area_id=area_config.id,
            definitions=definitions,
            policy_id=str(ControlGroupPolicyId.FAN_GROUPS),
            group_registry=data.group_registry,
        )
        if area_config.is_meta():
            return []
        return [switch_platform.FanControlSwitch(area_config, coordinator)]

    def desired_managed_surfaces(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedSurface]:
        """Build desired native HA fan group helper."""
        member_ids = [
            entity["entity_id"] for entity in data.entities.get(FAN_DOMAIN, [])
        ]
        if not member_ids:
            return []
        title = f"Magic Areas Fan Groups {area_config.name} Fan Group"
        return [
            ConfigEntryHelperSurface(
                unique_id=_fan_group_surface_unique_id(area_config, data),
                domain=GROUP_DOMAIN,
                title=title,
                options={
                    "group_type": FAN_DOMAIN,
                    CONF_NAME: title,
                    CONF_ENTITIES: member_ids,
                    "hide_members": False,
                },
                area_id=area_config.id,
                device_identifier=(DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{area_config.id}"),
                device_name=area_config.name,
            )
        ]


def _fan_group_surface_unique_id(
    area_config: AreaConfig,
    data: MagicAreasData,
) -> str:
    """Return managed helper unique ID for the area fan group."""
    return build_managed_surface_unique_id(
        entry_id=area_config.hass_config.entry_id,
        area_id=area_config.id,
        feature_id=MagicAreasFeatures.FAN_GROUPS,
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role="fan_group",
    )


__all__ = ["FanGroupsFeatureModule"]
