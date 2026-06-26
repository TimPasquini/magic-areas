"""Climate control feature module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.core.runtime_model import (
    ControlGroupPolicyId,
)
from custom_components.magic_areas.core.runtime_model.feature_ids import (
    build_climate_control_group_id,
)
from custom_components.magic_areas.features.config.readers import (
    CLIMATE_CONTROL_ENTITY_KEY,
    CLIMATE_CONTROL_PRESET_OPTION_KEYS,
    climate_control_config,
)
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureOption,
    default_feature_options,
    schema_from_options,
)
from custom_components.magic_areas.features.control_builders import (
    build_control_group_definition,
    build_control_switch_entities,
    register_area_default_groups,
)
import custom_components.magic_areas.switch as switch_platform

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)
_EXPECTED_BUILD_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


def _log_build_error(*, area_slug: str, label: str, exc: Exception) -> None:
    """Log a standardized feature build failure."""
    _LOGGER.error("%s: Error building %s: %s", area_slug, label, str(exc))


CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT = vol.Schema(
    {vol.Required(CLIMATE_CONTROL_ENTITY_KEY): cv.entity_id}
)

CLIMATE_CONTROL_OPTIONS = [
    FeatureOption(
        key=CLIMATE_CONTROL_ENTITY_KEY,
        validator=cv.entity_id,
    ),
    *default_feature_options(
        feature=MagicAreasFeatures.CLIMATE_CONTROL,
        keys=CLIMATE_CONTROL_PRESET_OPTION_KEYS,
        validator=str,
    ),
]

CLIMATE_CONTROL_FEATURE_SCHEMA = schema_from_options(options=CLIMATE_CONTROL_OPTIONS)


class ClimateControlFeatureModule(BaseFeatureModule):
    """Feature module for climate control."""

    id = MagicAreasFeatures.CLIMATE_CONTROL
    domains = {SWITCH_DOMAIN}
    feature_schema = CLIMATE_CONTROL_FEATURE_SCHEMA
    feature_config_step_schema = CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT
    feature_merge_options = True
    feature_next_step = "feature_conf_climate_control_select_presets"

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for climate control."""
        try:
            climate_entity = climate_control_config(data.feature_configs).entity_id
            if not climate_entity:
                register_area_default_groups(
                    area_id=area_config.id,
                    definitions=[],
                    policy_id=str(ControlGroupPolicyId.CLIMATE_CONTROL),
                    group_registry=data.group_registry,
                )
                return []

            register_area_default_groups(
                area_id=area_config.id,
                definitions=[
                    build_control_group_definition(
                        group_id=build_climate_control_group_id(area_id=area_config.id),
                        members=[climate_entity],
                        trigger_states=(),
                        policy_id=str(ControlGroupPolicyId.CLIMATE_CONTROL),
                        feature_id=MagicAreasFeatures.CLIMATE_CONTROL,
                    )
                ],
                policy_id=str(ControlGroupPolicyId.CLIMATE_CONTROL),
                group_registry=data.group_registry,
            )
            return build_control_switch_entities(
                area_config=area_config,
                switch_factory=lambda: switch_platform.ClimateControlSwitch(
                    area_config, coordinator
                ),
                logger=_LOGGER,
                switch_label="climate control switch",
            )
        except _EXPECTED_BUILD_ERRORS as exc:  # pragma: no cover
            _log_build_error(
                area_slug=area_config.slug,
                label="climate control entities",
                exc=exc,
            )
            return []


__all__ = ["ClimateControlFeatureModule"]
