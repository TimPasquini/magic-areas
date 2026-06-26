"""HA-aware target resolution for control intents."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.util import slugify

from custom_components.magic_areas.core.control_intents.models import (
    ControlTargetKind,
    ControlTargetPrecision,
    ControlTargetSource,
    RoleTarget,
)
from custom_components.magic_areas.core.managed_surface_registry import (
    resolve_managed_surface_entity_id,
)

CUSTOM_CONTROL_LABEL_PREFIX = "ma:control:"


def resolve_role_target(
    hass: HomeAssistant,
    *,
    area_id: str,
    domain: str,
    role: str,
    area_entity_ids: Iterable[str],
    label_name: str | None = None,
    allow_broad_label_target: bool = False,
    helper_unique_id: str | None = None,
    helper_entity_domain: str | None = None,
    helper_config_entry_domain: str | None = None,
    fallback_entity_ids: Iterable[str] = (),
    fallback_source: ControlTargetSource = ControlTargetSource.GROUP_REGISTRY,
    compatibility_entity_id: str | None = None,
) -> RoleTarget:
    """Resolve an executable target record without making policy decisions.

    The resolver starts from the Magic Areas area/domain entity universe supplied by
    the caller. Labels are applied inside that boundary instead of queried as a
    global control surface.
    """
    area_entities = _ordered_domain_entities(area_entity_ids, domain)
    entity_registry = er.async_get(hass)

    if helper_unique_id is not None:
        helper_entity_id = resolve_managed_surface_entity_id(
            hass,
            entity_registry,
            unique_id=helper_unique_id,
            entity_domain=helper_entity_domain or domain,
            config_entry_domain=helper_config_entry_domain,
        )
        if helper_entity_id is not None:
            return RoleTarget(
                role=role,
                domain=domain,
                area_id=area_id,
                kind=ControlTargetKind.HELPER_ENTITY,
                precision=ControlTargetPrecision.EXACT,
                source=ControlTargetSource.MANAGED_HELPER,
                helper_unique_id=helper_unique_id,
                helper_entity_id=helper_entity_id,
                resolution_path=("managed_helper",),
            )

    if label_name is not None:
        label_id = _resolve_label_id(hass, label_name)
        if label_id is not None and allow_broad_label_target:
            return RoleTarget(
                role=role,
                domain=domain,
                area_id=area_id,
                kind=ControlTargetKind.LABEL,
                precision=ControlTargetPrecision.BROAD,
                source=ControlTargetSource.RECONCILED_LABEL,
                label_name=label_name,
                label_id=label_id,
                resolution_path=("label",),
            )
        if label_id is not None:
            entity_ids = _resolve_label_entity_ids(
                entity_registry,
                label_id=label_id,
                area_entity_ids=area_entities,
                domain=domain,
            )
            if entity_ids:
                return RoleTarget(
                    role=role,
                    domain=domain,
                    area_id=area_id,
                    kind=ControlTargetKind.ENTITY_SUBSET,
                    precision=ControlTargetPrecision.FILTERED,
                    source=ControlTargetSource.RECONCILED_LABEL,
                    label_name=label_name,
                    label_id=label_id,
                    entity_ids=entity_ids,
                    resolution_path=("area_domain_boundary", "label"),
                    fallback_reason="ha_label_intersection_not_supported",
                )

    fallback_entities = _filter_entity_ids(
        fallback_entity_ids,
        allowed_entity_ids=area_entities,
        domain=domain,
    )
    if fallback_entities:
        return RoleTarget(
            role=role,
            domain=domain,
            area_id=area_id,
            kind=ControlTargetKind.ENTITY_SUBSET,
            precision=ControlTargetPrecision.FILTERED,
            source=fallback_source,
            entity_ids=fallback_entities,
            resolution_path=("compatibility_members",),
            fallback_reason="label_or_helper_target_unavailable",
        )

    if compatibility_entity_id is not None:
        return RoleTarget(
            role=role,
            domain=domain,
            area_id=area_id,
            kind=ControlTargetKind.COMPATIBILITY_ENTITY,
            precision=ControlTargetPrecision.COMPATIBILITY,
            source=ControlTargetSource.POLICY_ENTITY,
            compatibility_entity_id=compatibility_entity_id,
            resolution_path=("policy_entity",),
            fallback_reason="label_helper_and_member_targets_unavailable",
        )

    return RoleTarget(
        role=role,
        domain=domain,
        area_id=area_id,
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.ENTITY_SUBSET,
        entity_ids=(),
        resolution_path=("unresolved",),
        fallback_reason="no_target_available",
    )


def custom_control_label_name(group_id: str) -> str:
    """Return the reconciled HA label name for a custom control group."""
    return f"{CUSTOM_CONTROL_LABEL_PREFIX}{_custom_control_label_suffix(group_id)}"


def resolve_custom_control_target(
    hass: HomeAssistant,
    *,
    area_id: str,
    domain: str,
    group_id: str,
    area_entity_ids: Iterable[str],
    fallback_entity_ids: Iterable[str] = (),
    allow_broad_label_target: bool = False,
) -> RoleTarget:
    """Resolve a custom control group target through reconciled labels first."""
    return resolve_role_target(
        hass,
        area_id=area_id,
        domain=domain,
        role=group_id,
        area_entity_ids=area_entity_ids,
        label_name=custom_control_label_name(group_id),
        allow_broad_label_target=allow_broad_label_target,
        fallback_entity_ids=fallback_entity_ids,
        fallback_source=ControlTargetSource.CONFIG_RECONCILIATION,
    )


def _custom_control_label_suffix(group_id: str) -> str:
    """Return stable label suffix for a custom control group ID."""
    label_source = group_id.removeprefix("control.")
    label_suffix = slugify(label_source).replace("_", "-")
    return label_suffix or "custom"


def _resolve_label_id(hass: HomeAssistant, label_name: str) -> str | None:
    """Resolve a label name to an HA label ID."""
    label = lr.async_get(hass).async_get_label_by_name(label_name)
    if label is None:
        return None
    return label.label_id


def _resolve_label_entity_ids(
    entity_registry: er.EntityRegistry,
    *,
    label_id: str,
    area_entity_ids: tuple[str, ...],
    domain: str,
) -> tuple[str, ...]:
    """Resolve label members inside the caller-provided area/domain boundary."""
    labelled_entity_ids = {
        entry.entity_id
        for entry in er.async_entries_for_label(entity_registry, label_id)
        if entry.domain == domain
    }
    return tuple(
        entity_id for entity_id in area_entity_ids if entity_id in labelled_entity_ids
    )


def _ordered_domain_entities(entity_ids: Iterable[str], domain: str) -> tuple[str, ...]:
    """Return stable, de-duplicated entity IDs for a domain."""
    seen: set[str] = set()
    ordered: list[str] = []
    for entity_id in entity_ids:
        if entity_id in seen or not entity_id.startswith(f"{domain}."):
            continue
        seen.add(entity_id)
        ordered.append(entity_id)
    return tuple(ordered)


def _filter_entity_ids(
    entity_ids: Iterable[str],
    *,
    allowed_entity_ids: tuple[str, ...],
    domain: str,
) -> tuple[str, ...]:
    """Filter fallback members to the area/domain boundary."""
    requested = set(_ordered_domain_entities(entity_ids, domain))
    return tuple(
        entity_id for entity_id in allowed_entity_ids if entity_id in requested
    )


__all__ = [
    "custom_control_label_name",
    "resolve_custom_control_target",
    "resolve_role_target",
]
