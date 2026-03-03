"""Pure configuration helpers for Magic Areas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from custom_components.magic_areas.area_maps import CONFIGURABLE_AREA_STATE_MAP
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_CUSTOM_CONTROL_GROUPS,
    CONF_ENABLED_FEATURES,
    CONF_SECONDARY_STATES,
)
from custom_components.magic_areas.core.control_group import ControlGroupDefinition


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


def has_configured_state(config: dict[str, Any], state: AreaStates) -> bool:
    """Check if area supports a given state based on config."""
    state_opts = CONFIGURABLE_AREA_STATE_MAP.get(state, None)

    if not state_opts:
        return False

    secondary_states = config.get(CONF_SECONDARY_STATES, {})
    return bool(secondary_states.get(state_opts))


def has_feature(config: dict[str, Any], feature: str) -> bool:
    """Check if area has a given feature."""
    enabled, _ = normalize_feature_config(config)
    return feature in enabled


def get_feature_config(config: dict[str, Any], feature: str) -> dict[str, Any]:
    """Return configuration for a given feature."""
    enabled, feature_configs = normalize_feature_config(config)
    if feature not in enabled:
        return {}

    if not feature_configs:
        return {}

    return feature_configs.get(feature, {})


def normalize_custom_control_groups(
    config: dict[str, Any],
) -> list[ControlGroupDefinition]:
    """Return normalized custom control-group definitions from area config."""
    raw_groups = config.get(CONF_CUSTOM_CONTROL_GROUPS, [])
    if not isinstance(raw_groups, list):
        return []

    normalized: list[ControlGroupDefinition] = []
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            continue
        group_id = raw_group.get("group_id")
        members = raw_group.get("members")
        if not isinstance(group_id, str) or not isinstance(members, list):
            continue
        metadata_value = raw_group.get("metadata")
        metadata: dict[str, Any] = metadata_value if isinstance(metadata_value, dict) else {}
        normalized.append(
            ControlGroupDefinition(
                group_id=group_id,
                members=tuple(str(member) for member in members),
                trigger_states=tuple(str(state) for state in raw_group.get("trigger_states", [])),
                policy_id=str(raw_group.get("policy_id", "custom_control_group")),
                metadata=metadata,
            )
        )

    return normalized
