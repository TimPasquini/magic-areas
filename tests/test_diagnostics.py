"""Test the diagnostics module."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.diagnostics import async_get_config_entry_diagnostics
from tests.helpers import (
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

    await shutdown_integration(hass, [mock_config_entry])
