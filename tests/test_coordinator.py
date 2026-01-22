"""Tests for the Magic Areas coordinator."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.coordinator import (
    MagicAreasCoordinator,
    MagicAreasData,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.magic_areas.models import MagicAreasConfigEntry


async def test_coordinator_builds_snapshot(
    hass: HomeAssistant, init_integration: MagicAreasConfigEntry
) -> None:
    """Test coordinator data mirrors area snapshot."""
    entry = init_integration
    coordinator = entry.runtime_data.coordinator

    assert coordinator.data is not None
    data: MagicAreasData = coordinator.data
    assert data.area == entry.runtime_data.area
    assert data.entities == entry.runtime_data.area.entities
    assert data.magic_entities == entry.runtime_data.area.magic_entities
    assert data.presence_sensors == entry.runtime_data.area.get_presence_sensors()


async def test_coordinator_update_failure(
    hass: HomeAssistant, mock_config_entry: MagicAreasConfigEntry
) -> None:
    """Test coordinator handles update failures."""
    area = MagicMock()
    area.load_entities = AsyncMock(side_effect=RuntimeError("boom"))
    area.entities = {}
    area.magic_entities = {}
    area.config = {}
    area.get_presence_sensors.return_value = []

    coordinator = MagicAreasCoordinator(hass, area, mock_config_entry)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_refresh_updates_snapshot(
    hass: HomeAssistant, mock_config_entry: MagicAreasConfigEntry
) -> None:
    """Test coordinator refresh updates data snapshot."""
    area = MagicMock()
    area.entities = {}
    area.magic_entities = {}
    area.config = {}
    area.get_presence_sensors.return_value = ["binary_sensor.presence_one"]

    async def _load_entities() -> None:
        area.entities = {
            "sensor": [
                {
                    "entity_id": "sensor.illuminance_one",
                    "device_class": "illuminance",
                    "unit_of_measurement": "lx",
                }
            ]
        }
        area.magic_entities = {"sensor": [{"entity_id": "sensor.magic_one"}]}

    area.load_entities = AsyncMock(side_effect=_load_entities)

    coordinator = MagicAreasCoordinator(hass, area, mock_config_entry)
    await coordinator.async_refresh()
    assert coordinator.data is not None
    first_updated = coordinator.data.updated_at
    assert coordinator.data.entities == area.entities
    assert coordinator.data.magic_entities == area.magic_entities
    assert coordinator.data.presence_sensors == ["binary_sensor.presence_one"]

    area.get_presence_sensors.return_value = ["binary_sensor.presence_two"]
    await coordinator.async_refresh()
    assert coordinator.data is not None
    assert coordinator.data.updated_at >= first_updated
    assert coordinator.data.presence_sensors == ["binary_sensor.presence_two"]
