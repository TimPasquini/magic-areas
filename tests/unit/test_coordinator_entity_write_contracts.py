"""Contract tests for coordinator-native entity write behavior."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.binary_sensor.aggregate_factory import (
    AreaAggregateBinarySensor,
)
from custom_components.magic_areas.sensor import AreaAggregateSensor


def _area_config() -> Mock:
    area_config = Mock()
    area_config.id = "kitchen"
    area_config.slug = "kitchen"
    area_config.name = "Kitchen"
    area_config.icon = None
    area_config.is_meta.return_value = False
    return area_config


def _coordinator(hass: HomeAssistant) -> Mock:
    coordinator = Mock()
    coordinator.hass = hass
    coordinator.last_update_success = True
    coordinator.data = None
    return coordinator


@pytest.mark.asyncio
async def test_aggregate_binary_sensor_group_uses_single_write_path(
    hass: HomeAssistant,
) -> None:
    """Aggregate binary groups should write once during setup."""
    entity = AreaAggregateBinarySensor(
        _area_config(),
        _coordinator(hass),
        BinarySensorDeviceClass.MOTION,
        ["binary_sensor.motion_1"],
    )
    entity.hass = hass

    with (
        patch(
            "homeassistant.helpers.restore_state.RestoreEntity.async_added_to_hass",
            new=AsyncMock(),
        ),
        patch.object(entity, "_async_setup_group", new=AsyncMock()),
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        await entity.async_added_to_hass()

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()


@pytest.mark.asyncio
async def test_aggregate_sensor_group_uses_single_write_path(
    hass: HomeAssistant,
) -> None:
    """Aggregate sensors should write once during setup."""
    entity = AreaAggregateSensor(
        _area_config(),
        _coordinator(hass),
        "temperature",
        ["sensor.temp_1"],
        "C",
    )
    entity.hass = hass

    with (
        patch(
            "homeassistant.helpers.restore_state.RestoreEntity.async_added_to_hass",
            new=AsyncMock(),
        ),
        patch.object(entity, "_async_setup_group", new=AsyncMock()),
        patch.object(entity, "async_write_ha_state") as mock_write,
        patch.object(entity, "schedule_update_ha_state") as mock_schedule,
    ):
        await entity.async_added_to_hass()

    mock_write.assert_called_once()
    mock_schedule.assert_not_called()
