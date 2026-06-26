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


def test_setup_mock_areas_is_idempotent_for_repeated_area_sets(
    hass: HomeAssistant,
) -> None:
    """Repeated setup should reuse the same area and floor entries."""
    areas = [MockAreaIds.KITCHEN, MockAreaIds.LIVING_ROOM]

    setup_mock_areas(hass, areas)
    area_registry = async_get_ar(hass)
    first_area_ids = {area.id for area in area_registry.async_list_areas()}
    first_floor_ids = {
        floor.floor_id for floor in async_get_fr(hass).async_list_floors()
    }

    setup_mock_areas(hass, areas)

    assert {
        area.id for area in area_registry.async_list_areas()
    } == first_area_ids
    assert {
        floor.floor_id for floor in async_get_fr(hass).async_list_floors()
    } == first_floor_ids


def test_setup_mock_areas_adds_new_areas_without_duplicating_existing_entries(
    hass: HomeAssistant,
) -> None:
    """A later setup batch should preserve existing areas while adding new ones."""
    area_registry = async_get_ar(hass)
    setup_mock_areas(hass, [MockAreaIds.KITCHEN])
    kitchen = area_registry.async_get_area_by_name(MockAreaIds.KITCHEN.value)
    assert kitchen is not None

    setup_mock_areas(
        hass,
        [MockAreaIds.KITCHEN, MockAreaIds.LIVING_ROOM],
    )

    updated_kitchen = area_registry.async_get_area_by_name(
        MockAreaIds.KITCHEN.value
    )
    living_room = area_registry.async_get_area_by_name(
        MockAreaIds.LIVING_ROOM.value
    )
    assert updated_kitchen is not None
    assert updated_kitchen.id == kitchen.id
    assert living_room is not None
    assert len(list(area_registry.async_list_areas())) == 2
    assert len(list(async_get_fr(hass).async_list_floors())) == 1


def test_setup_mock_areas_reconciles_existing_area_floor(
    hass: HomeAssistant,
) -> None:
    """Existing named areas should be moved to their configured mock floor."""
    area_registry = async_get_ar(hass)
    kitchen = area_registry.async_create(name=MockAreaIds.KITCHEN.value)
    assert kitchen.floor_id is None

    setup_mock_areas(hass, [MockAreaIds.KITCHEN])

    updated_kitchen = area_registry.async_get_area(kitchen.id)
    floor = async_get_fr(hass).async_get_floor_by_name(
        MockFloorIds.FIRST_FLOOR.value
    )
    assert updated_kitchen is not None
    assert floor is not None
    assert updated_kitchen.floor_id == floor.floor_id
