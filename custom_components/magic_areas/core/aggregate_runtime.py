"""Runtime helpers for canonical aggregate definitions."""

from __future__ import annotations

from homeassistant.helpers import entity_registry as er
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.aggregate_policy import AggregateDefinition
from custom_components.magic_areas.core.control_group import ControlGroupDefinition
from custom_components.magic_areas.core.group_registry import GROUP_REGISTRY
from custom_components.magic_areas.const import DOMAIN

AGGREGATE_POLICY_ID = "aggregate"


def aggregate_group_id(*, area_id: str, device_class: str) -> str:
    """Return a stable aggregate group ID for an area/device-class pair."""
    return f"aggregates_{area_id}_aggregate_{device_class}"


def register_aggregate_definitions(
    *,
    area_id: str,
    definitions: list[AggregateDefinition],
) -> None:
    """Register aggregate definitions as area defaults in the group registry."""
    group_definitions: list[ControlGroupDefinition] = []
    for definition in definitions:
        group_definitions.append(
            ControlGroupDefinition(
                group_id=aggregate_group_id(
                    area_id=area_id,
                    device_class=definition.device_class,
                ),
                members=definition.entity_ids,
                policy_id=AGGREGATE_POLICY_ID,
                metadata={
                    "aggregate_domain": definition.domain,
                    "aggregate_device_class": definition.device_class,
                    "aggregate_kind": definition.kind.value,
                },
            )
        )

    GROUP_REGISTRY.register_area_defaults(
        area_id,
        group_definitions,
        policy_id=AGGREGATE_POLICY_ID,
    )


def resolve_aggregate_entity_ids_by_device_class(
    hass: HomeAssistant,
    *,
    area_id: str,
    domain: str,
) -> dict[str, str]:
    """Resolve aggregate entity IDs keyed by device-class for a domain."""
    entity_registry = er.async_get(hass)
    resolved: dict[str, str] = {}

    for entry in GROUP_REGISTRY.get_for_area_policy(area_id, AGGREGATE_POLICY_ID):
        if entry.definition.metadata.get("aggregate_domain") != domain:
            continue
        device_class = entry.definition.metadata.get("aggregate_device_class")
        if not isinstance(device_class, str):
            continue
        entity_id = entity_registry.async_get_entity_id(
            domain,
            DOMAIN,
            entry.definition.group_id,
        )
        if entity_id:
            resolved[device_class] = entity_id

    return resolved


def resolve_aggregate_entity_id(
    hass: HomeAssistant,
    *,
    area_id: str,
    domain: str,
    device_class: str,
) -> str | None:
    """Resolve one aggregate entity ID from area/domain/device-class metadata."""
    return resolve_aggregate_entity_ids_by_device_class(
        hass,
        area_id=area_id,
        domain=domain,
    ).get(device_class)
