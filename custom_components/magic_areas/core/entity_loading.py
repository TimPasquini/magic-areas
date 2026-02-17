"""Extract entity loading logic from MagicArea."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import async_get as devicereg_async_get
from homeassistant.helpers.entity_registry import (
    async_get as entityreg_async_get,
)

from custom_components.magic_areas.config_keys import (
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.entities import (
    EntitySnapshot,
    build_entity_dict,
    group_entities,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import RegistryEntry

_LOGGER = logging.getLogger(__name__)


async def load_area_entities(
    hass: HomeAssistant,
    area_id: str,
    config_entry_id: str,
    config: dict[str, Any],
    logger: logging.Logger | None = None,
) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    """Load entities and magic_entities for a regular area.

    Args:
        hass: Home Assistant instance
        area_id: Area ID to load entities for
        config_entry_id: Config entry ID for filtering
        config: Area configuration
        logger: Optional logger for debug output

    Returns:
        Tuple of (entities_by_domain, magic_entities_by_domain)

    """
    if logger is None:
        logger = _LOGGER

    entity_registry = entityreg_async_get(hass)
    device_registry = devicereg_async_get(hass)

    entity_list: list[RegistryEntry] = []
    include_entities = config.get(CONF_INCLUDE_ENTITIES)
    exclude_entities = config.get(CONF_EXCLUDE_ENTITIES, [])

    # Add entities from devices in this area
    devices_in_area = device_registry.devices.get_devices_for_area_id(area_id)
    for device in devices_in_area:
        device_entities = [
            entity
            for entity in entity_registry.entities.get_entries_for_device_id(
                device.id
            )
            if not (
                entity.disabled
                or entity.config_entry_id == config_entry_id
                or entity.entity_id in exclude_entities
                or entity.entity_category == EntityCategory.DIAGNOSTIC
            )
        ]
        entity_list.extend(device_entities)

    # Add entities that are specifically set as this area but device is not or has no device
    entities_in_area = entity_registry.entities.get_entries_for_area_id(area_id)
    entity_list.extend(
        [
            entity
            for entity in entities_in_area
            if entity.entity_id not in [e.entity_id for e in entity_list]
            and not (
                entity.disabled
                or entity.config_entry_id == config_entry_id
                or entity.entity_id in exclude_entities
                or entity.entity_category == EntityCategory.DIAGNOSTIC
            )
        ]
    )

    # Add explicitly included entities (with same exclusion rules)
    if include_entities and isinstance(include_entities, list):
        for include_entity in include_entities:
            entity_entry = entity_registry.async_get(include_entity)
            if entity_entry and not (
                entity_entry.disabled
                or entity_entry.config_entry_id == config_entry_id
                or entity_entry.entity_id in exclude_entities
                or entity_entry.entity_category == EntityCategory.DIAGNOSTIC
            ):
                entity_list.append(entity_entry)

    # Process entity list into domain-grouped format
    entities_by_domain = await _process_entity_list(
        hass, entity_list, area_id, logger
    )

    # Load magic entities (integration-generated)
    magic_entities_by_domain = await _load_magic_entities(
        hass, config_entry_id, logger
    )

    return entities_by_domain, magic_entities_by_domain


async def load_meta_area_entities(
    hass: HomeAssistant,
    child_area_slugs: list[str],
    config_entry_id: str,
    config: dict[str, Any],
    logger: logging.Logger | None = None,
) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    """Load entities for a meta area from child area magic entities.

    Args:
        hass: Home Assistant instance
        child_area_slugs: List of child area slugs
        config_entry_id: Config entry ID for filtering
        config: Meta area configuration
        logger: Optional logger for debug output

    Returns:
        Tuple of (entities_by_domain, magic_entities_by_domain)

    """
    if logger is None:
        logger = _LOGGER

    entity_registry = entityreg_async_get(hass)
    entity_list: list[RegistryEntry] = []
    exclude_entities = config.get(CONF_EXCLUDE_ENTITIES, [])

    # Load from child area magic entities
    entries = hass.config_entries.async_entries(DOMAIN)
    for entry in entries:
        if entry.state != ConfigEntryState.LOADED:
            continue

        if entry.domain != DOMAIN:
            continue

        # Get the area config from coordinator snapshot
        coordinator_data = entry.runtime_data.coordinator.data
        if coordinator_data is None:
            continue

        if coordinator_data.area_config.slug not in child_area_slugs:
            continue

        # Load magic entities directly from entity registry for this child area
        child_magic_entities = entity_registry.entities.get_entries_for_config_entry_id(
            entry.entry_id
        )

        # Collect entities from child area's magic entities
        for entity_entry in child_magic_entities:
            entity_id = entity_entry.entity_id

            # Skip excluded entities
            if entity_id in exclude_entities:
                continue

            entity_list.append(entity_entry)

    # Process entity list
    entities_by_domain = await _process_entity_list(
        hass, entity_list, "meta_area", logger
    )

    # Meta areas return empty magic_entities (they aggregate child magic entities)
    magic_entities_by_domain: dict[str, list[dict[str, str]]] = {}

    return entities_by_domain, magic_entities_by_domain


async def _process_entity_list(
    hass: HomeAssistant,
    entity_list: list[RegistryEntry],
    area_id: str,
    logger: logging.Logger,
) -> dict[str, list[dict[str, str]]]:
    """Process raw entity list into domain-grouped format.

    Args:
        hass: Home Assistant instance
        entity_list: Raw entity registry entries
        area_id: Area ID (for logging)
        logger: Logger instance

    Returns:
        Entities grouped by domain

    """
    logger.debug("Original entity list: %s", str(entity_list))
    snapshots: list[EntitySnapshot] = []

    for entity in entity_list:
        logger.debug("Loading entity: %s", entity.entity_id)

        try:
            if not entity.domain:
                logger.warning("Entity domain not found for %s", entity)
                continue

            latest_state = hass.states.get(entity.entity_id)

            # Combine state attributes with registry metadata (device_class, unit_of_measurement)
            combined_attributes = dict(latest_state.attributes) if latest_state else {}
            if entity.original_device_class:
                # Handle both Enum and string device classes
                if hasattr(entity.original_device_class, "value"):
                    combined_attributes["device_class"] = str(entity.original_device_class.value)
                else:
                    combined_attributes["device_class"] = str(entity.original_device_class)
            if entity.unit_of_measurement:
                combined_attributes["unit_of_measurement"] = entity.unit_of_measurement

            snapshots.append(
                EntitySnapshot(
                    entity_id=entity.entity_id,
                    domain=entity.domain,
                    attributes=combined_attributes if combined_attributes else None,
                )
            )

        # Adding pylint exception because this is a last-resort hail-mary catch-all
        # pylint: disable-next=broad-exception-caught
        except Exception as err:
            logger.error(
                "Unable to load entity '%s': %s",
                entity,
                str(err),
            )

    return group_entities(snapshots)


async def _load_magic_entities(
    hass: HomeAssistant,
    config_entry_id: str,
    logger: logging.Logger,
) -> dict[str, list[dict[str, str]]]:
    """Load magic areas-generated entities.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID to filter for
        logger: Logger instance

    Returns:
        Magic entities grouped by domain

    """
    entity_registry = entityreg_async_get(hass)
    magic_entities_by_domain: dict[str, list[dict[str, str]]] = {}

    # Add magic area entities
    entities_for_config_id = (
        entity_registry.entities.get_entries_for_config_entry_id(config_entry_id)
    )

    for entity in entities_for_config_id:
        entity_id = entity.entity_id
        entity_domain = entity_id.split(".")[0]

        if entity_domain not in magic_entities_by_domain:
            magic_entities_by_domain[entity_domain] = []

        latest_state = hass.states.get(entity_id)
        magic_entities_by_domain[entity_domain].append(
            build_entity_dict(entity_id, latest_state.attributes if latest_state else None)
        )

    logger.debug("Loaded magic entities: %s", str(magic_entities_by_domain))

    return magic_entities_by_domain
