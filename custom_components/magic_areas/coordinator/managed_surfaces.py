"""Reconcile Magic Areas-managed Home Assistant surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.runtime_model.managed_surfaces import (
    ConfigEntryHelperSurface,
    ManagedSurface,
    ManagedSurfaceOptionValue,
)


def _is_managed_by_entry(entry: ConfigEntry[object], owner_prefix: str) -> bool:
    """Return whether config entry is owned by this Magic Areas entry."""
    return bool(entry.unique_id and entry.unique_id.startswith(owner_prefix))


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


async def async_reconcile_config_entry_helpers(
    *,
    hass: HomeAssistant,
    owner_entry_id: str,
    desired_surfaces: list[ConfigEntryHelperSurface],
) -> None:
    """Create, update, and remove owned config-entry-backed helpers."""
    owner_prefix = f"magic_areas:{owner_entry_id}:"
    desired_by_unique_id = {surface.unique_id: surface for surface in desired_surfaces}
    managed_entries = [
        entry
        for entry in hass.config_entries.async_entries()
        if _is_managed_by_entry(entry, owner_prefix)
    ]
    current_by_unique_id = {
        entry.unique_id: entry for entry in managed_entries if entry.unique_id
    }

    for unique_id, surface in desired_by_unique_id.items():
        if (entry := current_by_unique_id.get(unique_id)) is None:
            await hass.config_entries.async_add(_build_config_entry(surface))
            continue

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

    for unique_id, entry in current_by_unique_id.items():
        if unique_id not in desired_by_unique_id:
            await hass.config_entries.async_remove(entry.entry_id)


__all__ = [
    "async_reconcile_config_entry_helpers",
    "async_reconcile_managed_surfaces",
]
