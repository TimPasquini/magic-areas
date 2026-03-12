"""Runtime helpers for light-group entity adapters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import STATE_ON
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.command_echo import CommandEchoState
from custom_components.magic_areas.core.group_contracts import (
    ControlGroupPolicyId,
    build_light_group_id,
)
from custom_components.magic_areas.core.group_metadata import GroupMetadataKey
from custom_components.magic_areas.core.control_group_runtime import (
    resolve_group_entity_ids_by_metadata,
)


def resolve_child_group_ids(
    hass: Any,
    area_id: str,
    child_categories: list[str],
) -> list[str] | None:
    """Resolve child light group entity ids for the ALL category group."""
    resolved_ids: list[str] = []
    category_entity_ids = resolve_group_entity_ids_by_metadata(
        hass,
        area_id=area_id,
        policy_id=str(ControlGroupPolicyId.LIGHT_GROUPS),
        domain=LIGHT_DOMAIN,
        metadata_key=str(GroupMetadataKey.CATEGORY),
    )
    for category in child_categories:
        entity_id = category_entity_ids.get(category)
        if entity_id:
            resolved_ids.append(entity_id)

    if resolved_ids:
        return resolved_ids

    registry = er.async_get(hass)
    for category in child_categories:
        child_uid = build_light_group_id(area_id=area_id, category=category)
        child_entity_id = registry.async_get_entity_id(
            LIGHT_DOMAIN, DOMAIN, child_uid
        )
        if child_entity_id:
            resolved_ids.append(child_entity_id)

    return resolved_ids or None


def restore_group_state(group: Any, last_state: Any | None) -> None:
    """Restore basic on/off + control state from last HA state object."""
    if not last_state:
        group._attr_is_on = False
        return

    group.logger.debug(
        "%s: State restored [state=%s]", group.name, last_state.state
    )
    group._attr_is_on = last_state.state == STATE_ON

    if "controlling" in last_state.attributes:
        controlling = last_state.attributes["controlling"]
        group._set_echo_state(
            CommandEchoState(
                owner_id=group.unique_id,
                controlling=controlling,
                awaiting_echo=False,
            )
        )


def is_group_control_enabled(group: Any) -> bool:
    """Check if light-control switch enables automatic group control."""
    if not group._coordinator.data:
        return True

    entity_id = group._coordinator.data.entity_references.light_control_switch
    if not entity_id:
        return True

    switch_entity = group.hass.states.get(entity_id)
    if not switch_entity:
        return True

    return switch_entity.state.lower() == STATE_ON
