"""Contract tests for listener-native entity write behavior."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
from homeassistant.core import Context, Event, EventStateChangedData

from custom_components.magic_areas.binary_sensor.ble_tracker import (
    AreaBLETrackerBinarySensor,
)
from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    AreaWaspInABoxBinarySensor,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.light_groups.entities import AreaLightGroup
from custom_components.magic_areas.light_groups.runtime import (
    handle_group_state_change,
)


def _area_config() -> Mock:
    area_config = Mock()
    area_config.id = "kitchen"
    area_config.slug = "kitchen"
    area_config.name = "Kitchen"
    area_config.icon = None
    area_config.is_meta.return_value = False
    return area_config


def _coordinator_with_feature(
    feature_id: MagicAreasFeatures, feature_config: dict[str, object]
) -> Mock:
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.hass = MagicMock()
    coordinator.data = Mock()
    coordinator.data.feature_configs = {feature_id: feature_config}
    return coordinator


def test_ble_tracker_update_state_uses_scheduled_write_path() -> None:
    """BLE tracker keeps scheduler writes because callbacks may arrive off-loop."""
    coordinator = _coordinator_with_feature(
        MagicAreasFeatures.BLE_TRACKER, {"ble_tracker_entities": ["sensor.ble_1"]}
    )
    entity = AreaBLETrackerBinarySensor(_area_config(), coordinator)
    entity.hass = MagicMock()
    entity.hass.states.get.return_value = None

    with (
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        entity._update_state()

    mock_schedule.assert_called_once()
    mock_write.assert_not_called()


def test_wasp_apply_update_uses_immediate_write() -> None:
    """Wasp entity writes immediately after applying state-machine output."""
    coordinator = _coordinator_with_feature(
        MagicAreasFeatures.WASP_IN_A_BOX,
        {
            "wasp_in_a_box_delay": 0,
            "wasp_timeout": 0,
            "wasp_device_classes": ["motion"],
        },
    )
    entity = AreaWaspInABoxBinarySensor(_area_config(), coordinator)
    entity.hass = MagicMock()
    entity.hass.states.get.return_value = None

    update = Mock()
    update.cancel_timer = False
    update.request_timer = None
    update.is_present = True

    with (
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        entity._apply_update(update)

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()


def test_light_group_reset_control_uses_immediate_write() -> None:
    """Light-group reset runs on-loop and writes immediately."""
    group = object.__new__(AreaLightGroup)
    group.logger = MagicMock()
    group._attr_name = "Kitchen Overhead"
    with (
        patch.object(group, "_reset_control_state") as mock_reset_control_state,
        patch.object(group, "async_write_ha_state") as mock_async_write_ha_state,
    ):
        reset_control = AreaLightGroup.reset_control
        reset_control(group)

    mock_reset_control_state.assert_called_once()
    mock_async_write_ha_state.assert_called_once()


def test_light_group_state_change_uses_immediate_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Light-group dispatcher callback writes immediately on-loop."""
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.resolve_area_presence_states",
        lambda **_kwargs: ["occupied"],
    )

    group = SimpleNamespace(
        _area_id="kitchen",
        name="Kitchen Overhead",
        category="overhead",
        hass=SimpleNamespace(states=SimpleNamespace(get=lambda _entity_id: None)),
        logger=MagicMock(),
        _attr_extra_state_attributes={},
        _echo_state=CommandEchoState(
            owner_id="light_groups_kitchen_overhead_lights",
            controlling=True,
            awaiting_echo=True,
        ),
        _last_known_area_states=["occupied"],
        async_write_ha_state=MagicMock(),
        schedule_update_ha_state=MagicMock(),
    )

    def _set_echo_state(state: CommandEchoState) -> None:
        group._echo_state = state

    group._set_echo_state = _set_echo_state
    group._reset_control_state = MagicMock()
    group.controlling = True

    origin_event = Event(
        "state_changed",
        {
            "old_state": SimpleNamespace(
                state="off",
                attributes={},
            ),
            "new_state": SimpleNamespace(
                state="on",
                attributes={},
            ),
        },
    )
    context = Context()
    context.origin_event = origin_event
    event = Event[EventStateChangedData](
        "state_changed",
        {
            "entity_id": "light.magic_areas_light_groups_kitchen_overhead_lights",
            "old_state": None,
            "new_state": None,
        },
        context=context,
    )

    result = handle_group_state_change(group, event)

    assert result is True
    group.async_write_ha_state.assert_called_once()
    group.schedule_update_ha_state.assert_not_called()
