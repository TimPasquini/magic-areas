"""Home Assistant registry helpers for Magic Areas-managed surfaces."""

from __future__ import annotations

from collections.abc import Iterator

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.core.runtime_model import (
    is_managed_surface_unique_id,
)


def is_managed_surface_config_entry(
    entry: ConfigEntry[object],
    *,
    owner_entry_id: str | None = None,
) -> bool:
    """Return whether a config entry is owned by Magic Areas managed surfaces."""
    return is_managed_surface_unique_id(
        entry.unique_id,
        owner_entry_id=owner_entry_id,
    )


def iter_managed_surface_config_entries(
    hass: HomeAssistant,
    *,
    owner_entry_id: str | None = None,
    domain: str | None = None,
    loaded_only: bool = False,
) -> Iterator[ConfigEntry[object]]:
    """Yield config entries for Magic Areas-managed HA surfaces."""
    for entry in hass.config_entries.async_entries(domain):
        if loaded_only and entry.state != ConfigEntryState.LOADED:
            continue
        if is_managed_surface_config_entry(entry, owner_entry_id=owner_entry_id):
            yield entry


def iter_managed_surface_entity_entries(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    *,
    owner_entry_id: str | None = None,
    config_entry_domain: str | None = None,
    entity_domain: str | None = None,
    loaded_only: bool = False,
) -> Iterator[er.RegistryEntry]:
    """Yield entity registry entries belonging to managed-surface config entries."""
    for entry in iter_managed_surface_config_entries(
        hass,
        owner_entry_id=owner_entry_id,
        domain=config_entry_domain,
        loaded_only=loaded_only,
    ):
        for registry_entry in er.async_entries_for_config_entry(
            entity_registry,
            entry.entry_id,
        ):
            if entity_domain is not None and registry_entry.domain != entity_domain:
                continue
            yield registry_entry


def resolve_managed_surface_entity_id(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    *,
    unique_id: str,
    entity_domain: str,
    config_entry_domain: str | None = None,
) -> str | None:
    """Resolve the entity ID for a managed surface by config-entry ownership ID."""
    for entry in iter_managed_surface_config_entries(
        hass,
        domain=config_entry_domain,
    ):
        if entry.unique_id != unique_id:
            continue
        for registry_entry in er.async_entries_for_config_entry(
            entity_registry,
            entry.entry_id,
        ):
            if registry_entry.domain == entity_domain:
                return registry_entry.entity_id
    return None


__all__ = [
    "is_managed_surface_config_entry",
    "iter_managed_surface_config_entries",
    "iter_managed_surface_entity_entries",
    "resolve_managed_surface_entity_id",
]
