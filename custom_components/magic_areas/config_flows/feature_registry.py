"""Declarative feature registry for Magic Areas config flows.

This file centralizes per-feature configuration metadata so OptionsFlowHandler
can act as a generic dispatcher instead of a god class.
"""

from __future__ import annotations

from dataclasses import dataclass

import voluptuous as vol

from custom_components.magic_areas.schemas.features import (
    CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT,
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
)
from custom_components.magic_areas.schemas.validation import (
    OPTIONS_LIGHT_GROUP,
    OPTIONS_FAN_GROUP,
    OPTIONS_CLIMATE_CONTROL,
    OPTIONS_CLIMATE_CONTROL_ENTITY_SELECT,
    OPTIONS_HEALTH_SENSOR,
    OPTIONS_AGGREGATES,
    OPTIONS_PRESENCE_HOLD,
    OPTIONS_BLE_TRACKERS,
    OPTIONS_WASP_IN_A_BOX,
    OPTIONS_AREA_AWARE_MEDIA_PLAYER,
)
from custom_components.magic_areas.enums import MagicAreasFeatures


@dataclass
class FeatureConfig:
    """Declarative description of a configurable feature."""

    name: str
    options: list
    schema: vol.Schema | None = None
    merge_options: bool = False
    next_step: str | None = None


FEATURE_REGISTRY: dict[str, FeatureConfig] = {
    MagicAreasFeatures.LIGHT_GROUPS: FeatureConfig(
        name=MagicAreasFeatures.LIGHT_GROUPS,
        options=OPTIONS_LIGHT_GROUP,
    ),
    MagicAreasFeatures.FAN_GROUPS: FeatureConfig(
        name=MagicAreasFeatures.FAN_GROUPS,
        options=OPTIONS_FAN_GROUP,
    ),
    MagicAreasFeatures.CLIMATE_CONTROL : FeatureConfig(
        name=MagicAreasFeatures.CLIMATE_CONTROL ,
        options=OPTIONS_CLIMATE_CONTROL_ENTITY_SELECT,
        schema=CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT,
        merge_options=True,
        next_step="feature_conf_climate_control_select_presets",
    ),
    f"{MagicAreasFeatures.CLIMATE_CONTROL }_presets": FeatureConfig(
        name=MagicAreasFeatures.CLIMATE_CONTROL ,
        options=OPTIONS_CLIMATE_CONTROL,
        schema=CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
        merge_options=True,
        next_step="feature_conf_climate_control_select_presets",
    ),
    MagicAreasFeatures.HEALTH: FeatureConfig(
        name=MagicAreasFeatures.HEALTH,
        options=OPTIONS_HEALTH_SENSOR,
    ),
    MagicAreasFeatures.AGGREGATES: FeatureConfig(
        name=MagicAreasFeatures.AGGREGATES,
        options=OPTIONS_AGGREGATES,
    ),
    MagicAreasFeatures.PRESENCE_HOLD: FeatureConfig(
        name=MagicAreasFeatures.PRESENCE_HOLD,
        options=OPTIONS_PRESENCE_HOLD,
    ),
    MagicAreasFeatures.BLE_TRACKER: FeatureConfig(
        name=MagicAreasFeatures.BLE_TRACKER,
        options=OPTIONS_BLE_TRACKERS,
    ),
    MagicAreasFeatures.WASP_IN_A_BOX: FeatureConfig(
        name=MagicAreasFeatures.WASP_IN_A_BOX,
        options=OPTIONS_WASP_IN_A_BOX,
    ),
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER: FeatureConfig(
        name=MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
        options=OPTIONS_AREA_AWARE_MEDIA_PLAYER,
    ),
}


__all__ = ["FeatureConfig", "FEATURE_REGISTRY"]
