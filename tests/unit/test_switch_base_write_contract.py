"""Contract tests for switch write behavior."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import ResettableSwitchBase, SwitchBase


def _mock_area_config() -> Mock:
    area_config = Mock()
    area_config.id = "kitchen"
    area_config.slug = "kitchen"
    area_config.name = "Kitchen"
    area_config.icon = None
    area_config.is_meta.return_value = False
    return area_config


def _mock_coordinator() -> Mock:
    coordinator = Mock()
    coordinator.last_update_success = True
    coordinator.data = None
    return coordinator


class _TestSwitch(SwitchBase):
    feature_id = MagicAreasFeatures.PRESENCE_HOLD


class _TestResettableSwitch(ResettableSwitchBase):
    feature_id = MagicAreasFeatures.PRESENCE_HOLD


@pytest.mark.asyncio
async def test_switch_base_turn_on_uses_single_write_path() -> None:
    """SwitchBase turns on via async_write_ha_state (no scheduler call)."""
    switch = _TestSwitch(_mock_area_config(), _mock_coordinator())
    with (
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch.object(switch, "schedule_update_ha_state") as mock_schedule,
    ):
        await switch.async_turn_on()

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()


@pytest.mark.asyncio
async def test_switch_base_added_to_hass_uses_single_write_path() -> None:
    """SwitchBase setup writes once and does not schedule a second write."""
    switch = _TestSwitch(_mock_area_config(), _mock_coordinator())

    with (
        patch(
            "homeassistant.helpers.restore_state.RestoreEntity.async_added_to_hass",
            new=AsyncMock(),
        ),
        patch.object(switch, "async_get_last_state", new=AsyncMock(return_value=None)),
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch.object(switch, "schedule_update_ha_state") as mock_schedule,
    ):
        await switch.async_added_to_hass()

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()


@pytest.mark.asyncio
async def test_switch_base_turn_off_uses_single_write_path() -> None:
    """SwitchBase turns off via async_write_ha_state (no scheduler call)."""
    switch = _TestSwitch(_mock_area_config(), _mock_coordinator())
    with (
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch.object(switch, "schedule_update_ha_state") as mock_schedule,
    ):
        await switch.async_turn_off()

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()


@pytest.mark.asyncio
async def test_resettable_switch_turn_on_uses_single_write_path() -> None:
    """ResettableSwitchBase turns on via async_write_ha_state."""
    switch = _TestResettableSwitch(_mock_area_config(), _mock_coordinator(), timeout=0)
    with (
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch.object(switch, "schedule_update_ha_state") as mock_schedule,
    ):
        await switch.async_turn_on()

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()


@pytest.mark.asyncio
async def test_resettable_switch_turn_off_uses_single_write_path() -> None:
    """ResettableSwitchBase turns off via async_write_ha_state."""
    switch = _TestResettableSwitch(_mock_area_config(), _mock_coordinator(), timeout=0)
    with (
        patch.object(switch, "async_write_ha_state") as mock_write,
        patch.object(switch, "schedule_update_ha_state") as mock_schedule,
    ):
        await switch.async_turn_off()

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()


def test_resettable_switch_clear_timers_cancels_active_timer() -> None:
    """Removal cleanup should cancel the active timeout callback."""
    switch = _TestResettableSwitch(_mock_area_config(), _mock_coordinator(), timeout=1)
    cancel = Mock()
    switch._timeout_callback = cancel

    switch._clear_timers()

    cancel.assert_called_once_with()


@pytest.mark.asyncio
async def test_resettable_switch_timeout_turns_off_active_switch() -> None:
    """The HA timer callback should turn off an active resettable switch."""
    switch = _TestResettableSwitch(_mock_area_config(), _mock_coordinator(), timeout=1)
    switch._attr_is_on = True
    with patch.object(switch, "async_turn_off", new=AsyncMock()) as turn_off:
        await switch._timeout_turn_off(None)

    turn_off.assert_awaited_once_with()
