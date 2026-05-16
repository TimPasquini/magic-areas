"""Reconcile Magic Areas-managed Home Assistant surfaces."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import label_registry as lr

from custom_components.magic_areas.const import DOMAIN, MANAGED_LABEL_SURFACES_DATA_KEY
from custom_components.magic_areas.core.managed_surface_registry import (
    iter_managed_surface_config_entries,
)
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    LabelSurface,
    ManagedSurface,
    ManagedSurfaceOptionValue,
)

_LOGGER = logging.getLogger(__name__)

_REPAIR_TRANSLATION_KEY = "managed_surface_reconciliation_failed"
_EXPECTED_RECONCILIATION_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
    StopIteration,
    HomeAssistantError,
)


def _options_equal(
    current: Mapping[str, object],
    desired: Mapping[str, ManagedSurfaceOptionValue],
) -> bool:
    """Return whether helper options are equivalent."""
    return current == desired


def _build_config_entry(surface: ConfigEntryHelperSurface) -> ConfigEntry[object]:
    """Build a config entry for a desired helper surface."""
    return ConfigEntry(
        data={},
        discovery_keys=MappingProxyType({}),
        domain=surface.domain,
        minor_version=1,
        options=surface.options,
        source=SOURCE_IMPORT,
        subentries_data=(),
        title=surface.title,
        unique_id=surface.unique_id,
        version=1,
    )


def _surface_repair_issue_id(unique_id: str) -> str:
    """Build a stable Repairs issue ID for a managed surface."""
    digest = hashlib.sha1(unique_id.encode(), usedforsecurity=False).hexdigest()[:12]
    return f"managed_surface_reconciliation_{digest}"


def _create_surface_repair_issue(
    *,
    hass: HomeAssistant,
    surface_unique_id: str,
    surface_domain: str,
    surface_title: str,
    action: str,
    error: Exception,
) -> None:
    """Create or update a Repairs issue for a managed-surface failure."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _surface_repair_issue_id(surface_unique_id),
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=_REPAIR_TRANSLATION_KEY,
        translation_placeholders={
            "action": action,
            "domain": surface_domain,
            "surface": surface_title,
            "error": f"{type(error).__name__}: {error}",
        },
    )


def _delete_surface_repair_issue(
    *,
    hass: HomeAssistant,
    surface_unique_id: str,
) -> None:
    """Clear a Repairs issue for a successfully reconciled managed surface."""
    ir.async_delete_issue(
        hass,
        DOMAIN,
        _surface_repair_issue_id(surface_unique_id),
    )


def _get_or_create_surface_device(
    *,
    hass: HomeAssistant,
    owner_entry_id: str,
    surface: ConfigEntryHelperSurface,
) -> str | None:
    """Return device ID for the helper surface's Magic Areas device."""
    if surface.device_identifier is None:
        return None

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=owner_entry_id,
        identifiers={surface.device_identifier},
        manufacturer="Magic Areas",
        model="Magic Area",
        name=surface.device_name,
        suggested_area=surface.area_id,
    )
    if surface.area_id and device.area_id != surface.area_id:
        updated_device = device_registry.async_update_device(
            device.id,
            area_id=surface.area_id,
        )
        return updated_device.id if updated_device else device.id
    return device.id


def _apply_surface_registry_metadata(
    *,
    hass: HomeAssistant,
    owner_entry_id: str,
    helper_entry: ConfigEntry[object],
    surface: ConfigEntryHelperSurface,
) -> None:
    """Attach helper entities to the correct HA area and Magic Areas device."""
    if surface.area_id is None and surface.device_identifier is None:
        return

    device_id = _get_or_create_surface_device(
        hass=hass,
        owner_entry_id=owner_entry_id,
        surface=surface,
    )
    entity_registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(
        entity_registry,
        helper_entry.entry_id,
    ):
        updates: dict[str, object] = {
            "area_id": surface.area_id,
            "device_id": device_id,
            "device_class": surface.device_class,
        }
        if surface.entity_name is not None:
            updates["name"] = surface.entity_name
        entity_registry.async_update_entity(entry.entity_id, **updates)


async def async_reconcile_managed_surfaces(
    *,
    hass: HomeAssistant,
    owner_entry_id: str,
    desired_surfaces: list[ManagedSurface],
) -> None:
    """Reconcile Magic Areas-managed HA surfaces for one config entry."""
    await async_reconcile_config_entry_helpers(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            surface
            for surface in desired_surfaces
            if isinstance(surface, ConfigEntryHelperSurface)
        ],
    )
    async_reconcile_label_surfaces(
        hass=hass,
        owner_entry_id=owner_entry_id,
        desired_surfaces=[
            surface for surface in desired_surfaces if isinstance(surface, LabelSurface)
        ],
    )


def _find_or_create_label(
    *,
    label_registry: lr.LabelRegistry,
    surface: LabelSurface,
) -> lr.LabelEntry:
    """Return an existing label by name or create it."""
    label = label_registry.async_get_label_by_name(surface.name)
    if label is None:
        return label_registry.async_create(
            surface.name,
            color=surface.color,
            icon=surface.icon,
            description=surface.description,
        )

    if (
        label.color != surface.color
        or label.icon != surface.icon
        or label.description != surface.description
    ):
        return label_registry.async_update(
            label.label_id,
            color=surface.color,
            icon=surface.icon,
            description=surface.description,
        )
    return label


def _set_entity_label_membership(
    *,
    entity_registry: er.EntityRegistry,
    entity_id: str,
    label_id: str,
    assigned: bool,
) -> None:
    """Set one label membership while preserving all unrelated labels."""
    entry = entity_registry.async_get(entity_id)
    if entry is None:
        return

    labels = set(entry.labels)
    if assigned:
        if label_id in labels:
            return
        labels.add(label_id)
    else:
        if label_id not in labels:
            return
        labels.remove(label_id)
    entity_registry.async_update_entity(entity_id, labels=labels)


def async_reconcile_label_surfaces(
    *,
    hass: HomeAssistant,
    desired_surfaces: list[LabelSurface],
    owner_entry_id: str | None = None,
) -> None:
    """Create/update labels and reconcile scoped entity label membership."""
    label_registry = lr.async_get(hass)
    entity_registry = er.async_get(hass)
    owner_entry = (
        hass.config_entries.async_get_entry(owner_entry_id)
        if owner_entry_id is not None
        else None
    )
    previous_owner_labels = _managed_label_snapshot(owner_entry)
    desired_by_name = {surface.name: surface for surface in desired_surfaces}
    surfaces_to_reconcile = list(desired_surfaces)
    surfaces_to_reconcile.extend(
        LabelSurface(
            name=label_name,
            entity_ids=(),
            prune_entity_ids=entity_ids,
        )
        for label_name, entity_ids in previous_owner_labels.items()
        if label_name not in desired_by_name
    )

    for surface in surfaces_to_reconcile:
        label = _find_or_create_label(
            label_registry=label_registry,
            surface=surface,
        )
        desired_entity_ids = set(surface.entity_ids)
        previous_entity_ids = set(previous_owner_labels.get(surface.name, ()))
        prune_entity_ids = (
            set(surface.prune_entity_ids) | previous_entity_ids
        ) or desired_entity_ids

        for entity_id in desired_entity_ids:
            _set_entity_label_membership(
                entity_registry=entity_registry,
                entity_id=entity_id,
                label_id=label.label_id,
                assigned=True,
            )

        for entity_id in prune_entity_ids - desired_entity_ids:
            _set_entity_label_membership(
                entity_registry=entity_registry,
                entity_id=entity_id,
                label_id=label.label_id,
                assigned=False,
            )

        if not er.async_entries_for_label(entity_registry, label.label_id):
            label_registry.async_delete(label.label_id)

    _store_managed_label_snapshot(
        hass=hass,
        owner_entry=owner_entry,
        desired_surfaces=desired_surfaces,
    )


def _managed_label_snapshot(
    owner_entry: ConfigEntry[object] | None,
) -> dict[str, tuple[str, ...]]:
    """Return previously reconciled labels owned by this config entry."""
    if owner_entry is None:
        return {}

    raw_snapshot = owner_entry.data.get(MANAGED_LABEL_SURFACES_DATA_KEY, {})
    if not isinstance(raw_snapshot, Mapping):
        return {}

    snapshot: dict[str, tuple[str, ...]] = {}
    for label_name, entity_ids in raw_snapshot.items():
        if not isinstance(label_name, str) or not isinstance(entity_ids, list):
            continue
        snapshot[label_name] = tuple(
            entity_id for entity_id in entity_ids if isinstance(entity_id, str)
        )
    return snapshot


def _store_managed_label_snapshot(
    *,
    hass: HomeAssistant,
    owner_entry: ConfigEntry[object] | None,
    desired_surfaces: list[LabelSurface],
) -> None:
    """Persist the labels this owner last intended so deletions can prune them."""
    if owner_entry is None:
        return

    next_snapshot = {
        surface.name: sorted(set(surface.entity_ids)) for surface in desired_surfaces
    }
    if owner_entry.data.get(MANAGED_LABEL_SURFACES_DATA_KEY, {}) == next_snapshot:
        return

    hass.config_entries.async_update_entry(
        owner_entry,
        data={
            **owner_entry.data,
            MANAGED_LABEL_SURFACES_DATA_KEY: next_snapshot,
        },
    )


async def async_reconcile_config_entry_helpers(
    *,
    hass: HomeAssistant,
    owner_entry_id: str,
    desired_surfaces: Sequence[ConfigEntryHelperSurface],
) -> None:
    """Create, update, and remove owned config-entry-backed helpers."""
    desired_by_unique_id = {surface.unique_id: surface for surface in desired_surfaces}
    managed_entries = list(
        iter_managed_surface_config_entries(hass, owner_entry_id=owner_entry_id)
    )
    current_by_unique_id = {
        entry.unique_id: entry for entry in managed_entries if entry.unique_id
    }

    for unique_id, surface in desired_by_unique_id.items():
        action = "create"
        try:
            if (entry := current_by_unique_id.get(unique_id)) is None:
                await hass.config_entries.async_add(_build_config_entry(surface))
                entry = next(
                    current_entry
                    for current_entry in hass.config_entries.async_entries(
                        surface.domain
                    )
                    if current_entry.unique_id == unique_id
                )
                _apply_surface_registry_metadata(
                    hass=hass,
                    owner_entry_id=owner_entry_id,
                    helper_entry=entry,
                    surface=surface,
                )
                _delete_surface_repair_issue(
                    hass=hass,
                    surface_unique_id=unique_id,
                )
                continue

            action = "update"
            changed = False
            if entry.title != surface.title:
                changed = hass.config_entries.async_update_entry(
                    entry,
                    title=surface.title,
                )
            if not _options_equal(dict(entry.options), surface.options):
                changed = (
                    hass.config_entries.async_update_entry(
                        entry,
                        options=surface.options,
                    )
                    or changed
                )
            if changed and entry.state is ConfigEntryState.LOADED:
                await hass.config_entries.async_reload(entry.entry_id)
            _apply_surface_registry_metadata(
                hass=hass,
                owner_entry_id=owner_entry_id,
                helper_entry=entry,
                surface=surface,
            )
            _delete_surface_repair_issue(
                hass=hass,
                surface_unique_id=unique_id,
            )
        except _EXPECTED_RECONCILIATION_ERRORS as err:
            _LOGGER.exception(
                "%s: Failed to %s managed %s helper surface '%s'",
                owner_entry_id,
                action,
                surface.domain,
                surface.title,
            )
            _create_surface_repair_issue(
                hass=hass,
                surface_unique_id=unique_id,
                surface_domain=surface.domain,
                surface_title=surface.title,
                action=action,
                error=err,
            )

    for unique_id, entry in current_by_unique_id.items():
        if unique_id not in desired_by_unique_id:
            try:
                await hass.config_entries.async_remove(entry.entry_id)
                _delete_surface_repair_issue(
                    hass=hass,
                    surface_unique_id=unique_id,
                )
            except _EXPECTED_RECONCILIATION_ERRORS as err:
                _LOGGER.exception(
                    "%s: Failed to remove stale managed %s helper surface '%s'",
                    owner_entry_id,
                    entry.domain,
                    entry.title,
                )
                _create_surface_repair_issue(
                    hass=hass,
                    surface_unique_id=unique_id,
                    surface_domain=entry.domain,
                    surface_title=entry.title,
                    action="remove",
                    error=err,
                )


__all__ = [
    "async_reconcile_config_entry_helpers",
    "async_reconcile_label_surfaces",
    "async_reconcile_managed_surfaces",
]
