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
from custom_components.magic_areas.features import (
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_FAN_GROUPS,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_WASP_IN_A_BOX,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
)


@dataclass(frozen=True)
class FeatureConfig:
    """Declarative description of a configurable feature."""

    name: str
    options: list
    schema: vol.Schema | None = None
    merge_options: bool = False
    next_step: str | None = None


FEATURE_REGISTRY: dict[str, FeatureConfig] = {
    CONF_FEATURE_LIGHT_GROUPS: FeatureConfig(
        name=CONF_FEATURE_LIGHT_GROUPS,
        options=OPTIONS_LIGHT_GROUP,
    ),
    CONF_FEATURE_FAN_GROUPS: FeatureConfig(
        name=CONF_FEATURE_FAN_GROUPS,
        options=OPTIONS_FAN_GROUP,
    ),
    CONF_FEATURE_CLIMATE_CONTROL: FeatureConfig(
        name=CONF_FEATURE_CLIMATE_CONTROL,
        options=OPTIONS_CLIMATE_CONTROL_ENTITY_SELECT,
        schema=CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT,
        merge_options=True,
        next_step="feature_conf_climate_control_select_presets",
    ),
    f"{CONF_FEATURE_CLIMATE_CONTROL}_presets": FeatureConfig(
        name=CONF_FEATURE_CLIMATE_CONTROL,
        options=OPTIONS_CLIMATE_CONTROL,
        schema=CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
        merge_options=True,
        next_step="feature_conf_climate_control_select_presets",
    ),
    CONF_FEATURE_HEALTH: FeatureConfig(
        name=CONF_FEATURE_HEALTH,
        options=OPTIONS_HEALTH_SENSOR,
    ),
    CONF_FEATURE_AGGREGATION: FeatureConfig(
        name=CONF_FEATURE_AGGREGATION,
        options=OPTIONS_AGGREGATES,
    ),
    CONF_FEATURE_PRESENCE_HOLD: FeatureConfig(
        name=CONF_FEATURE_PRESENCE_HOLD,
        options=OPTIONS_PRESENCE_HOLD,
    ),
    CONF_FEATURE_BLE_TRACKERS: FeatureConfig(
        name=CONF_FEATURE_BLE_TRACKERS,
        options=OPTIONS_BLE_TRACKERS,
    ),
    CONF_FEATURE_WASP_IN_A_BOX: FeatureConfig(
        name=CONF_FEATURE_WASP_IN_A_BOX,
        options=OPTIONS_WASP_IN_A_BOX,
    ),
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: FeatureConfig(
        name=CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
        options=OPTIONS_AREA_AWARE_MEDIA_PLAYER,
    ),
}


__all__ = ["FeatureConfig", "FEATURE_REGISTRY"]
