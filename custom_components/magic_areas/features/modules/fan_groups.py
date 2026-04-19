"""Fan groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_fan_group_id,
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
    build_primary_group_entities,
)
from custom_components.magic_areas.group_entities import AreaFanGroup
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


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
        return build_primary_group_entities(
            area_config=area_config,
            coordinator=coordinator,
            source_domain=FAN_DOMAIN,
            entities_by_domain=data.entities,
            feature_id=MagicAreasFeatures.FAN_GROUPS,
            policy_id=str(ControlGroupPolicyId.FAN_GROUPS),
            build_group_id=lambda area_id: build_fan_group_id(area_id=area_id),
            group_entity_factory=lambda member_ids: AreaFanGroup(
                area_config, coordinator, member_ids
            ),
            trigger_states=(config.required_state,),
            control_switch_factory=lambda: switch_platform.FanControlSwitch(
                area_config, coordinator
            ),
            group_registry=data.group_registry,
            logger=_LOGGER,
            group_label="fan group",
        )

__all__ = ["FanGroupsFeatureModule"]
