"""Tests for meta-area functionality."""

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.const import MockAreaIds


async def test_magic_meta_area_active_areas(
    hass: HomeAssistant, init_integration_all_areas: list[MockConfigEntry]
) -> None:
    """Test getting active areas for a meta area."""

    # Get Global Meta Area
    global_entry = None
    for entry in init_integration_all_areas:
        if entry.data["id"] == MockAreaIds.GLOBAL.value:
            global_entry = entry
            break

    assert global_entry is not None
    entry = hass.config_entries.async_get_entry(global_entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinator
    meta_area_config = coordinator.data.area_config

    assert meta_area_config.is_meta()

    # Mock child area states
    # Kitchen (child of Global) -> Occupied
    kitchen_state_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_"
        f"{MockAreaIds.KITCHEN.value}_area_state"
    )
    hass.states.async_set(kitchen_state_id, STATE_ON)

    # Living Room (child of Global) -> Clear
    living_room_state_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_"
        f"{MockAreaIds.LIVING_ROOM.value}_area_state"
    )
    hass.states.async_set(living_room_state_id, STATE_OFF)

    # Refresh coordinator to pick up state changes
    await coordinator.async_refresh()

    # Read active areas from snapshot
    active_areas = coordinator.data.active_areas

    assert MockAreaIds.KITCHEN.value in active_areas
    assert MockAreaIds.LIVING_ROOM.value not in active_areas


async def test_get_child_areas_floor_logic(
    hass: HomeAssistant, init_integration_all_areas: list[MockConfigEntry]
) -> None:
    """Test get_child_areas logic for floors."""

    # Get First Floor Meta Area
    floor_entry = None
    for entry in init_integration_all_areas:
        if entry.data["id"] == MockAreaIds.FIRST_FLOOR.value:
            floor_entry = entry
            break

    assert floor_entry is not None
    entry = hass.config_entries.async_get_entry(floor_entry.entry_id)
    assert entry is not None
    children = entry.runtime_data.coordinator.data.child_areas
    # Kitchen, Living Room, Dining Room are on First Floor
    assert MockAreaIds.KITCHEN.value in children
    assert MockAreaIds.LIVING_ROOM.value in children
    assert MockAreaIds.DINING_ROOM.value in children
    assert MockAreaIds.MASTER_BEDROOM.value not in children  # Second floor
