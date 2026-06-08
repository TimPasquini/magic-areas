"""Home Assistant registry setup helpers for tests."""

from collections.abc import Sequence

from homeassistant.const import ATTR_FLOOR_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.floor_registry import async_get as async_get_fr

from tests.const import MOCK_AREAS, MockAreaIds


def setup_mock_areas(
    hass: HomeAssistant,
    areas: Sequence[MockAreaIds],
) -> None:
    """Register mock areas and their configured floors."""
    area_registry = async_get_ar(hass)
    floor_registry = async_get_fr(hass)

    for area in areas:
        area_object = MOCK_AREAS[area]
        floor_id: str | None = None

        if area_object[ATTR_FLOOR_ID]:
            assert area_object[ATTR_FLOOR_ID] is not None
            floor_name = str(area_object[ATTR_FLOOR_ID])
            floor_entry = floor_registry.async_get_floor_by_name(floor_name)
            if not floor_entry:
                floor_entry = floor_registry.async_create(floor_name)
            assert floor_entry is not None
            floor_id = floor_entry.floor_id
        area_registry.async_create(name=area.value, floor_id=floor_id)
