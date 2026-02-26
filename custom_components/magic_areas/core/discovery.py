"""Pure helper functions for area discovery in config flow.

These functions are designed to be testable without HA dependencies.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as areareg_async_get
from homeassistant.helpers.floor_registry import async_get as floorreg_async_get
from homeassistant.util import slugify

from custom_components.magic_areas.area_state import AreaType, MetaAreaType
from custom_components.magic_areas.config_keys import CONF_ID, CONF_TYPE
from custom_components.magic_areas.helpers.area import (
    BasicArea,
    basic_area_from_floor,
    basic_area_from_meta,
    basic_area_from_object,
)
from custom_components.magic_areas.schemas.area import DOMAIN_SCHEMA

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


def build_floor_meta_areas(
    floors: Iterable,
    area_ids: list[str],
) -> tuple[list[BasicArea], list[str]]:
    """Build meta areas from floor registry.

    Returns:
        Tuple of (created areas, reserved IDs to prevent conflicts)

    """
    areas = []
    reserved_ids = []

    for floor in floors:
        # Prevent conflicts between meta areas and existing areas
        if floor.floor_id in area_ids:
            _LOGGER.warning(
                "ConfigFlow: You have an area with a reserved name '%s'. "
                "This will prevent from using the %s Meta area.",
                floor.floor_id,
                floor.floor_id,
            )
            continue

        _LOGGER.debug(
            "ConfigFlow: Appending Meta Area %s to the list of areas",
            floor.floor_id,
        )
        area = basic_area_from_floor(floor)
        reserved_ids.append(area.id)
        areas.append(area)

    return areas, reserved_ids


def build_standard_meta_areas(
    area_ids: list[str],
) -> tuple[list[BasicArea], list[str]]:
    """Build standard meta areas (Global, Interior, Exterior).

    Returns:
        Tuple of (created areas, reserved IDs to prevent conflicts)

    """
    areas = []
    reserved_ids = []
    non_floor_meta_areas = [
        meta_area_type
        for meta_area_type in MetaAreaType
        if meta_area_type != MetaAreaType.FLOOR
    ]

    for meta_area in non_floor_meta_areas:
        # Prevent conflicts between meta areas and existing areas
        if meta_area in area_ids:
            _LOGGER.warning(
                "ConfigFlow: You have an area with a reserved name '%s'. "
                "This will prevent from using the %s Meta area.",
                meta_area,
                meta_area,
            )
            continue

        _LOGGER.debug(
            "ConfigFlow: Appending Meta Area %s to the list of areas", meta_area
        )
        area = basic_area_from_meta(meta_area)
        reserved_ids.append(area.id)
        areas.append(area)

    return areas, reserved_ids


def lookup_area_by_display_name(
    areas: list[BasicArea],
    display_name: str,
) -> BasicArea | None:
    """Look up an area by its display name.

    Handles both regular and meta area names (meta names have "(Meta) " prefix).

    Returns:
        The matching area or None if not found

    """
    area_name = display_name

    # Handle meta area name append
    if area_name.startswith("(Meta)"):
        area_name = " ".join(area_name.split(" ")[1:])

    for area in areas:
        if area.name == area_name:
            return area

    return None


def build_area_selector_options(
    areas: list[BasicArea],
    reserved_ids: list[str],
) -> list[str]:
    """Build area names for selector, with meta areas marked.

    Regular areas come first (sorted), then meta areas (sorted).

    Returns:
        List of display names for selector

    """
    available_area_names = sorted(
        [area.name for area in areas if area.id not in reserved_ids]
    )
    available_area_names.extend(
        sorted(
            [
                f"(Meta) {area.name}"
                for area in areas
                if area.id in reserved_ids
            ]
        )
    )
    return available_area_names


def create_area_config_entry(
    area_object: BasicArea,
    reserved_ids: list[str],
) -> dict:
    """Create default config dict for an area.

    Returns:
        Default config entry dict with type set for meta areas

    """
    config_entry = DOMAIN_SCHEMA({f"{area_object.id}": {}})[area_object.id]
    extra_opts = {
        "name": area_object.name,
        CONF_ID: area_object.id,
    }
    config_entry.update(extra_opts)

    # Handle Meta area
    if slugify(area_object.id) in reserved_ids:
        _LOGGER.debug(
            "ConfigFlow: Meta area %s found, setting correct type.",
            area_object.id,
        )
        config_entry.update({CONF_TYPE: AreaType.META})

    return config_entry


async def load_candidate_areas(
    hass: HomeAssistant,
) -> tuple[list[BasicArea], list[str]]:
    """Load all candidate areas from registries.

    Includes regular areas, floors, and standard meta areas.

    Returns:
        Tuple of (all areas including meta, reserved IDs)

    """
    reserved_ids = []

    # Load registries
    area_registry = areareg_async_get(hass)
    floor_registry = floorreg_async_get(hass)

    areas = [
        basic_area_from_object(area) for area in area_registry.async_list_areas()
    ]
    area_ids = [area.id for area in areas]

    # Load floors meta-areas
    floors = floor_registry.async_list_floors()
    floor_areas, floor_reserved = build_floor_meta_areas(floors, area_ids)
    areas.extend(floor_areas)
    reserved_ids.extend(floor_reserved)

    # Add standard meta areas
    standard_areas, standard_reserved = build_standard_meta_areas(area_ids)
    areas.extend(standard_areas)
    reserved_ids.extend(standard_reserved)

    return areas, reserved_ids
