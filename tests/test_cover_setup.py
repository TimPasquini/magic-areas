"""Tests for cover setup paths."""

from unittest.mock import MagicMock, patch

from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.cover import async_setup_entry


async def test_cover_setup_no_entities(hass: HomeAssistant) -> None:
    """Test early return when no cover entities exist."""
    area = MagicMock()
    area.has_feature.return_value = True
    area.has_entities.return_value = False
    area.name = "Test Area"

    config_entry = MockConfigEntry(domain=DOMAIN, data={})

    with patch(
        "custom_components.magic_areas.cover.get_area_from_config_entry",
        return_value=area,
    ):
        await async_setup_entry(hass, config_entry, MagicMock())


async def test_cover_setup_cleanup_removed_entries(hass: HomeAssistant) -> None:
    """Test cleanup runs when entities are registered."""
    area = MagicMock()
    area.has_feature.return_value = True
    area.has_entities.return_value = True
    area.entities = {COVER_DOMAIN: [{"entity_id": "cover.test", "device_class": None}]}
    area.magic_entities = {COVER_DOMAIN: [MagicMock()]}
    area.hass = hass
    area.name = "Test Area"

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    async_add_entities = MagicMock()

    with (
        patch(
            "custom_components.magic_areas.cover.get_area_from_config_entry",
            return_value=area,
        ),
        patch("custom_components.magic_areas.cover.AreaCoverGroup", return_value=MagicMock()),
        patch(
            "custom_components.magic_areas.cover.cleanup_removed_entries"
        ) as cleanup_removed_entries,
    ):
        await async_setup_entry(hass, config_entry, async_add_entities)

    cleanup_removed_entries.assert_called_once()
