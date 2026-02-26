"""Registry and schemas for all feature configurations."""

from __future__ import annotations

from itertools import chain
from typing import Any

from voluptuous import Schema
import voluptuous as vol

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.policy import FEATURE_LIST, FEATURE_LIST_GLOBAL
from custom_components.magic_areas.features.modules.aggregates import (
    AGGREGATE_FEATURE_SCHEMA,
)
from custom_components.magic_areas.features.modules.area_aware_media_player import (
    AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA,
)
from custom_components.magic_areas.features.modules.ble_trackers import (
    BLE_TRACKER_FEATURE_SCHEMA,
)
from custom_components.magic_areas.features.modules.climate_control import (
    CLIMATE_CONTROL_FEATURE_SCHEMA,
    CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT,
    CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT,
)
from custom_components.magic_areas.features.modules.fan_groups import (
    FAN_GROUP_FEATURE_SCHEMA,
)
from custom_components.magic_areas.features.modules.health import (
    HEALTH_FEATURE_SCHEMA,
)
from custom_components.magic_areas.features.modules.light_groups import (
    LIGHT_GROUP_FEATURE_SCHEMA,
)
from custom_components.magic_areas.features.modules.presence_hold import (
    PRESENCE_HOLD_FEATURE_SCHEMA,
)
from custom_components.magic_areas.features.modules.wasp_in_a_box import (
    WASP_IN_A_BOX_FEATURE_SCHEMA,
)

__all__ = [
    "AGGREGATE_FEATURE_SCHEMA",
    "HEALTH_FEATURE_SCHEMA",
    "PRESENCE_HOLD_FEATURE_SCHEMA",
    "BLE_TRACKER_FEATURE_SCHEMA",
    "WASP_IN_A_BOX_FEATURE_SCHEMA",
    "CLIMATE_CONTROL_FEATURE_SCHEMA",
    "CLIMATE_CONTROL_FEATURE_SCHEMA_ENTITY_SELECT",
    "CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT",
    "FAN_GROUP_FEATURE_SCHEMA",
    "LIGHT_GROUP_FEATURE_SCHEMA",
    "AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA",
    "ALL_FEATURES",
    "CONFIGURABLE_FEATURES",
    "NON_CONFIGURABLE_FEATURES",
    "NON_CONFIGURABLE_FEATURES_META",
    "FEATURES_SCHEMA",
]

ALL_FEATURES = set(FEATURE_LIST) | set(FEATURE_LIST_GLOBAL)

CONFIGURABLE_FEATURES = {
    MagicAreasFeatures.LIGHT_GROUPS: LIGHT_GROUP_FEATURE_SCHEMA,
    MagicAreasFeatures.CLIMATE_CONTROL: CLIMATE_CONTROL_FEATURE_SCHEMA,
    MagicAreasFeatures.FAN_GROUPS: FAN_GROUP_FEATURE_SCHEMA,
    MagicAreasFeatures.AGGREGATES: AGGREGATE_FEATURE_SCHEMA,
    MagicAreasFeatures.HEALTH: HEALTH_FEATURE_SCHEMA,
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER: AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA,
    MagicAreasFeatures.PRESENCE_HOLD: PRESENCE_HOLD_FEATURE_SCHEMA,
    MagicAreasFeatures.BLE_TRACKER: BLE_TRACKER_FEATURE_SCHEMA,
    MagicAreasFeatures.WASP_IN_A_BOX: WASP_IN_A_BOX_FEATURE_SCHEMA,
}

NON_CONFIGURABLE_FEATURES_META = [
    MagicAreasFeatures.LIGHT_GROUPS,
    MagicAreasFeatures.FAN_GROUPS,
]

NON_CONFIGURABLE_FEATURES: dict[str, dict[str, Any]] = {
    str(feature): {} for feature in ALL_FEATURES if feature not in CONFIGURABLE_FEATURES
}

FEATURES_SCHEMA: Schema = vol.Schema(
    {
        vol.Optional(str(feature)): feature_schema
        for feature, feature_schema in chain(
            CONFIGURABLE_FEATURES.items(), NON_CONFIGURABLE_FEATURES.items()
        )
    },
    extra=vol.REMOVE_EXTRA,
)
