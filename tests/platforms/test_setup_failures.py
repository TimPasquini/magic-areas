"""Tests for platform setup error handling and edge cases."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.core.runtime_model import AreaRuntime
from custom_components.magic_areas.core.runtime_model import EntityReferences
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.cover import async_setup_entry as cover_async_setup_entry
from custom_components.magic_areas.switch import async_setup_entry as switch_async_setup_entry
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.components import MagicAreasRuntimeData


# Switch setup tests


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
    area_runtime = AreaRuntime(last_update_success=True)
    data = MagicAreasData(
        entities={},
        magic_entities=area.magic_entities,
        presence_sensors=[],
        active_areas=[],
        child_areas=[],
        config={},
        enabled_features={MagicAreasFeatures.PRESENCE_HOLD},
        feature_configs={MagicAreasFeatures.PRESENCE_HOLD: {}},
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

    caplog.set_level("ERROR")
    with (
        patch(
            "custom_components.magic_areas.switch.PresenceHoldSwitch",
            side_effect=ValueError("boom"),
        ),
    ):
        await switch_async_setup_entry(hass, config_entry, MagicMock())

    assert "Error loading presence hold switch" in caplog.text


# Cover setup tests


async def test_cover_setup_no_entities(hass: HomeAssistant) -> None:
    """Test early return when no cover entities exist."""
    area = MagicMock()
    area.name = "Test Area"

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
    area_runtime = AreaRuntime(last_update_success=True)
    data = MagicAreasData(
        entities={},
        magic_entities={},
        presence_sensors=[],
        active_areas=[],
        child_areas=[],
        config={},
        enabled_features={MagicAreasFeatures.COVER_GROUPS},
        feature_configs={MagicAreasFeatures.COVER_GROUPS: {}},
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
    await cover_async_setup_entry(hass, config_entry, async_add_entities)
    async_add_entities.assert_not_called()
    assert async_add_entities.call_count == 0


async def test_cover_setup_cleanup_removed_entries(
    hass: HomeAssistant,
) -> None:
    """Test cleanup runs when entities are registered."""
    area = MagicMock()
    area.entities = {
        COVER_DOMAIN: [{"entity_id": "cover.test", "device_class": None}]
    }
    area.magic_entities = {COVER_DOMAIN: [MagicMock()]}
    area.hass = hass
    area.name = "Test Area"

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
    area_runtime = AreaRuntime(last_update_success=True)
    data = MagicAreasData(
        entities=area.entities,
        magic_entities=area.magic_entities,
        presence_sensors=[],
        active_areas=[],
        child_areas=[],
        config={},
        enabled_features={MagicAreasFeatures.COVER_GROUPS},
        feature_configs={MagicAreasFeatures.COVER_GROUPS: {}},
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

    with (
        patch(
            "custom_components.magic_areas.features.modules.cover_groups.AreaCoverGroup",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.magic_areas.helpers.cleanup_removed_entries"
        ) as cleanup_removed_entries,
    ):
        await cover_async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    assert async_add_entities.call_count == 1
    cleanup_removed_entries.assert_called_once()
