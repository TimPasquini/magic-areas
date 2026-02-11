"""Tests for switch setup error handling."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core.area_runtime import AreaRuntime
from custom_components.magic_areas.core.entity_ids import EntityReferences
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.features import CONF_FEATURE_PRESENCE_HOLD
from custom_components.magic_areas.switch import async_setup_entry
from custom_components.magic_areas.models import MagicAreasRuntimeData


async def test_switch_setup_presence_hold_error(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test presence hold switch errors are handled."""
    area = MagicMock()
    area.is_meta.return_value = False
    area.name = "Test Area"
    area.magic_entities = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    area_config = AreaConfig(
        id="test_area",
        name="Test Area",
        slug="test_area",
        area_type="interior",
        config={},
        hass_config=config_entry,
        icon=None,
        floor_id=None,
    )
    area_runtime = AreaRuntime(
        entities={},
        magic_entities=area.magic_entities,
        states=set(),
        last_changed={},
        last_update_success=True,
        loaded_platforms=[],
        timestamp=None,
        reloading=False,
    )
    data = MagicAreasData(
        area=area,
        entities={},
        magic_entities=area.magic_entities,
        presence_sensors=[],
        active_areas=[],
        child_areas=[],
        config={},
        enabled_features={CONF_FEATURE_PRESENCE_HOLD},
        feature_configs={CONF_FEATURE_PRESENCE_HOLD: {}},
        entity_references=EntityReferences(),
        area_config=area_config,
        area_runtime=area_runtime,
        updated_at=datetime.now(UTC),
    )
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()
    config_entry.runtime_data = MagicAreasRuntimeData(
        area=area, coordinator=coordinator, listeners=[]
    )

    caplog.set_level("ERROR")
    with (
        patch(
            "custom_components.magic_areas.switch.PresenceHoldSwitch",
            side_effect=Exception("boom"),
        ),
    ):
        await async_setup_entry(hass, config_entry, MagicMock())

    assert "Error loading presence hold switch" in caplog.text
