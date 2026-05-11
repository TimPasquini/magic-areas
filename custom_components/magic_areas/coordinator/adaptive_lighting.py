"""Reconcile Magic Areas-managed Adaptive Lighting configurations."""

from __future__ import annotations

from collections.abc import Iterable
import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.components import MAGIC_DEVICE_ID_PREFIX
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.control_intents import (
    ADAPTIVE_LIGHTING_DOMAIN,
    ExistingAdaptiveLightingConfigEntry,
    ManagedAdaptiveLightingConfig,
    ManagedAdaptiveLightingReconcileAction,
    ManagedAdaptiveLightingReconcileOperation,
    managed_adaptive_lighting_reconcile_plan,
)

_LOGGER = logging.getLogger(__name__)

_EXPECTED_RECONCILIATION_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
    StopIteration,
    HomeAssistantError,
)


def _project_entry(entry: ConfigEntry[object]) -> ExistingAdaptiveLightingConfigEntry:
    """Return the pure reconciler projection for an existing AL config entry."""
    return ExistingAdaptiveLightingConfigEntry(
        entry_id=entry.entry_id,
        unique_id=entry.unique_id,
        title=entry.title,
        data=entry.data,
        options=entry.options,
    )


def _build_config_entry(
    operation: ManagedAdaptiveLightingReconcileOperation,
) -> ConfigEntry[object]:
    """Build a new MA-owned Adaptive Lighting config entry."""
    if operation.desired_config is None or operation.data is None:
        raise ValueError("create operation requires desired config and data")
    return ConfigEntry(
        data=operation.data,
        discovery_keys=MappingProxyType({}),
        domain=ADAPTIVE_LIGHTING_DOMAIN,
        minor_version=1,
        options=operation.options or {},
        source=SOURCE_IMPORT,
        subentries_data=(),
        title=operation.desired_config.name,
        unique_id=operation.desired_config.name,
        version=1,
    )


def _find_entry_by_unique_id(
    hass: HomeAssistant,
    unique_id: str,
) -> ConfigEntry[object] | None:
    """Return an Adaptive Lighting config entry by unique ID."""
    for entry in hass.config_entries.async_entries(ADAPTIVE_LIGHTING_DOMAIN):
        if entry.unique_id == unique_id:
            return entry
    return None


def _get_or_create_area_device(
    *,
    hass: HomeAssistant,
    owner_entry_id: str,
    config: ManagedAdaptiveLightingConfig,
) -> str:
    """Return the Magic Areas device ID used for managed AL switches."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=owner_entry_id,
        identifiers={(DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{config.area_id}")},
        manufacturer="Magic Areas",
        model="Magic Area",
        name=config.area_name,
        suggested_area=config.area_id,
    )
    if device.area_id != config.area_id:
        updated = device_registry.async_update_device(
            device.id,
            area_id=config.area_id,
        )
        return updated.id if updated else device.id
    return device.id


def _apply_registry_metadata(
    *,
    hass: HomeAssistant,
    owner_entry_id: str | None,
    entry: ConfigEntry[object],
    config: ManagedAdaptiveLightingConfig,
) -> None:
    """Attach managed AL entities to the owning Magic Areas area/device."""
    entity_registry = er.async_get(hass)
    device_id = (
        _get_or_create_area_device(
            hass=hass,
            owner_entry_id=owner_entry_id,
            config=config,
        )
        if owner_entry_id is not None
        else None
    )
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry,
        entry.entry_id,
    ):
        entity_registry.async_update_entity(
            entity_entry.entity_id,
            area_id=config.area_id,
            device_id=device_id,
        )


async def _async_apply_managed_adaptive_lighting_operation(
    *,
    hass: HomeAssistant,
    owner_entry_id: str | None,
    operation: ManagedAdaptiveLightingReconcileOperation,
) -> None:
    """Apply one managed Adaptive Lighting config-entry reconciliation operation."""
    if operation.action is ManagedAdaptiveLightingReconcileAction.CREATE:
        await hass.config_entries.async_add(_build_config_entry(operation))
        if operation.desired_config is not None:
            entry = _find_entry_by_unique_id(hass, operation.desired_config.name)
            if entry is not None:
                _apply_registry_metadata(
                    hass=hass,
                    owner_entry_id=owner_entry_id,
                    entry=entry,
                    config=operation.desired_config,
                )
        return

    if operation.existing_entry is None:
        raise ValueError("update/delete operation requires an existing entry")

    entry = hass.config_entries.async_get_entry(operation.existing_entry.entry_id)
    if entry is None:
        return

    if operation.action is ManagedAdaptiveLightingReconcileAction.DELETE:
        await hass.config_entries.async_remove(entry.entry_id)
        return

    if operation.action is ManagedAdaptiveLightingReconcileAction.UPDATE:
        if (
            operation.desired_config is None
            or operation.data is None
            or operation.options is None
        ):
            raise ValueError(
                "update operation requires desired config, data, and options"
            )
        changed = hass.config_entries.async_update_entry(
            entry,
            data=operation.data,
            options=operation.options,
            title=operation.desired_config.name,
        )
        if changed and entry.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_reload(entry.entry_id)
        _apply_registry_metadata(
            hass=hass,
            owner_entry_id=owner_entry_id,
            entry=entry,
            config=operation.desired_config,
        )


async def async_reconcile_managed_adaptive_lighting(
    *,
    hass: HomeAssistant,
    area_id: str | None = None,
    owner_entry_id: str | None = None,
    desired_configs: Iterable[ManagedAdaptiveLightingConfig],
) -> None:
    """Create, update, and remove Magic Areas-managed Adaptive Lighting entries."""
    desired_config_tuple = tuple(desired_configs)
    operations = managed_adaptive_lighting_reconcile_plan(
        desired_configs=desired_config_tuple,
        existing_entries=[
            _project_entry(entry)
            for entry in hass.config_entries.async_entries(ADAPTIVE_LIGHTING_DOMAIN)
        ],
        area_id=area_id,
    )

    for operation in operations:
        try:
            await _async_apply_managed_adaptive_lighting_operation(
                hass=hass,
                owner_entry_id=owner_entry_id,
                operation=operation,
            )
        except _EXPECTED_RECONCILIATION_ERRORS:
            _LOGGER.exception(
                "Failed to %s managed Adaptive Lighting config '%s'",
                operation.action,
                (
                    operation.desired_config.name
                    if operation.desired_config
                    else operation.existing_entry.name
                    if operation.existing_entry
                    else "<unknown>"
                ),
            )

    for config in desired_config_tuple:
        entry = _find_entry_by_unique_id(hass, config.name)
        if entry is not None:
            _apply_registry_metadata(
                hass=hass,
                owner_entry_id=owner_entry_id,
                entry=entry,
                config=config,
            )


__all__ = ["async_reconcile_managed_adaptive_lighting"]
