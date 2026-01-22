"""Tests for fan setup error handling."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.fan import async_setup_entry
from custom_components.magic_areas.features import CONF_FEATURE_FAN_GROUPS
from custom_components.magic_areas.models import MagicAreasRuntimeData


async def test_fan_setup_handles_group_errors(hass: HomeAssistant) -> None:
    """Test fan group errors are handled."""
    area = MagicMock()
    area.entities = {"fan": [{"entity_id": "fan.test"}]}
    area.slug = "test-area"
    area.magic_entities = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    data = MagicAreasData(
        area=area,
        entities=area.entities,
        magic_entities=area.magic_entities,
        presence_sensors=[],
        active_areas=[],
        config={},
        enabled_features={CONF_FEATURE_FAN_GROUPS},
        feature_configs={CONF_FEATURE_FAN_GROUPS: {}},
        updated_at=datetime.now(UTC),
    )
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()
    config_entry.runtime_data = MagicAreasRuntimeData(
        area=area, coordinator=coordinator, listeners=[]
    )

    with (
        patch(
            "custom_components.magic_areas.fan.AreaFanGroup",
            side_effect=Exception("boom"),
        ),
    ):
        await async_setup_entry(hass, config_entry, MagicMock())
