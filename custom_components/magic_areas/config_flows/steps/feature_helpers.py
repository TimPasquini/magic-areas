"""Feature helper functions for options flow."""

from typing import TYPE_CHECKING

from custom_components.magic_areas.area_state import AreaType, META_AREA_GLOBAL
from custom_components.magic_areas.config_keys import CONF_TYPE
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.policy import (
    FEATURE_LIST,
    FEATURE_LIST_GLOBAL,
    FEATURE_LIST_META,
)
from custom_components.magic_areas.schemas.features import (
    CONFIGURABLE_FEATURES,
    NON_CONFIGURABLE_FEATURES_META,
)

if TYPE_CHECKING:
    from custom_components.magic_areas.core.area_config import AreaConfig


def get_feature_list(area_config: "AreaConfig | None") -> list[MagicAreasFeatures]:
    """Return list of available features for area type."""
    feature_list = FEATURE_LIST
    if area_config:
        area_type = area_config.config.get(CONF_TYPE)
        if area_type == AreaType.META:
            feature_list = FEATURE_LIST_META
        if area_config.id == META_AREA_GLOBAL.lower():
            feature_list = FEATURE_LIST_GLOBAL

    return feature_list


def get_configurable_features(area_config: "AreaConfig | None") -> list[MagicAreasFeatures]:
    """Return configurable features for area type."""
    filtered_configurable_features = list(CONFIGURABLE_FEATURES.keys())
    if area_config and area_config.is_meta():
        for feature in NON_CONFIGURABLE_FEATURES_META:
            if feature in filtered_configurable_features:
                filtered_configurable_features.remove(feature)

    return filtered_configurable_features
