"""Contract tests for presence entity write behavior."""

from unittest.mock import MagicMock, Mock, patch

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.binary_sensor.presence import (
    AreaStateBinarySensor,
    MetaAreaStateBinarySensor,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_SECONDARY_STATES,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
)
from custom_components.magic_areas.const import ATTR_STATES, DOMAIN
from custom_components.magic_areas.core.runtime_model import (
    build_presence_tracking_unique_id,
)
from custom_components.magic_areas.enums import CalculationMode


def _area_config() -> Mock:
    area_config = Mock()
    area_config.id = "kitchen"
    area_config.slug = "kitchen"
    area_config.name = "Kitchen"
    area_config.icon = None
    area_config.config = {}
    area_config.is_meta.return_value = False
    return area_config


def _coordinator() -> Mock:
    coordinator = Mock()
    coordinator.hass = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = Mock()
    coordinator.data.presence_sensors = ["binary_sensor.motion_1"]
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    return coordinator


def _meta_area_config() -> Mock:
    area_config = _area_config()
    area_config.id = "global"
    area_config.slug = "global"
    area_config.name = "Global"
    area_config.config = {
        CONF_SECONDARY_STATES: {
            CONF_SECONDARY_STATES_CALCULATION_MODE: CalculationMode.ANY
        }
    }
    area_config.is_meta.return_value = True
    return area_config


def test_area_state_changed_uses_scheduled_write_path() -> None:
    """Dispatcher-driven area state changes keep scheduler writes."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}

    with (
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        entity._area_state_changed(
            "kitchen",
            ([AreaStates.OCCUPIED.value], [], [AreaStates.OCCUPIED.value]),
        )

    mock_schedule.assert_called_once()
    mock_write.assert_not_called()


def test_coordinator_update_uses_scheduled_write_path() -> None:
    """Coordinator refresh listener keeps scheduler writes."""
    coordinator = _coordinator()
    entity = AreaStateBinarySensor(_area_config(), coordinator)
    entity._attr_extra_state_attributes = {}
    entity._sensors = []
    coordinator.data.presence_sensors = ["binary_sensor.motion_1"]

    with (
        patch.object(entity, "_track_presence_sensor_listener") as mock_track,
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        entity._handle_coordinator_update()

    mock_track.assert_called_once_with(["binary_sensor.motion_1"])
    mock_schedule.assert_called_once()
    mock_write.assert_not_called()


def test_apply_state_projection_updates_cached_state_and_attributes() -> None:
    """Projection helper owns binary state refresh from current states."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}

    entity._apply_state_projection([AreaStates.OCCUPIED.value])

    assert entity._current_states == [AreaStates.OCCUPIED.value]
    assert entity._attr_is_on is True
    assert entity._attr_extra_state_attributes["states"] == [
        AreaStates.OCCUPIED.value
    ]
    assert entity._attr_extra_state_attributes["active_states"] == "Occupied"
    assert entity._attr_extra_state_attributes["state_occupied"] == "on"
    assert entity._attr_extra_state_attributes["state_sleep"] == "off"


def test_apply_state_projection_exposes_ordered_state_summary_and_flags() -> None:
    """Projection metadata should expose ordered states + active/inactive flags."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}

    entity._apply_state_projection(
        [AreaStates.BRIGHT.value, AreaStates.OCCUPIED.value, AreaStates.SLEEP.value]
    )

    assert entity._attr_extra_state_attributes["states"] == [
        AreaStates.OCCUPIED.value,
        AreaStates.SLEEP.value,
        AreaStates.BRIGHT.value,
    ]
    assert (
        entity._attr_extra_state_attributes["active_states"]
        == "Occupied, Sleep, Bright"
    )
    assert entity._attr_extra_state_attributes["state_occupied"] == "on"
    assert entity._attr_extra_state_attributes["state_sleep"] == "on"
    assert entity._attr_extra_state_attributes["state_bright"] == "on"
    assert entity._attr_extra_state_attributes["state_extended"] == "off"


def test_runtime_states_merge_into_visible_area_state_attributes() -> None:
    """Feature-published runtime states should appear in area-state metadata."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}
    entity._apply_state_projection([AreaStates.OCCUPIED.value])

    with (
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
        patch("custom_components.magic_areas.binary_sensor.presence.dispatcher_send"),
    ):
        entity._runtime_states_changed(
            "kitchen",
            "fan_groups",
            [AreaStates.HUMID.value, AreaStates.ODOR.value],
        )

    assert entity._attr_extra_state_attributes["states"] == [
        AreaStates.OCCUPIED.value,
        AreaStates.HUMID.value,
        AreaStates.ODOR.value,
    ]
    assert (
        entity._attr_extra_state_attributes["active_states"]
        == "Occupied, Humid, Odor"
    )
    assert entity._attr_extra_state_attributes["state_humid"] == "on"
    assert entity._attr_extra_state_attributes["state_odor"] == "on"
    mock_schedule.assert_called_once()


def test_runtime_states_clear_when_source_publishes_empty_state_list() -> None:
    """Runtime-state sources can clear their visible area states."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}
    entity._apply_state_projection([AreaStates.OCCUPIED.value])
    with (
        patch.object(entity, "schedule_update_ha_state"),
        patch("custom_components.magic_areas.binary_sensor.presence.dispatcher_send"),
    ):
        entity._runtime_states_changed(
            "kitchen",
            "fan_groups",
            [AreaStates.HOT.value],
        )
        entity._runtime_states_changed("kitchen", "fan_groups", [])

    assert entity._attr_extra_state_attributes["states"] == [
        AreaStates.OCCUPIED.value
    ]
    assert entity._attr_extra_state_attributes["state_hot"] == "off"


def test_apply_sensor_inventory_update_tracks_added_sensors() -> None:
    """Inventory helper owns snapshot-driven presence sensor reconciliation."""
    entity = AreaStateBinarySensor(_area_config(), _coordinator())
    entity._attr_extra_state_attributes = {}
    entity._sensors = []

    with patch.object(entity, "_track_presence_sensor_listener") as mock_track:
        entity._apply_sensor_inventory_update(["binary_sensor.motion_1"])

    assert entity._sensors == ["binary_sensor.motion_1"]
    mock_track.assert_called_once_with(["binary_sensor.motion_1"])


def test_meta_secondary_states_read_registered_active_child_entities(
    hass: HomeAssistant,
) -> None:
    """Meta secondary states should aggregate valid active child attributes."""
    coordinator = _coordinator()
    coordinator.hass = hass
    coordinator.data.presence_sensors = []
    coordinator.data.active_areas = ["kitchen", "bedroom", "office", "missing"]
    entity = MetaAreaStateBinarySensor(_meta_area_config(), coordinator)
    entity.hass = hass
    registry = er.async_get(hass)

    child_entity_ids: dict[str, str] = {}
    for area_id in ("kitchen", "bedroom", "office"):
        entry = registry.async_get_or_create(
            domain=BINARY_SENSOR_DOMAIN,
            platform=DOMAIN,
            unique_id=build_presence_tracking_unique_id(area_id=area_id),
            suggested_object_id=f"magic_areas_presence_tracking_{area_id}_area_state",
        )
        child_entity_ids[area_id] = entry.entity_id

    hass.states.async_set(
        child_entity_ids["kitchen"],
        "on",
        {ATTR_STATES: [AreaStates.DARK, AreaStates.SLEEP]},
    )
    hass.states.async_set(
        child_entity_ids["bedroom"],
        "off",
        {ATTR_STATES: "invalid"},
    )

    assert entity._get_secondary_states() == [AreaStates.SLEEP, AreaStates.DARK]
