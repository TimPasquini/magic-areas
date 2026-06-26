"""Tests for fan setup error handling."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.core.runtime_model import AreaRuntime
from custom_components.magic_areas.core.runtime_model import EntityReferences
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.fan import async_setup_entry
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.components import MagicAreasRuntimeData


async def test_fan_setup_adds_no_custom_group_entities(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Fan platform should not add Magic Areas custom fan-group entities."""
    area = MagicMock()
    area.entities = {"fan": [{"entity_id": "fan.test"}]}
    area.slug = "test-area"
    area.magic_entities = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    area_config = AreaConfig(
        id="test_area",
        name="Test Area",
        slug="test-area",
        area_type="interior",
        config={},
        hass_config=config_entry,
        icon=None,
        floor_id=None,
    )
    area_runtime = AreaRuntime(last_update_success=True)
    data = MagicAreasData(
        entities=area.entities,
        magic_entities=area.magic_entities,
        presence_sensors=[],
        active_areas=[],
        child_areas=[],
        config={},
        enabled_features={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={MagicAreasFeatures.FAN_GROUPS: {}},
        group_registry=GroupRegistry(),
        entity_references=EntityReferences(),
        area_config=area_config,
        area_runtime=area_runtime,
        updated_at=datetime.now(UTC),
    )
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()
    config_entry.runtime_data = MagicAreasRuntimeData(
        coordinator=coordinator, listeners=[]
    )

    async_add_entities = MagicMock()
    caplog.set_level("ERROR")
    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_not_called()
    assert "Error creating fan group" not in caplog.text
