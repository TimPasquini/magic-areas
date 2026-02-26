"""Entity/device registry queries for Magic Areas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.device_registry import async_get as devicereg_async_get
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.entity_loading.filters import (
    should_exclude_entity,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceRegistry
    from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry


def get_entity_registry(hass: HomeAssistant) -> EntityRegistry:
    """Return the entity registry."""
    return entityreg_async_get(hass)


def get_device_registry(hass: HomeAssistant) -> DeviceRegistry:
    """Return the device registry."""
    return devicereg_async_get(hass)


def get_device_entities_for_area(
    entity_registry: EntityRegistry,
    device_registry: DeviceRegistry,
    area_id: str,
    config_entry_id: str,
    exclude_entities: list[str],
    ignore_diagnostic: bool | None = None,
) -> list[RegistryEntry]:
    """Return registry entries for devices in the given area."""
    entity_list: list[RegistryEntry] = []
    devices_in_area = device_registry.devices.get_devices_for_area_id(area_id)
    for device in devices_in_area:
        device_entities = [
            entity
            for entity in entity_registry.entities.get_entries_for_device_id(
                device.id
            )
            if not should_exclude_entity(
                entity,
                config_entry_id,
                exclude_list=exclude_entities,
                ignore_diagnostic=ignore_diagnostic,
            )
        ]
        entity_list.extend(device_entities)
    return entity_list


def get_area_entities(
    entity_registry: EntityRegistry,
    area_id: str,
    existing_entity_ids: list[str],
    config_entry_id: str,
    exclude_entities: list[str],
    ignore_diagnostic: bool | None = None,
) -> list[RegistryEntry]:
    """Return registry entries explicitly assigned to the area."""
    entities_in_area = entity_registry.entities.get_entries_for_area_id(area_id)
    return [
        entity
        for entity in entities_in_area
        if entity.entity_id not in existing_entity_ids
        and not should_exclude_entity(
            entity,
            config_entry_id,
            exclude_list=exclude_entities,
            ignore_diagnostic=ignore_diagnostic,
        )
    ]


def get_included_entities(
    entity_registry: EntityRegistry,
    include_entities: list[str],
    config_entry_id: str,
    exclude_entities: list[str],
    ignore_diagnostic: bool | None = None,
) -> list[RegistryEntry]:
    """Return explicitly included entities."""
    entity_list: list[RegistryEntry] = []
    for include_entity in include_entities:
        entity_entry = entity_registry.async_get(include_entity)
        if entity_entry and not should_exclude_entity(
            entity_entry,
            config_entry_id,
            exclude_list=exclude_entities,
            ignore_diagnostic=ignore_diagnostic,
        ):
            entity_list.append(entity_entry)
    return entity_list


def get_child_magic_entities(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    child_area_slugs: list[str],
    exclude_entities: list[str],
) -> list[RegistryEntry]:
    """Return magic entities for child areas in a meta area."""
    entity_list: list[RegistryEntry] = []
    entries = hass.config_entries.async_entries(DOMAIN)
    for entry in entries:
        if entry.state != ConfigEntryState.LOADED:
            continue
        if entry.domain != DOMAIN:
            continue

        coordinator_data = entry.runtime_data.coordinator.data
        if coordinator_data is None:
            continue
        if coordinator_data.area_config.slug not in child_area_slugs:
            continue

        child_magic_entities = entity_registry.entities.get_entries_for_config_entry_id(
            entry.entry_id
        )
        for entity_entry in child_magic_entities:
            if entity_entry.entity_id in exclude_entities:
                continue
            entity_list.append(entity_entry)

    return entity_list


def get_magic_entities_for_config_entry(
    entity_registry: EntityRegistry, config_entry_id: str
) -> list[RegistryEntry]:
    """Return magic entities for the given config entry."""
    return entity_registry.entities.get_entries_for_config_entry_id(config_entry_id)
