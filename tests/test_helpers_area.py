"""Tests for area helper utilities."""

from homeassistant.const import ATTR_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.helpers.area import (
    get_area_from_config_entry,
    get_magic_area_for_config_entry,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import get_basic_config_entry_data


async def test_get_magic_area_for_config_entry_missing_area(
    hass: HomeAssistant,
) -> None:
    """Test returning None when the area is missing."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data[ATTR_ID] = "missing_area"
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    assert get_magic_area_for_config_entry(hass, config_entry) is None


async def test_get_area_from_config_entry_without_runtime_data(
    hass: HomeAssistant,
) -> None:
    """Test returning None when runtime data is missing."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)

    assert get_area_from_config_entry(hass, config_entry) is None
