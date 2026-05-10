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


async def _async_apply_managed_adaptive_lighting_operation(
    *,
    hass: HomeAssistant,
    operation: ManagedAdaptiveLightingReconcileOperation,
) -> None:
    """Apply one managed Adaptive Lighting config-entry reconciliation operation."""
    if operation.action is ManagedAdaptiveLightingReconcileAction.CREATE:
        await hass.config_entries.async_add(_build_config_entry(operation))
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


async def async_reconcile_managed_adaptive_lighting(
    *,
    hass: HomeAssistant,
    desired_configs: Iterable[ManagedAdaptiveLightingConfig],
) -> None:
    """Create, update, and remove Magic Areas-managed Adaptive Lighting entries."""
    operations = managed_adaptive_lighting_reconcile_plan(
        desired_configs=desired_configs,
        existing_entries=[
            _project_entry(entry)
            for entry in hass.config_entries.async_entries(ADAPTIVE_LIGHTING_DOMAIN)
        ],
    )

    for operation in operations:
        try:
            await _async_apply_managed_adaptive_lighting_operation(
                hass=hass,
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


__all__ = ["async_reconcile_managed_adaptive_lighting"]
