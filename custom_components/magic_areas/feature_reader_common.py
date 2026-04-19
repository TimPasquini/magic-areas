"""Shared generic helpers for feature option readers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from custom_components.magic_areas.core.config import (
    coerce_float,
    coerce_int,
    string_list,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.option_defaults import feature_option_default

type FeatureConfigValue = object
type FeatureConfig = Mapping[str, FeatureConfigValue]
type RawFeatureList = list[FeatureConfigValue]


def _int_default(feature: MagicAreasFeatures, key: str) -> int:
    """Return integer default for one feature option key."""
    default = feature_option_default(feature, key)
    if isinstance(default, int):
        return default
    msg = f"Expected int default for {feature}:{key}"
    raise TypeError(msg)


def _float_default(feature: MagicAreasFeatures, key: str) -> float:
    """Return float default for one feature option key."""
    default = feature_option_default(feature, key)
    if isinstance(default, (int, float)):
        return float(default)
    msg = f"Expected float default for {feature}:{key}"
    raise TypeError(msg)


@dataclass(frozen=True, slots=True)
class FeatureOptions:
    """Feature-scoped accessor for normalized option values."""

    feature_config: FeatureConfig
    feature: MagicAreasFeatures

    def value(self, key: str) -> FeatureConfigValue:
        """Return one feature option with default fallback."""
        return self.feature_config.get(key, feature_option_default(self.feature, key))

    def list_value(self, key: str, *, default: list[str] | None = None) -> list[str]:
        """Return one feature option as normalized list[str]."""
        return string_list(self.value(key), default=default)

    def int_value(self, key: str) -> int:
        """Return one feature option coerced to int."""
        return coerce_int(self.value(key), default=_int_default(self.feature, key))

    def float_value(self, key: str) -> float:
        """Return one feature option coerced to float."""
        return coerce_float(self.value(key), default=_float_default(self.feature, key))

    def str_value(self, key: str) -> str:
        """Return one feature option as string."""
        return str(self.value(key))

    def optional_entity_id(self, key: str) -> str | None:
        """Return configured entity_id when set as non-empty string."""
        value = self.feature_config.get(key)
        return value if isinstance(value, str) and value else None

    def raw_list_value(self, key: str) -> RawFeatureList:
        """Return one feature option as list preserving raw element types."""
        value = self.value(key)
        if isinstance(value, list):
            return list(value)
        return []


def options_for_feature(
    feature_configs: FeatureConfig,
    feature: MagicAreasFeatures,
) -> FeatureOptions:
    """Return options for a feature from full map or one feature slice."""
    feature_key = str(feature.value) if isinstance(feature, Enum) else str(feature)
    feature_config = feature_configs.get(feature_key)
    if isinstance(feature_config, Mapping):
        return FeatureOptions(feature_config=feature_config, feature=feature)
    return FeatureOptions(feature_config=feature_configs, feature=feature)
