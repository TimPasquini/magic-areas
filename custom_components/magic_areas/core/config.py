"""Pure configuration helpers for Magic Areas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from custom_components.magic_areas.area_maps import CONFIGURABLE_AREA_STATE_MAP
from custom_components.magic_areas.config_keys import (
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
)


def normalize_feature_key(feature: Any) -> str:
    """Normalize feature keys to strings."""
    if isinstance(feature, Enum):
        return str(feature.value)
    return str(feature)


def normalize_feature_config(
    config: dict[str, Any],
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    """Return enabled features and normalized feature config map."""
    raw_features = config.get(CONF_ENABLED_FEATURES, {})

    if isinstance(raw_features, list):
        normalized = {normalize_feature_key(feature) for feature in raw_features}
        return normalized, {feature: {} for feature in normalized}

    if isinstance(raw_features, dict):
        normalized = {normalize_feature_key(feature) for feature in raw_features}
        return normalized, {
            normalize_feature_key(feature): dict(values)
            for feature, values in raw_features.items()
        }

    return set(), {}


def has_configured_state(config: dict[str, Any], state: str) -> bool:
    """Check if area supports a given state based on config."""
    state_opts = CONFIGURABLE_AREA_STATE_MAP.get(state, None)

    if not state_opts:
        return False

    secondary_states = config.get(CONF_SECONDARY_STATES, {})
    return bool(secondary_states.get(state_opts))
