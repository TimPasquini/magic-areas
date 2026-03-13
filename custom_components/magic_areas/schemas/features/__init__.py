"""Registry-backed schemas for feature configuration."""

from __future__ import annotations

from itertools import chain

from voluptuous import Schema
import voluptuous as vol

from custom_components.magic_areas.config_keys.area import (
    CLIMATE_CONTROL_PRESET_KEYS,
)
from custom_components.magic_areas.feature_contracts import (
    schema_from_default_options,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.feature_registry import RUNTIME_FEATURE_REGISTRY
ALL_FEATURES = set(RUNTIME_FEATURE_REGISTRY.all_features())

CONFIGURABLE_FEATURES: dict[MagicAreasFeatures, vol.Schema] = {}
for _module in RUNTIME_FEATURE_REGISTRY.modules():
    _schema = _module.config_schema()
    if _schema is not None:
        CONFIGURABLE_FEATURES[_module.id] = _schema

CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT = schema_from_default_options(
    feature=MagicAreasFeatures.CLIMATE_CONTROL,
    keys_and_validators=tuple((key, str) for key in CLIMATE_CONTROL_PRESET_KEYS),
    include_keys=set(CLIMATE_CONTROL_PRESET_KEYS),
)

NON_CONFIGURABLE_FEATURES_META = [
    module.id
    for module in RUNTIME_FEATURE_REGISTRY.modules()
    if module.supports_meta_area and not module.configurable_on_meta
]

NON_CONFIGURABLE_FEATURES: dict[str, dict[str, object]] = {
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

__all__ = [
    "CLIMATE_CONTROL_FEATURE_SCHEMA_PRESET_SELECT",
    "CONFIGURABLE_FEATURES",
    "FEATURES_SCHEMA",
    "NON_CONFIGURABLE_FEATURES_META",
]
