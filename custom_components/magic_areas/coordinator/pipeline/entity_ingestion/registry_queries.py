"""Entity/device registry queries for Magic Areas."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from homeassistant.const import EntityCategory
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.device_registry import async_get as devicereg_async_get
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.defaults import (
    DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES,
)
from custom_components.magic_areas.core.managed_surface_registry import (
    iter_managed_surface_entity_entries,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceRegistry
    from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry


@dataclass(slots=True)
class EntitySnapshot:
    """Pure entity snapshot for grouping and normalization."""

    entity_id: str
    domain: str
    attributes: Mapping[str, object] | None = None


def _normalize_attr_value(value: object) -> str:
    """Normalize attribute values for snapshot storage."""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (list, tuple, set)):
        return str([_normalize_attr_value(item) for item in value])
    if isinstance(value, dict):
        return str({key: _normalize_attr_value(item) for key, item in value.items()})
    return str(value)


def build_entity_dict(
    entity_id: str, attributes: Mapping[str, object] | None
) -> dict[str, str]:
    """Return entity_id with normalized attributes (excluding entity_id)."""
    entity_dict: dict[str, str] = {ATTR_ENTITY_ID: entity_id}

    if attributes:
        for attr_key, attr_value in attributes.items():
            if attr_key == ATTR_ENTITY_ID:
                continue
            entity_dict[str(attr_key)] = _normalize_attr_value(attr_value)

    return entity_dict


def group_entities(entities: list[EntitySnapshot]) -> dict[str, list[dict[str, str]]]:
    """Group entity snapshots by domain with normalized attributes."""
    grouped: dict[str, list[dict[str, str]]] = {}

    for entity in entities:
        grouped.setdefault(entity.domain, []).append(
            build_entity_dict(entity.entity_id, entity.attributes)
        )

    return grouped


def get_entity_registry(hass: HomeAssistant) -> EntityRegistry:
    """Return the entity registry."""
    return entityreg_async_get(hass)


def is_magic_area_entity(entity: RegistryEntry, config_entry_id: str) -> bool:
    """Return if entity belongs to this integration instance."""
    return entity.config_entry_id == config_entry_id


def should_exclude_entity(
    entity: RegistryEntry,
    config_entry_id: str,
    exclude_list: list[str] | None = None,
    ignore_diagnostic: bool | None = None,
) -> bool:
    """Determine if entity should be excluded from area."""
    if entity.config_entry_id == config_entry_id:
        return True

    if entity.disabled:
        return True

    if exclude_list and entity.entity_id in exclude_list:
        return True

    if ignore_diagnostic is None:
        ignore_diagnostic = DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES

    if ignore_diagnostic and entity.entity_category in (
        EntityCategory.CONFIG,
        EntityCategory.DIAGNOSTIC,
    ):
        return True

    return False


def filter_entity_list(
    entity_list: list[RegistryEntry],
    config_entry_id: str,
    exclude_list: list[str] | None = None,
    ignore_diagnostic: bool | None = None,
) -> list[RegistryEntry]:
    """Filter entity list based on exclusion criteria."""
    return [
        entity
        for entity in entity_list
        if not should_exclude_entity(
            entity,
            config_entry_id,
            exclude_list,
            ignore_diagnostic,
        )
    ]


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
            for entity in entity_registry.entities.get_entries_for_device_id(device.id)
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

        for entity_entry in iter_managed_surface_entity_entries(
            hass,
            entity_registry,
            owner_entry_id=entry.entry_id,
            loaded_only=True,
        ):
            if entity_entry.entity_id in exclude_entities:
                continue
            entity_list.append(entity_entry)

    return entity_list


def get_magic_entities_for_config_entry(
    entity_registry: EntityRegistry, config_entry_id: str
) -> list[RegistryEntry]:
    """Return magic entities for the given config entry."""
    return entity_registry.entities.get_entries_for_config_entry_id(config_entry_id)
