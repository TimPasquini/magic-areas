"""Tests for coordinator-driven availability."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.core_constants import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


async def test_entity_availability_reflects_coordinator(
    hass: HomeAssistant,
) -> None:
    """Entities report unavailable when coordinator updates fail."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    mock_config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    await init_integration_helper(hass, [mock_config_entry])

    entity = hass.data["entity_components"]["binary_sensor"].get_entity(
        "binary_sensor.magic_areas_presence_tracking_kitchen_area_state"
    )
    assert entity is not None

    area = mock_config_entry.runtime_data.area
    area.last_update_success = False
    assert entity.available is False

    area.last_update_success = True
    assert entity.available is True

    await shutdown_integration(hass, [mock_config_entry])
