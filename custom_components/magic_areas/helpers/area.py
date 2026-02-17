"""Magic Areas Area Helper Functions.

Small helper functions for area and Magic Area objects.
"""

import logging
from typing import TYPE_CHECKING

from homeassistant.const import ATTR_ID, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import (
    AreaEntry,
    async_get as areareg_async_get,
)
from homeassistant.helpers.floor_registry import (
    FloorEntry,
    async_get as floorreg_async_get,
)
from homeassistant.util import slugify

from custom_components.magic_areas.base.magic import BasicArea, MagicArea
from custom_components.magic_areas.area_state import MetaAreaType
from custom_components.magic_areas.config_keys import CONF_TYPE
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.icons import MetaAreaIcons

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


def basic_area_from_meta(area_id: str, name: str | None = None) -> BasicArea:
    """Create a BasicArea from a name."""

    basic_area = BasicArea()
    if not name:
        basic_area.name = area_id.capitalize()
    basic_area.id = area_id
    basic_area.is_meta = True

    meta_area_icon_map = {
        MetaAreaType.EXTERIOR.value: MetaAreaIcons.EXTERIOR.value,
        MetaAreaType.INTERIOR.value: MetaAreaIcons.INTERIOR.value,
        MetaAreaType.GLOBAL.value: MetaAreaIcons.GLOBAL.value,
    }

    basic_area.icon = meta_area_icon_map.get(area_id, None)

    return basic_area


def basic_area_from_object(area: AreaEntry) -> BasicArea:
    """Create a BasicArea from an AreaEntry object."""

    basic_area = BasicArea()
    basic_area.name = area.name
    basic_area.id = area.id
    basic_area.icon = area.icon
    basic_area.floor_id = area.floor_id

    return basic_area


def basic_area_from_floor(floor: FloorEntry) -> BasicArea:
    """Create a BasicArea from an AreaEntry object."""

    basic_area = BasicArea()
    basic_area.name = floor.name
    basic_area.id = floor.floor_id
    default_icon = (
        f"mdi:home-floor-{floor.level}"  # noqa: E231
        if floor.level is not None
        else "mdi:home"  # noqa: E231
    )
    basic_area.icon = floor.icon or default_icon
    basic_area.floor_id = floor.floor_id
    basic_area.is_meta = True

    return basic_area


def get_magic_area_for_config_entry(
    hass: HomeAssistant, config_entry: "MagicAreasConfigEntry"
) -> MagicArea | None:
    """Return magic area object for given config entry."""

    area_id = config_entry.data[ATTR_ID]
    area_name = config_entry.data[ATTR_NAME]

    _LOGGER.debug("%s: Setting up entry.", area_name)

    # Load floors
    floor_registry = floorreg_async_get(hass)
    floors = floor_registry.async_list_floors()

    non_floor_meta_ids = [
        meta_area_type
        for meta_area_type in MetaAreaType
        if meta_area_type != MetaAreaType.FLOOR
    ]
    floor_ids = [f.floor_id for f in floors]

    magic_area: MagicArea

    if area_id in non_floor_meta_ids:
        # Non-floor Meta-Area (Global/Interior/Exterior)
        meta_area = basic_area_from_meta(area_id)
        magic_area = MagicArea(hass, meta_area, config_entry)
    elif area_id in floor_ids:
        # Floor Meta-Area
        floor_entry: FloorEntry | None = floor_registry.async_get_floor(area_id)
        assert floor_entry is not None
        meta_area = basic_area_from_floor(floor_entry)
        magic_area = MagicArea(hass, meta_area, config_entry)
    else:
        # Regular Area
        area_registry = areareg_async_get(hass)
        area = area_registry.async_get_area(area_id)

        if not area:
            _LOGGER.warning("%s: ID '%s' not found on registry", area_name, area_id)
            return None

        _LOGGER.debug("%s: Got area from registry: %s", area_name, str(area))

        magic_area = MagicArea(
            hass,
            basic_area_from_object(area),
            config_entry,
        )

    return magic_area


def build_area_config_for_config_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
) -> AreaConfig | None:
    """Build an AreaConfig directly from the area/floor registry and config entry.

    This replaces the MagicArea construction path for cases where only configuration
    data is needed (i.e. the coordinator). No MagicArea object is created.

    Returns None if the area ID is not found in the registry (regular areas only).
    """
    area_id: str = config_entry.data[ATTR_ID]
    area_name: str = config_entry.data[ATTR_NAME]

    area_config_data: dict = dict(config_entry.data)
    if config_entry.options:
        area_config_data.update(config_entry.options)

    floor_registry = floorreg_async_get(hass)
    floors = floor_registry.async_list_floors()
    floor_ids = [f.floor_id for f in floors]

    non_floor_meta_ids = [
        meta_area_type.value
        for meta_area_type in MetaAreaType
        if meta_area_type != MetaAreaType.FLOOR
    ]

    icon: str | None = None
    floor_id: str | None = None

    if area_id in non_floor_meta_ids:
        meta_icon_map = {
            MetaAreaType.EXTERIOR.value: MetaAreaIcons.EXTERIOR.value,
            MetaAreaType.INTERIOR.value: MetaAreaIcons.INTERIOR.value,
            MetaAreaType.GLOBAL.value: MetaAreaIcons.GLOBAL.value,
        }
        icon = meta_icon_map.get(area_id)
        name = area_id.capitalize()
    elif area_id in floor_ids:
        floor_entry = floor_registry.async_get_floor(area_id)
        assert floor_entry is not None
        icon = floor_entry.icon or (
            f"mdi:home-floor-{floor_entry.level}"
            if floor_entry.level is not None
            else "mdi:home"
        )
        floor_id = floor_entry.floor_id
        name = floor_entry.name
    else:
        area_registry = areareg_async_get(hass)
        area = area_registry.async_get_area(area_id)
        if not area:
            _LOGGER.warning("%s: ID '%s' not found on registry", area_name, area_id)
            return None
        icon = area.icon
        floor_id = area.floor_id
        name = area.name

    area_type = area_config_data.get(CONF_TYPE) or area_id

    return AreaConfig(
        id=area_id,
        name=name,
        slug=slugify(name),
        icon=icon,
        floor_id=floor_id,
        area_type=str(area_type),
        config=area_config_data,
        hass_config=config_entry,
    )
