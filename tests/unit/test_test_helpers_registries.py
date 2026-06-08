"""Tests for shared Home Assistant registry setup helpers."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.floor_registry import async_get as async_get_fr

from tests.const import MockAreaIds, MockFloorIds
from tests.helpers.registries import setup_mock_areas


def test_setup_mock_areas_reuses_floors_and_assigns_areas(
    hass: HomeAssistant,
) -> None:
    """Areas configured for the same floor should share one registry floor."""
    setup_mock_areas(
        hass,
        [MockAreaIds.KITCHEN, MockAreaIds.LIVING_ROOM],
    )

    area_registry = async_get_ar(hass)
    floor_registry = async_get_fr(hass)
    floor = floor_registry.async_get_floor_by_name(MockFloorIds.FIRST_FLOOR.value)
    kitchen = area_registry.async_get_area_by_name(MockAreaIds.KITCHEN.value)
    living_room = area_registry.async_get_area_by_name(
        MockAreaIds.LIVING_ROOM.value
    )

    assert floor is not None
    assert kitchen is not None
    assert living_room is not None
    assert kitchen.floor_id == floor.floor_id
    assert living_room.floor_id == floor.floor_id
    assert len(list(floor_registry.async_list_floors())) == 1


def test_setup_mock_areas_supports_areas_without_floors(
    hass: HomeAssistant,
) -> None:
    """Areas without configured floors should remain unassigned."""
    setup_mock_areas(hass, [MockAreaIds.GLOBAL])

    area = async_get_ar(hass).async_get_area_by_name(MockAreaIds.GLOBAL.value)

    assert area is not None
    assert area.floor_id is None
    assert not async_get_fr(hass).async_list_floors()
