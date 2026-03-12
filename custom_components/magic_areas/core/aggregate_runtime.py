"""Runtime helpers for canonical aggregate definitions."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.aggregate_policy import AggregateDefinition
from custom_components.magic_areas.core.control_group import ControlGroupDefinition
from custom_components.magic_areas.core.group_contracts import (
    ControlGroupPolicyId,
    build_aggregate_group_id,
)
from custom_components.magic_areas.core.group_metadata import GroupMetadataKey
from custom_components.magic_areas.core.control_group_runtime import (
    resolve_group_entity_ids_by_metadata,
)
from custom_components.magic_areas.core.group_registry import GROUP_REGISTRY

AGGREGATE_POLICY_ID = ControlGroupPolicyId.AGGREGATE


def aggregate_group_id(*, area_id: str, device_class: str) -> str:
    """Return a stable aggregate group ID for an area/device-class pair."""
    return build_aggregate_group_id(area_id=area_id, device_class=device_class)


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
                    GroupMetadataKey.AGGREGATE_DOMAIN: definition.domain,
                    GroupMetadataKey.AGGREGATE_DEVICE_CLASS: definition.device_class,
                    GroupMetadataKey.AGGREGATE_KIND: definition.kind.value,
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
    domain_matches = resolve_group_entity_ids_by_metadata(
        hass,
        area_id=area_id,
        policy_id=str(AGGREGATE_POLICY_ID),
        domain=domain,
        metadata_key=str(GroupMetadataKey.AGGREGATE_DEVICE_CLASS),
        metadata_filters={str(GroupMetadataKey.AGGREGATE_DOMAIN): domain},
    )
    return domain_matches


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
