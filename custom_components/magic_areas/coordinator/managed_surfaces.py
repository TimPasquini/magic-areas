"""Reconcile Magic Areas-managed Home Assistant surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.core.runtime_model import (
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
        entity_registry.async_update_entity(
            entry.entity_id,
            area_id=surface.area_id,
            device_id=device_id,
            device_class=surface.device_class,
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
            entry = next(
                current_entry
                for current_entry in hass.config_entries.async_entries(surface.domain)
                if current_entry.unique_id == unique_id
            )
            _apply_surface_registry_metadata(
                hass=hass,
                owner_entry_id=owner_entry_id,
                helper_entry=entry,
                surface=surface,
            )
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
        _apply_surface_registry_metadata(
            hass=hass,
            owner_entry_id=owner_entry_id,
            helper_entry=entry,
            surface=surface,
        )

    for unique_id, entry in current_by_unique_id.items():
        if unique_id not in desired_by_unique_id:
            await hass.config_entries.async_remove(entry.entry_id)


__all__ = [
    "async_reconcile_config_entry_helpers",
    "async_reconcile_managed_surfaces",
]
