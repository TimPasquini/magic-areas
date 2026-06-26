"""Test for the logic on automatically reloading areas."""
import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    _EventEntityRegistryUpdatedData_CreateRemove,
    _EventEntityRegistryUpdatedData_Update,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import (
    DOMAIN,
)
from custom_components.magic_areas.components import MagicAreasRuntimeData
from custom_components.magic_areas.coordinator import MagicAreasData
from tests.const import MockAreaIds
from tests.helpers.waits import wait_until
from tests.mocks import MockBinarySensor

_LOGGER = logging.getLogger(__name__)

# Constants

NORMAL_AREAS = [
    MockAreaIds.KITCHEN.value,
    MockAreaIds.BACKYARD.value,
    MockAreaIds.MASTER_BEDROOM.value,
]
REGULAR_META_AREAS = [
    MockAreaIds.GLOBAL.value,
    MockAreaIds.INTERIOR.value,
    MockAreaIds.EXTERIOR.value,
]
FLOOR_META_AREAS = [
    MockAreaIds.GROUND_LEVEL.value,
    MockAreaIds.FIRST_FLOOR.value,
    MockAreaIds.SECOND_FLOOR.value,
]
ALL_AREAS = NORMAL_AREAS + REGULAR_META_AREAS + FLOOR_META_AREAS

# Helpers


def get_config_entry_by_area_name(hass: HomeAssistant, area_name: str) -> str | None:
    """Fetch config_entry_id from an area's name."""
    entries = hass.config_entries.async_entries(DOMAIN)
    for entry in entries:
        if entry.state != ConfigEntryState.LOADED:
            continue
        # After Phase 8, access area config from coordinator snapshot
        runtime_data = entry.runtime_data
        if not isinstance(runtime_data, MagicAreasRuntimeData):
            continue
        coordinator_data = runtime_data.coordinator.data
        if coordinator_data and coordinator_data.area_config.id == area_name.lower():
            return entry.entry_id

    return None


def get_entry_by_area_name(hass: HomeAssistant, area_name: str) -> MagicAreasData | None:
    """Fetch coordinator snapshot from an area's name."""
    config_entry_id = get_config_entry_by_area_name(hass, area_name)
    if not config_entry_id:
        return None

    entry = hass.config_entries.async_get_entry(config_entry_id)

    if not entry or entry.state != ConfigEntryState.LOADED:
        return None

    runtime_data = entry.runtime_data
    if not isinstance(runtime_data, MagicAreasRuntimeData):
        return None
    return runtime_data.coordinator.data


# Tests


async def test_reload_on_entity_area_change(
    hass: HomeAssistant,
    entities_binary_sensor_motion_all_areas_with_meta: dict[
        MockAreaIds, list[MockBinarySensor]
    ],
    init_integration_all_areas: list[MockConfigEntry],
) -> None:
    """Test that only corresponding areas reload when an entity changes state."""

    # Check all areas' snapshot timestamp
    area_snapshot_map: dict[str, datetime] = {}
    for area in NORMAL_AREAS:
        area_object = get_entry_by_area_name(hass, area)
        assert area_object
        area_snapshot_map[area] = area_object.updated_at

    # Simulate entity changing area_id (this triggers "all areas reload" logic in MagicArea)
    event_data: _EventEntityRegistryUpdatedData_Update = {
        "action": "update",
        "entity_id": "sensor.test",
        "changes": {"area_id": MockAreaIds.KITCHEN.value},
    }

    hass.bus.async_fire(EVENT_ENTITY_REGISTRY_UPDATED, event_data)
    await hass.async_block_till_done()
    await wait_until(
        hass,
        lambda: (
            (area_object := get_entry_by_area_name(hass, MockAreaIds.KITCHEN.value))
            is not None
            and area_snapshot_map[MockAreaIds.KITCHEN.value] != area_object.updated_at
        ),
    )

    # Check all areas' snapshot timestamp against the previous map
    for area in NORMAL_AREAS:
        area_object = get_entry_by_area_name(hass, area)
        assert area_object
        if area == MockAreaIds.KITCHEN.value:
            assert area_snapshot_map[area] != area_object.updated_at
        else:
            assert area_snapshot_map[area] == area_object.updated_at


async def test_meta_reload_from_single_reload(
    hass: HomeAssistant,
    entities_binary_sensor_motion_all_areas_with_meta: dict[
        MockAreaIds, list[MockBinarySensor]
    ],
    init_integration_all_areas: list[MockConfigEntry],
) -> None:
    """Test that the corresponding meta-areas reload when a child area reloads."""

    # Check all areas' snapshot timestamp
    area_snapshot_map: dict[str, datetime] = {}
    for area in ALL_AREAS:
        area_object = get_entry_by_area_name(hass, area)
        assert area_object
        area_snapshot_map[area] = area_object.updated_at

    # Simulate entity changing area_id (this triggers "all areas reload" logic in MagicArea)
    kitchen_motion_sensor_id = entities_binary_sensor_motion_all_areas_with_meta[
        MockAreaIds.KITCHEN
    ][0].entity_id

    event_data: _EventEntityRegistryUpdatedData_CreateRemove = {
        "action": "remove",
        "entity_id": kitchen_motion_sensor_id,
    }

    def _assert_has_reloaded(area_name: str) -> None:
        area_object = get_entry_by_area_name(hass, area_name)
        assert area_object
        assert area_object.updated_at != area_snapshot_map[area_name]

    def _assert_has_not_reloaded(area_name: str) -> None:
        area_object = get_entry_by_area_name(hass, area_name)
        assert area_object
        assert area_object.updated_at == area_snapshot_map[area_name]

    hass.bus.async_fire(EVENT_ENTITY_REGISTRY_UPDATED, event_data)
    await hass.async_block_till_done()
    await wait_until(
        hass,
        lambda: all(
            (area_object := get_entry_by_area_name(hass, area_name)) is not None
            and area_object.updated_at != area_snapshot_map[area_name]
            for area_name in (
                MockAreaIds.KITCHEN.value,
                MockAreaIds.INTERIOR.value,
                MockAreaIds.GLOBAL.value,
                MockAreaIds.FIRST_FLOOR.value,
            )
        ),
    )

    # Check corresponding area reloaded
    _assert_has_reloaded(MockAreaIds.KITCHEN.value)

    # Check corresponding meta-areas reloaded
    _assert_has_reloaded(MockAreaIds.INTERIOR.value)
    _assert_has_reloaded(MockAreaIds.GLOBAL.value)
    _assert_has_reloaded(MockAreaIds.FIRST_FLOOR.value)

    # Check other areas didn't reload
    _assert_has_not_reloaded(MockAreaIds.MASTER_BEDROOM.value)
    _assert_has_not_reloaded(MockAreaIds.BACKYARD.value)
    _assert_has_not_reloaded(MockAreaIds.EXTERIOR.value)
    _assert_has_not_reloaded(MockAreaIds.SECOND_FLOOR.value)
    _assert_has_not_reloaded(MockAreaIds.GROUND_LEVEL.value)
