"""Light groups feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import LightGroupCategory, MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)
from custom_components.magic_areas.light_group_entities import AreaLightGroup, MagicLightGroup
from custom_components.magic_areas.light_groups import (
    CONF_ACCENT_LIGHTS,
    CONF_ACCENT_LIGHTS_ACT_ON,
    CONF_ACCENT_LIGHTS_STATES,
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    CONF_SLEEP_LIGHTS,
    CONF_SLEEP_LIGHTS_ACT_ON,
    CONF_SLEEP_LIGHTS_STATES,
    CONF_TASK_LIGHTS,
    CONF_TASK_LIGHTS_ACT_ON,
    CONF_TASK_LIGHTS_STATES,
    DEFAULT_LIGHT_GROUP_ACT_ON,
    LIGHT_GROUP_CATEGORIES,
)
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)

LIGHT_GROUP_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_OVERHEAD_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_OVERHEAD_LIGHTS_STATES, default=[AreaStates.OCCUPIED]
        ): cv.ensure_list,
        vol.Optional(
            CONF_OVERHEAD_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_SLEEP_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_SLEEP_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_SLEEP_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_ACCENT_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_ACCENT_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_ACCENT_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_TASK_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_TASK_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_TASK_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)


class LightGroupsFeatureModule(BaseFeatureModule):
    """Feature module for light groups."""

    id = MagicAreasFeatures.LIGHT_GROUPS
    domains = {LIGHT_DOMAIN, SWITCH_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return LIGHT_GROUP_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.LIGHT_GROUPS in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the light groups feature."""
        entities_by_domain = data.entities
        light_groups: list[Entity] = []

        if LIGHT_DOMAIN not in entities_by_domain:
            _LOGGER.debug("%s: No %s entities for area.", area_config.name, LIGHT_DOMAIN)
        else:
            light_entities = [e["entity_id"] for e in entities_by_domain[LIGHT_DOMAIN]]
            feature_config = data.feature_configs.get(MagicAreasFeatures.LIGHT_GROUPS, {})

            # Create light groups
            if area_config.is_meta():
                light_groups.append(
                    MagicLightGroup(
                        area_config,
                        coordinator,
                        light_entities,
                        translation_key=LightGroupCategory.ALL,
                    )
                )
            else:
                child_categories: list[str] = []

                # Create extended light groups
                for category in LIGHT_GROUP_CATEGORIES:
                    category_lights = [
                        light_entity
                        for light_entity in feature_config.get(category, {})
                        if light_entity in light_entities
                    ]

                    if category_lights:
                        _LOGGER.debug(
                            "%s: Creating %s group for area with lights: %s",
                            area_config.name,
                            category,
                            category_lights,
                        )
                        light_group_object = AreaLightGroup(
                            area_config,
                            coordinator,
                            category_lights,
                            category,
                            feature_config=feature_config,
                        )
                        light_groups.append(light_group_object)
                        child_categories.append(category)

                _LOGGER.debug(
                    "%s: Creating Area light group for area with child categories: %s",
                    area_config.name,
                    str(child_categories),
                )
                light_groups.append(
                    AreaLightGroup(
                        area_config,
                        coordinator,
                        light_entities,
                        category=LightGroupCategory.ALL,
                        child_categories=child_categories,
                        feature_config=feature_config,
                    )
                )

        if not area_config.is_meta():
            light_groups.append(
                switch_platform.LightControlSwitch(area_config, coordinator)
            )

        return light_groups

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.LIGHT_GROUPS,
                step_id="feature_conf_light_groups",
                schema=LIGHT_GROUP_FEATURE_SCHEMA,
            )
        ]


__all__ = ["LightGroupsFeatureModule"]
