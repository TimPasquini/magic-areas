"""Tests for cover setup paths."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.cover import async_setup_entry
from custom_components.magic_areas.features import CONF_FEATURE_COVER_GROUPS
from custom_components.magic_areas.models import MagicAreasRuntimeData


async def test_cover_setup_no_entities(hass: HomeAssistant) -> None:
    """Test early return when no cover entities exist."""
    area = MagicMock()
    area.name = "Test Area"

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    data = MagicAreasData(
        area=area,
        entities={},
        magic_entities={},
        presence_sensors=[],
        active_areas=[],
        config={},
        enabled_features={CONF_FEATURE_COVER_GROUPS},
        feature_configs={CONF_FEATURE_COVER_GROUPS: {}},
        updated_at=datetime.now(UTC),
    )
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()
    config_entry.runtime_data = MagicAreasRuntimeData(
        area=area, coordinator=coordinator, listeners=[]
    )

    await async_setup_entry(hass, config_entry, MagicMock())


async def test_cover_setup_cleanup_removed_entries(hass: HomeAssistant) -> None:
    """Test cleanup runs when entities are registered."""
    area = MagicMock()
    area.entities = {COVER_DOMAIN: [{"entity_id": "cover.test", "device_class": None}]}
    area.magic_entities = {COVER_DOMAIN: [MagicMock()]}
    area.hass = hass
    area.name = "Test Area"

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    data = MagicAreasData(
        area=area,
        entities=area.entities,
        magic_entities=area.magic_entities,
        presence_sensors=[],
        active_areas=[],
        config={},
        enabled_features={CONF_FEATURE_COVER_GROUPS},
        feature_configs={CONF_FEATURE_COVER_GROUPS: {}},
        updated_at=datetime.now(UTC),
    )
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.async_refresh = AsyncMock()
    config_entry.runtime_data = MagicAreasRuntimeData(
        area=area, coordinator=coordinator, listeners=[]
    )
    async_add_entities = MagicMock()

    with (
        patch(
            "custom_components.magic_areas.cover.AreaCoverGroup",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.magic_areas.cover.cleanup_removed_entries"
        ) as cleanup_removed_entries,
    ):
        await async_setup_entry(hass, config_entry, async_add_entities)

    cleanup_removed_entries.assert_called_once()
