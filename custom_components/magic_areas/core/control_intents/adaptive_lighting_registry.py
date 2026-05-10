"""HA registry binding for Adaptive Lighting coordination contracts."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr

from custom_components.magic_areas.core.control_intents.adaptive_lighting import (
    AdaptiveLightingSwitchCandidate,
    AdaptiveLightingSwitchSet,
    switch_set_from_discovery_candidates,
    switch_sets_from_discovery_candidates,
)


def switch_set_from_hass_registry(
    hass: HomeAssistant,
    *,
    area_id: str,
    role: str | None = None,
    required_label_ids: Iterable[str] = (),
    required_label_names: Iterable[str] = (),
) -> AdaptiveLightingSwitchSet | None:
    """Resolve one Adaptive Lighting switch set from HA entity/label registries."""
    entity_registry = er.async_get(hass)
    label_registry = lr.async_get(hass)
    resolved_label_ids = _resolve_required_label_ids(
        label_registry,
        required_label_ids=required_label_ids,
        required_label_names=required_label_names,
    )
    if required_label_names and not resolved_label_ids:
        return None

    candidates = [
        _candidate_from_registry_entry(label_registry, entry)
        for entry in _candidate_entries(
            entity_registry,
            area_id=area_id,
            required_label_ids=resolved_label_ids,
        )
    ]
    return switch_set_from_discovery_candidates(
        area_id=area_id,
        role=role,
        candidates=candidates,
        required_label_ids=resolved_label_ids,
    )


def switch_sets_from_hass_registry(
    hass: HomeAssistant,
    *,
    area_id: str,
    required_label_ids: Iterable[str] = (),
    required_label_names: Iterable[str] = (),
) -> tuple[AdaptiveLightingSwitchSet, ...]:
    """Return all complete Adaptive Lighting switch sets matching an HA area/label scope."""
    entity_registry = er.async_get(hass)
    label_registry = lr.async_get(hass)
    resolved_label_ids = _resolve_required_label_ids(
        label_registry,
        required_label_ids=required_label_ids,
        required_label_names=required_label_names,
    )
    if required_label_names and not resolved_label_ids:
        return ()

    candidates = [
        _candidate_from_registry_entry(label_registry, entry)
        for entry in _candidate_entries(
            entity_registry,
            area_id=area_id,
            required_label_ids=resolved_label_ids,
        )
    ]
    return switch_sets_from_discovery_candidates(
        area_id=area_id,
        candidates=candidates,
        required_label_ids=resolved_label_ids,
    )


def _candidate_entries(
    entity_registry: er.EntityRegistry,
    *,
    area_id: str,
    required_label_ids: frozenset[str],
) -> tuple[er.RegistryEntry, ...]:
    """Return registry entries worth considering for AL switch discovery."""
    if required_label_ids:
        entries_by_entity_id = {
            entry.entity_id: entry
            for label_id in required_label_ids
            for entry in er.async_entries_for_label(entity_registry, label_id)
        }
        return tuple(entries_by_entity_id.values())
    return tuple(er.async_entries_for_area(entity_registry, area_id))


def _candidate_from_registry_entry(
    label_registry: lr.LabelRegistry,
    entry: er.RegistryEntry,
) -> AdaptiveLightingSwitchCandidate:
    """Convert an HA registry entry into the pure AL candidate shape."""
    label_ids = frozenset(entry.labels)
    label_names = frozenset(
        label.name
        for label_id in label_ids
        if (label := label_registry.async_get_label(label_id)) is not None
    )
    return AdaptiveLightingSwitchCandidate(
        entity_id=entry.entity_id,
        area_id=entry.area_id,
        label_ids=label_ids,
        label_names=label_names,
    )


def _resolve_required_label_ids(
    label_registry: lr.LabelRegistry,
    *,
    required_label_ids: Iterable[str],
    required_label_names: Iterable[str],
) -> frozenset[str]:
    """Resolve explicit IDs plus names into the label IDs stored on registry entries."""
    resolved = set(required_label_ids)
    for label_name in required_label_names:
        label = label_registry.async_get_label_by_name(label_name)
        if label is None:
            return frozenset()
        resolved.add(label.label_id)
    return frozenset(resolved)


__all__ = ["switch_set_from_hass_registry", "switch_sets_from_hass_registry"]
