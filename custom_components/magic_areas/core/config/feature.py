"""Generic configuration normalization helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum

from custom_components.magic_areas.config_keys.area import CONF_ENABLED_FEATURES

type FeatureConfigValue = object
type FeatureConfigDict = dict[str, FeatureConfigValue]
type FeatureConfigMapping = Mapping[str, FeatureConfigValue]


def coerce_int(value: object, default: int = 0) -> int:
    """Return integer value or a safe default."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, (str, bytes, bytearray, float)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)
    return int(default)


def coerce_float(value: object, default: float = 0.0) -> float:
    """Return float value or a safe default."""
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (str, bytes, bytearray, int, float)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)
    return float(default)


def string_list(value: object, default: Sequence[object] | None = None) -> list[str]:
    """Normalize a list-like value into a list of strings."""
    fallback = [] if default is None else [str(item) for item in default]
    if not isinstance(value, list):
        return fallback
    return [str(item) for item in value]


def enum_string_list(value: object) -> list[str]:
    """Normalize enum-or-string list values to a list of strings."""
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, Enum):
            normalized.append(str(item.value))
        else:
            normalized.append(str(item))
    return normalized


def normalize_feature_key(feature: object) -> str:
    """Normalize feature keys to strings."""
    if isinstance(feature, Enum):
        return str(feature.value)
    return str(feature)


def normalize_feature_config(
    config: FeatureConfigDict,
) -> tuple[set[str], dict[str, FeatureConfigDict]]:
    """Return enabled features and normalized feature config map."""
    raw_features = config.get(CONF_ENABLED_FEATURES, {})

    if isinstance(raw_features, list):
        normalized_features = {
            normalize_feature_key(feature) for feature in raw_features
        }
        return normalized_features, {feature: {} for feature in normalized_features}

    if isinstance(raw_features, dict):
        normalized: set[str] = set()
        feature_configs: dict[str, FeatureConfigDict] = {}
        for feature, values in raw_features.items():
            key = normalize_feature_key(feature)
            normalized.add(key)
            feature_configs[key] = dict(values) if isinstance(values, dict) else {}
        return normalized, feature_configs

    return set(), {}


def feature_config_slice(
    feature_configs: Mapping[str, object],
    feature: object,
) -> FeatureConfigDict:
    """Return one feature config slice from a normalized feature-config mapping."""
    normalized_key = normalize_feature_key(feature)
    value = feature_configs.get(normalized_key, {})
    return dict(value) if isinstance(value, dict) else {}
