"""Test the diagnostics module."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.diagnostics import async_get_config_entry_diagnostics
from custom_components.magic_areas.const import DOMAIN
from tests.const import DEFAULT_MOCK_AREA
from tests.helpers import (
    get_basic_config_entry_data,
    init_integration as init_integration_helper,
    shutdown_integration,
)


async def test_diagnostics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test diagnostics."""
    await init_integration_helper(hass, [mock_config_entry])
    await hass.async_start()
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert "entry" in diagnostics
    assert "area" in diagnostics

    # Check redaction
    assert diagnostics["entry"]["data"]["id"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["name"] == "**REDACTED**"

    area_diag = diagnostics["area"]
    assert area_diag["name"] == "kitchen"
    assert area_diag["id"] == "kitchen"
    assert area_diag["type"] == "interior"
    assert isinstance(area_diag["states"], list)
    assert area_diag["meta"] is False
    assert isinstance(area_diag["entities"], dict)
    assert isinstance(area_diag["magic_entities"], dict)
    assert area_diag["config"]["id"] == "**REDACTED**"
    assert area_diag["config"]["name"] == "**REDACTED**"
    assert "updated_at" in area_diag

    await shutdown_integration(hass, [mock_config_entry])


async def test_diagnostics_coordinator_data_unavailable(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics when coordinator data is unavailable."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    config_entry = MockConfigEntry(domain=DOMAIN, data=data)
    config_entry.add_to_hass(hass)

    # Mock coordinator that returns None for data
    from custom_components.magic_areas.models import MagicAreasRuntimeData

    mock_coordinator = AsyncMock()
    mock_coordinator.data = None
    mock_coordinator.async_refresh = AsyncMock()  # Returns None implicitly

    # Create a minimal runtime data mock
    runtime_data = MagicMock()
    runtime_data.coordinator = mock_coordinator
    config_entry.runtime_data = runtime_data

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    # Should return error response when data unavailable
    assert "entry" in diagnostics
    assert "area" in diagnostics
    assert diagnostics["area"] == {"error": "Coordinator data unavailable"}
