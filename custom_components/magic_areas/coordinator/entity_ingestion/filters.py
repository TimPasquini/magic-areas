"""Pure functions for loading and filtering area entities."""

from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_registry import RegistryEntry

from custom_components.magic_areas.defaults import (
    DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES,
)


def is_magic_area_entity(entity: RegistryEntry, config_entry_id: str) -> bool:
    """Return if entity belongs to this integration instance.

    Args:
        entity: Entity registry entry
        config_entry_id: Config entry ID for this area

    Returns:
        True if entity belongs to this integration instance

    """
    return entity.config_entry_id == config_entry_id


def should_exclude_entity(
    entity: RegistryEntry,
    config_entry_id: str,
    exclude_list: list[str] | None = None,
    ignore_diagnostic: bool | None = None,
) -> bool:
    """Determine if entity should be excluded from area.

    Args:
        entity: Entity registry entry
        config_entry_id: Config entry ID for this area
        exclude_list: List of entity IDs to exclude
        ignore_diagnostic: Whether to ignore diagnostic entities

    Returns:
        True if entity should be excluded

    """
    # Is magic_area entity?
    if entity.config_entry_id == config_entry_id:
        return True

    # Is disabled?
    if entity.disabled:
        return True

    # Is in the exclusion list?
    if exclude_list and entity.entity_id in exclude_list:
        return True

    # Are we excluding DIAGNOSTIC and CONFIG?
    if ignore_diagnostic is None:
        ignore_diagnostic = DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES

    if ignore_diagnostic:
        if entity.entity_category in [
            EntityCategory.CONFIG,
            EntityCategory.DIAGNOSTIC,
        ]:
            return True

    return False


def filter_entity_list(
    entity_list: list[RegistryEntry],
    config_entry_id: str,
    exclude_list: list[str] | None = None,
    ignore_diagnostic: bool | None = None,
) -> list[RegistryEntry]:
    """Filter entity list based on exclusion criteria.

    Args:
        entity_list: Raw entity registry entries
        config_entry_id: Config entry ID for this area
        exclude_list: List of entity IDs to exclude
        ignore_diagnostic: Whether to ignore diagnostic entities

    Returns:
        Filtered list of entities

    """
    return [
        entity
        for entity in entity_list
        if not should_exclude_entity(
            entity, config_entry_id, exclude_list, ignore_diagnostic
        )
    ]
