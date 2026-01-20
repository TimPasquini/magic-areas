"""Tests for fan setup error handling."""

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.fan import async_setup_entry


async def test_fan_setup_handles_group_errors(hass: HomeAssistant) -> None:
    """Test fan group errors are handled."""
    area = MagicMock()
    area.has_feature.return_value = True
    area.has_entities.return_value = True
    area.entities = {"fan": [{"entity_id": "fan.test"}]}
    area.slug = "test-area"
    area.magic_entities = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})

    with (
        patch(
            "custom_components.magic_areas.fan.get_area_from_config_entry",
            return_value=area,
        ),
        patch(
            "custom_components.magic_areas.fan.AreaFanGroup",
            side_effect=Exception("boom"),
        ),
    ):
        await async_setup_entry(hass, config_entry, MagicMock())
