"""Climate control feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.core.control_group import ControlGroupDefinition
from custom_components.magic_areas.core.group_registry import GROUP_REGISTRY
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)
from custom_components.magic_areas.config_keys import (
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
    DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
    DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
    DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
)
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)

CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT = vol.Schema(
    {
        vol.Required(CONF_CLIMATE_CONTROL_ENTITY_ID): cv.entity_id,
    }
)

CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT = vol.Schema(
    {
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_CLEAR,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_SLEEP,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
        ): str,
    },
    extra=vol.REMOVE_EXTRA,
)

CLIMATE_CONTROL_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CLIMATE_CONTROL_ENTITY_ID): cv.entity_id,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_CLEAR,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_SLEEP,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
        ): str,
        vol.Optional(
            CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
            default=DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
        ): str,
    },
    extra=vol.REMOVE_EXTRA,
)


class ClimateControlFeatureModule(BaseFeatureModule):
    """Feature module for climate control."""

    id = MagicAreasFeatures.CLIMATE_CONTROL
    domains = {SWITCH_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return CLIMATE_CONTROL_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.CLIMATE_CONTROL in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for climate control."""
        try:
            feature_config = data.feature_configs.get(
                MagicAreasFeatures.CLIMATE_CONTROL, {}
            )
            climate_entity = feature_config.get(CONF_CLIMATE_CONTROL_ENTITY_ID)
            group_definitions: list[ControlGroupDefinition] = []
            if not climate_entity:
                GROUP_REGISTRY.register_area_defaults(
                    area_id=area_config.id,
                    definitions=[],
                    policy_id="climate_control",
                )
                return []

            group_definitions.append(
                ControlGroupDefinition(
                    group_id=f"climate_control_{area_config.id}_climate_control",
                    members=(climate_entity,),
                    trigger_states=(),
                    policy_id="climate_control",
                    metadata={
                        "feature": str(MagicAreasFeatures.CLIMATE_CONTROL),
                    },
                )
            )
            GROUP_REGISTRY.register_area_defaults(
                area_id=area_config.id,
                definitions=group_definitions,
                policy_id="climate_control",
            )
            return [switch_platform.ClimateControlSwitch(area_config, coordinator)]
        except Exception as exc:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error loading climate control switch: %s",
                area_config.name,
                str(exc),
            )
            return []

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.CLIMATE_CONTROL,
                step_id="feature_conf_climate_control",
                schema=CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT,
                merge_options=True,
                next_step="feature_conf_climate_control_select_presets",
            )
        ]


__all__ = ["ClimateControlFeatureModule"]
