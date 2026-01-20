"""Tests for switch setup error handling."""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch import async_setup_entry


async def test_switch_setup_presence_hold_error(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test presence hold switch errors are handled."""
    area = MagicMock()
    area.has_feature.side_effect = (
        lambda feature: feature == MagicAreasFeatures.PRESENCE_HOLD
    )
    area.is_meta.return_value = False
    area.name = "Test Area"
    area.magic_entities = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})

    caplog.set_level("ERROR")
    with (
        patch(
            "custom_components.magic_areas.switch.get_area_from_config_entry",
            return_value=area,
        ),
        patch(
            "custom_components.magic_areas.switch.PresenceHoldSwitch",
            side_effect=Exception("boom"),
        ),
    ):
        await async_setup_entry(hass, config_entry, MagicMock())

    assert "Error loading presence hold switch" in caplog.text
