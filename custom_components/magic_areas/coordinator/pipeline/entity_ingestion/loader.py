"""Extract entity loading logic from MagicArea."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from custom_components.magic_areas.core.config import (
    exclude_entities,
    ignore_diagnostic_entities,
    include_entities,
)
from custom_components.magic_areas.coordinator.pipeline.entity_ingestion.registry_queries import (
    EntitySnapshot,
    build_entity_dict,
    get_area_entities,
    get_child_magic_entities,
    get_device_entities_for_area,
    get_device_registry,
    get_entity_registry,
    get_included_entities,
    get_magic_entities_for_config_entry,
    group_entities,
)
from custom_components.magic_areas.core.managed_surface_registry import (
    is_managed_surface_config_entry,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import RegistryEntry

_LOGGER = logging.getLogger(__name__)
_EXPECTED_ENTITY_LOAD_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


async def load_area_entities(
    hass: HomeAssistant,
    area_id: str,
    config_entry_id: str,
    config: dict[str, object],
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

    entity_list: list[RegistryEntry] = []
    include_entity_ids = include_entities(config)
    exclude_entity_ids = exclude_entities(config)
    ignore_diagnostic = ignore_diagnostic_entities(config)

    entity_registry = get_entity_registry(hass)
    device_registry = get_device_registry(hass)

    # Add entities from devices in this area
    entity_list.extend(
        get_device_entities_for_area(
            entity_registry=entity_registry,
            device_registry=device_registry,
            area_id=area_id,
            config_entry_id=config_entry_id,
            exclude_entities=exclude_entity_ids,
            ignore_diagnostic=ignore_diagnostic,
        )
    )

    # Add entities that are specifically set as this area but device is not or has no device
    entity_list.extend(
        get_area_entities(
            entity_registry=entity_registry,
            area_id=area_id,
            existing_entity_ids=[e.entity_id for e in entity_list],
            config_entry_id=config_entry_id,
            exclude_entities=exclude_entity_ids,
            ignore_diagnostic=ignore_diagnostic,
        )
    )

    # Add explicitly included entities (with same exclusion rules)
    if include_entity_ids:
        entity_list.extend(
            get_included_entities(
                entity_registry=entity_registry,
                include_entities=include_entity_ids,
                config_entry_id=config_entry_id,
                exclude_entities=exclude_entity_ids,
                ignore_diagnostic=ignore_diagnostic,
            )
        )

    entity_list = _exclude_managed_helper_entities(hass, entity_list)

    # Process entity list into domain-grouped format
    entities_by_domain = await _process_entity_list(hass, entity_list, area_id, logger)

    # Load magic entities (integration-generated)
    magic_entities_by_domain = await _load_magic_entities(hass, config_entry_id, logger)

    return entities_by_domain, magic_entities_by_domain


def _exclude_managed_helper_entities(
    hass: HomeAssistant,
    entity_list: list[RegistryEntry],
) -> list[RegistryEntry]:
    """Remove HA helper entities managed by Magic Areas from source enumeration."""
    filtered: list[RegistryEntry] = []
    for entity in entity_list:
        if entity.config_entry_id:
            entry = hass.config_entries.async_get_entry(entity.config_entry_id)
            if entry and is_managed_surface_config_entry(entry):
                continue
        filtered.append(entity)
    return filtered


async def load_meta_area_entities(
    hass: HomeAssistant,
    child_area_slugs: list[str],
    config_entry_id: str,
    config: dict[str, object],
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

    entity_list: list[RegistryEntry] = []
    exclude_entity_ids = exclude_entities(config)

    entity_registry = get_entity_registry(hass)
    entity_list.extend(
        get_child_magic_entities(
            hass=hass,
            entity_registry=entity_registry,
            child_area_slugs=child_area_slugs,
            exclude_entities=exclude_entity_ids,
        )
    )

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
            combined_attributes: dict[str, object] = (
                dict(latest_state.attributes) if latest_state else {}
            )
            if entity.original_device_class:
                # Handle both Enum and string device classes
                if hasattr(entity.original_device_class, "value"):
                    combined_attributes["device_class"] = str(
                        entity.original_device_class.value
                    )
                else:
                    combined_attributes["device_class"] = str(
                        entity.original_device_class
                    )
            if entity.unit_of_measurement:
                combined_attributes["unit_of_measurement"] = entity.unit_of_measurement

            snapshots.append(
                EntitySnapshot(
                    entity_id=entity.entity_id,
                    domain=entity.domain,
                    attributes=combined_attributes if combined_attributes else None,
                )
            )

        except _EXPECTED_ENTITY_LOAD_ERRORS as err:
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
    magic_entities_by_domain: dict[str, list[dict[str, str]]] = {}

    # Add magic area entities
    entity_registry = get_entity_registry(hass)
    entities_for_config_id = get_magic_entities_for_config_entry(
        entity_registry=entity_registry,
        config_entry_id=config_entry_id,
    )

    for entity in entities_for_config_id:
        entity_id = entity.entity_id
        entity_domain = entity_id.split(".")[0]

        if entity_domain not in magic_entities_by_domain:
            magic_entities_by_domain[entity_domain] = []

        latest_state = hass.states.get(entity_id)
        magic_entities_by_domain[entity_domain].append(
            build_entity_dict(
                entity_id, latest_state.attributes if latest_state else None
            )
        )

    logger.debug("Loaded magic entities: %s", str(magic_entities_by_domain))

    return magic_entities_by_domain
