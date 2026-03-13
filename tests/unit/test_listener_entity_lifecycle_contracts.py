"""Contract tests for listener-native entity lifecycle cleanup."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.magic_areas.binary_sensor.ble_tracker import (
    AreaBLETrackerBinarySensor,
)
from custom_components.magic_areas.binary_sensor.presence import AreaStateBinarySensor
from custom_components.magic_areas.binary_sensor.wasp_in_a_box import (
    AreaWaspInABoxBinarySensor,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import (
    ControlSwitchBase,
    ResettableSwitchBase,
)


def _area_config() -> Mock:
    area_config = Mock()
    area_config.id = "kitchen"
    area_config.slug = "kitchen"
    area_config.name = "Kitchen"
    area_config.icon = None
    area_config.config = {}
    area_config.is_meta.return_value = False
    return area_config


def _coordinator(
    feature_id: MagicAreasFeatures,
    feature_config: dict[str, object] | None = None,
) -> Mock:
    coordinator = Mock()
    coordinator.hass = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = Mock()
    coordinator.data.feature_configs = {feature_id: feature_config or {}}
    return coordinator


class _TestResettableSwitch(ResettableSwitchBase):
    feature_id = MagicAreasFeatures.PRESENCE_HOLD


class _TestControlSwitch(ControlSwitchBase):
    feature_id = MagicAreasFeatures.CLIMATE_CONTROL


@pytest.mark.asyncio
async def test_ble_tracker_cleanup_clears_listener_registry() -> None:
    """BLE tracker should always clean registered listeners on unload."""
    entity = AreaBLETrackerBinarySensor(
        _area_config(),
        _coordinator(
            MagicAreasFeatures.BLE_TRACKER,
            {"ble_tracker_entities": ["sensor.ble_1"]},
        ),
    )
    remove_callback = Mock()
    entity._listener_registry.track("sensor_state_change", remove_callback)

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_will_remove_from_hass",
        new=AsyncMock(),
    ):
        await entity.async_will_remove_from_hass()

    remove_callback.assert_called_once()
    assert entity._listener_registry.count == 0


@pytest.mark.asyncio
async def test_presence_cleanup_clears_timer_and_listeners() -> None:
    """Presence entities should clear tracked listeners and timeout callbacks on unload."""
    entity = AreaStateBinarySensor(
        _area_config(),
        _coordinator(MagicAreasFeatures.PRESENCE_TRACKING),
    )
    remove_callback = Mock()
    clear_timeout = Mock()
    entity._listener_registry.track("presence_sensor_state_change", remove_callback)
    entity._clear_timeout_callback = clear_timeout
    entity._listener_registry.track("cleanup_timers", entity._remove_clear_timeout)

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_will_remove_from_hass",
        new=AsyncMock(),
    ):
        await entity.async_will_remove_from_hass()

    remove_callback.assert_called_once()
    clear_timeout.assert_called_once()
    assert entity._listener_registry.count == 0


@pytest.mark.asyncio
async def test_wasp_cleanup_removes_timer_and_listeners() -> None:
    """Wasp cleanup should remove timer and listener registrations."""
    entity = AreaWaspInABoxBinarySensor(
        _area_config(),
        _coordinator(
            MagicAreasFeatures.WASP_IN_A_BOX,
            {
                "wasp_in_a_box_delay": 0,
                "wasp_timeout": 1,
                "wasp_device_classes": ["motion"],
            },
        ),
    )
    remove_callback = Mock()
    timer = AsyncMock()
    entity._listener_registry.track("wasp_sensor_state_change", remove_callback)
    entity._wasp_timer = timer

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_will_remove_from_hass",
        new=AsyncMock(),
    ):
        await entity.async_will_remove_from_hass()

    timer.async_remove.assert_awaited_once()
    remove_callback.assert_called_once()
    assert entity._listener_registry.count == 0


@pytest.mark.asyncio
async def test_resettable_switch_cleanup_clears_timer_callback() -> None:
    """Resettable switches should clear timeout cleanup callbacks on unload."""
    switch = _TestResettableSwitch(
        _area_config(),
        _coordinator(MagicAreasFeatures.PRESENCE_HOLD),
        timeout=1,
    )
    timeout_remove = Mock()
    switch._timeout_callback = timeout_remove

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_will_remove_from_hass",
        new=AsyncMock(),
    ):
        await switch.async_will_remove_from_hass()

    timeout_remove.assert_called_once()
    assert switch._listener_registry.count == 0


@pytest.mark.asyncio
async def test_control_switch_cleanup_clears_registered_listeners() -> None:
    """Control switches should clear tracked listeners on unload."""
    switch = _TestControlSwitch(
        _area_config(),
        _coordinator(MagicAreasFeatures.CLIMATE_CONTROL),
    )
    remove_callback = Mock()
    switch._listener_registry.track("area_state_dispatcher", remove_callback)

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_will_remove_from_hass",
        new=AsyncMock(),
    ):
        await switch.async_will_remove_from_hass()

    remove_callback.assert_called_once()
    assert switch._listener_registry.count == 0
