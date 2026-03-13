"""Runtime helpers for resolving control-group targets and listeners."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import Enum
from typing import Protocol

from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import entity_registry as entity_registry_module
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.const import ATTR_STATES
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model import (
    GroupRegistryView,
    RegisteredControlGroupView,
)
from custom_components.magic_areas.core.runtime_model import (
    build_presence_tracking_unique_id,
)
from custom_components.magic_areas.enums import MagicAreasEvents


class AreaStateHandler(Protocol):
    """Callable contract for area-state dispatcher callbacks."""

    def __call__(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> object:
        """Handle one area-state event payload."""
        ...


class GroupStateHandler(Protocol):
    """Callable contract for group state-change callbacks."""

    def __call__(self, event: Event[EventStateChangedData]) -> object:
        """Handle one group state-change event."""
        ...


def _metadata_matches(
    entry: RegisteredControlGroupView,
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
    group_registry: GroupRegistryView,
    area_id: str,
    policy_id: str,
    domain: str,
) -> str | None:
    """Resolve a control-group entity ID using registry-defined groups only."""
    entity_registry = er.async_get(hass)

    resolved_group = group_registry.get_first_for_area_policy(area_id, policy_id)
    if not resolved_group:
        return None

    return entity_registry.async_get_entity_id(
        domain,
        DOMAIN,
        resolved_group.definition.group_id,
    )


def resolve_group_member_entity_id(
    *,
    group_registry: GroupRegistryView,
    area_id: str,
    policy_id: str,
    member_index: int = 0,
) -> str | None:
    """Resolve a member entity ID from an area+policy control-group definition."""
    resolved_group = group_registry.get_first_for_area_policy(area_id, policy_id)
    if not resolved_group:
        return None

    members = resolved_group.definition.members
    if member_index < 0 or member_index >= len(members):
        return None

    return members[member_index]


def resolve_group_entity_ids_by_metadata(
    hass: HomeAssistant,
    *,
    group_registry: GroupRegistryView,
    area_id: str,
    policy_id: str,
    domain: str,
    metadata_key: str,
    metadata_filters: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve entity IDs keyed by a group metadata value."""
    entity_registry = er.async_get(hass)
    resolved: dict[str, str] = {}

    for entry in group_registry.get_for_area_policy(area_id, policy_id):
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


def resolve_group_entity_ids_for_metadata_values(
    hass: HomeAssistant,
    *,
    group_registry: GroupRegistryView,
    area_id: str,
    policy_id: str,
    domain: str,
    metadata_key: str,
    metadata_values: list[str],
    metadata_filters: Mapping[str, str] | None = None,
) -> list[str] | None:
    """Resolve entity IDs for ordered metadata values.

    Returns entity IDs in the same order as ``metadata_values`` and ignores
    values with no matching entity.
    """
    resolved_by_metadata = resolve_group_entity_ids_by_metadata(
        hass,
        group_registry=group_registry,
        area_id=area_id,
        policy_id=policy_id,
        domain=domain,
        metadata_key=metadata_key,
        metadata_filters=metadata_filters,
    )
    ordered_ids = [
        resolved_by_metadata[value]
        for value in metadata_values
        if value in resolved_by_metadata
    ]
    return ordered_ids or None


def resolve_group_entity_id_by_metadata(
    hass: HomeAssistant,
    *,
    group_registry: GroupRegistryView,
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
        for entry in group_registry.get_for_area_policy(area_id, policy_id)
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
    group_registry: GroupRegistryView,
    area_id: str,
    policy_id: str,
    metadata_key: str,
    metadata_value: str,
    member_index: int = 0,
) -> str | None:
    """Resolve one member from a specific metadata key/value group match."""
    matches = [
        entry
        for entry in group_registry.get_for_area_policy(area_id, policy_id)
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


def register_area_and_group_state_listeners(
    *,
    hass: HomeAssistant,
    track_listener: Callable[[Callable[[], None], str], None],
    area_state_handler: AreaStateHandler,
    group_entity_id: str,
    group_state_handler: GroupStateHandler,
    area_signal: str = str(MagicAreasEvents.AREA_STATE_CHANGED),
) -> None:
    """Register canonical area-state + group-state listeners for a group entity."""
    track_listener(
        async_dispatcher_connect(hass, area_signal, area_state_handler),
        "area_state_dispatcher",
    )
    track_listener(
        async_track_state_change_event(hass, [group_entity_id], group_state_handler),
        "group_state_change",
    )


def read_area_presence_states(hass: HomeAssistant, area_id: str) -> list[str]:
    """Read current area states from the presence-tracking binary sensor."""
    entity_registry = entity_registry_module.async_get(hass)
    presence_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        build_presence_tracking_unique_id(area_id=area_id),
    )
    if not presence_entity_id:
        return []

    state = hass.states.get(presence_entity_id)
    if not state or ATTR_STATES not in state.attributes:
        return []

    return [
        str(s.value) if isinstance(s, Enum) else str(s)
        for s in state.attributes[ATTR_STATES]
    ]


def resolve_area_presence_states(
    *,
    hass: HomeAssistant,
    area_id: str,
    cached_states: list[str] | None = None,
    require_occupied: bool = False,
) -> list[str]:
    """Resolve area states from cache with optional occupied-state validation."""
    if cached_states:
        if not require_occupied or AreaStates.OCCUPIED.value in cached_states:
            return list(cached_states)
    return read_area_presence_states(hass, area_id)
