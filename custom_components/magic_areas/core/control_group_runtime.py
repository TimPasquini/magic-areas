"""Runtime helpers for resolving control-group targets."""

from __future__ import annotations

from collections.abc import Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.group_registry import RegisteredControlGroup
from custom_components.magic_areas.core.group_registry import GROUP_REGISTRY


def _metadata_matches(
    entry: RegisteredControlGroup,
    *,
    metadata_key: str,
    metadata_value: str,
    metadata_filters: Mapping[str, str] | None = None,
) -> bool:
    """Return True when metadata key/value + filters match."""
    if entry.definition.metadata.get(metadata_key) != metadata_value:
        return False
    if metadata_filters and any(
        entry.definition.metadata.get(key) != value
        for key, value in metadata_filters.items()
    ):
        return False
    return True


def resolve_group_entity_id(
    hass: HomeAssistant,
    *,
    area_id: str,
    policy_id: str,
    domain: str,
) -> str | None:
    """Resolve a control-group entity ID using registry-defined groups only."""
    entity_registry = er.async_get(hass)

    resolved_group = GROUP_REGISTRY.get_first_for_area_policy(area_id, policy_id)
    if not resolved_group:
        return None

    return entity_registry.async_get_entity_id(
        domain,
        DOMAIN,
        resolved_group.definition.group_id,
    )


def resolve_group_member_entity_id(
    *,
    area_id: str,
    policy_id: str,
    member_index: int = 0,
) -> str | None:
    """Resolve a member entity ID from an area+policy control-group definition."""
    resolved_group = GROUP_REGISTRY.get_first_for_area_policy(area_id, policy_id)
    if not resolved_group:
        return None

    members = resolved_group.definition.members
    if member_index < 0 or member_index >= len(members):
        return None

    return members[member_index]


def resolve_group_entity_ids_by_metadata(
    hass: HomeAssistant,
    *,
    area_id: str,
    policy_id: str,
    domain: str,
    metadata_key: str,
    metadata_filters: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve entity IDs keyed by a group metadata value."""
    entity_registry = er.async_get(hass)
    resolved: dict[str, str] = {}

    for entry in GROUP_REGISTRY.get_for_area_policy(area_id, policy_id):
        metadata_value = entry.definition.metadata.get(metadata_key)
        if not isinstance(metadata_value, str) or not _metadata_matches(
            entry,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
            metadata_filters=metadata_filters,
        ):
            continue
        entity_id = entity_registry.async_get_entity_id(
            domain,
            DOMAIN,
            entry.definition.group_id,
        )
        if entity_id:
            resolved[metadata_value] = entity_id

    return resolved


def resolve_group_entity_id_by_metadata(
    hass: HomeAssistant,
    *,
    area_id: str,
    policy_id: str,
    domain: str,
    metadata_key: str,
    metadata_value: str,
) -> str | None:
    """Resolve one entity ID for a specific metadata key/value match.

    Returns None when there is no match or when the match is ambiguous.
    """
    matches = [
        entry
        for entry in GROUP_REGISTRY.get_for_area_policy(area_id, policy_id)
        if _metadata_matches(
            entry,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
        )
    ]
    if len(matches) != 1:
        return None

    entity_registry = er.async_get(hass)
    return entity_registry.async_get_entity_id(
        domain,
        DOMAIN,
        matches[0].definition.group_id,
    )


def resolve_group_member_entity_id_by_metadata(
    *,
    area_id: str,
    policy_id: str,
    metadata_key: str,
    metadata_value: str,
    member_index: int = 0,
) -> str | None:
    """Resolve one member from a specific metadata key/value group match."""
    matches = [
        entry
        for entry in GROUP_REGISTRY.get_for_area_policy(area_id, policy_id)
        if _metadata_matches(
            entry,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
        )
    ]
    if len(matches) != 1:
        return None

    members = matches[0].definition.members
    if member_index < 0 or member_index >= len(members):
        return None
    return members[member_index]
