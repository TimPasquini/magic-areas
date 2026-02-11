"""Tests for coordinator-driven availability."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import DOMAIN
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
    from unittest.mock import AsyncMock, patch

    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    mock_config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    await init_integration_helper(hass, [mock_config_entry])

    entity = hass.data["entity_components"]["binary_sensor"].get_entity(
        "binary_sensor.magic_areas_presence_tracking_kitchen_area_state"
    )
    assert entity is not None

    # Entity should be available initially
    assert entity.available is True

    # Mock coordinator's update to fail
    coordinator = mock_config_entry.runtime_data.coordinator
    with patch.object(coordinator, "_async_update_data", side_effect=Exception("Test failure")):
        await coordinator.async_refresh()

    # Entity should now be unavailable
    assert entity.available is False

    # Mock coordinator's update to succeed
    with patch.object(coordinator, "_async_update_data", new_callable=AsyncMock) as mock_update:
        # Set up mock to return valid data
        mock_update.return_value = coordinator.data
        await coordinator.async_refresh()

    # Entity should be available again
    assert entity.available is True

    await shutdown_integration(hass, [mock_config_entry])
