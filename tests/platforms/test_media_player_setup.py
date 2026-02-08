"""Test media player platform setup with coordinator data conditions."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.media_player import async_setup_entry
from custom_components.magic_areas.const import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import get_basic_config_entry_data


@pytest.mark.asyncio
async def test_media_player_setup_calls_refresh_when_coordinator_data_none(
    hass: HomeAssistant,
) -> None:
    """Test that async_setup_entry calls coordinator.async_refresh() when data is None."""
    # Create a mock config entry
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)

    # Create mock runtime_data with coordinator that has None data
    mock_coordinator = AsyncMock()
    mock_coordinator.data = None  # Initially None
    mock_coordinator.async_refresh = AsyncMock()

    # After refresh, still None
    mock_coordinator.async_refresh.side_effect = lambda: (
        setattr(mock_coordinator, 'data', None),
        None
    )

    mock_runtime_data = MagicMock()
    mock_runtime_data.coordinator = mock_coordinator

    config_entry.runtime_data = mock_runtime_data

    # Call async_setup_entry with no entities added
    async_add_entities: AddEntitiesCallback = AsyncMock()

    # Call the function
    result = await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify that async_refresh was called (line 51)
    mock_coordinator.async_refresh.assert_called_once()

    # Verify that no entities were added (because data remained None)
    async_add_entities.assert_not_called()

    # Result should be None (early return at line 55)
    assert result is None
