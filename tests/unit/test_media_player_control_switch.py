"""Unit tests for MediaPlayerControlSwitch with mocked dependencies."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.switch import (
    MediaPlayerControlSwitch,
)


@pytest.fixture
def mock_area_config() -> AreaConfig:
    """Create a mock AreaConfig."""
    config = MagicMock(spec=AreaConfig)
    config.id = "test_area"
    config.name = "Test Area"
    config.slug = "test_area"
    config.config = {}
    config.icon = None
    config.floor_id = None
    config.area_type = "interior"
    return cast(AreaConfig, config)


@pytest.fixture
def mock_coordinator() -> MagicAreasCoordinator:
    """Create a mock coordinator."""
    coordinator = AsyncMock()
    coordinator.data = MagicMock()
    coordinator.data.entity_references = MagicMock()
    coordinator.data.entity_references.media_player_group = "media_player.test_group"
    return cast(MagicAreasCoordinator, coordinator)


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Create a mock hass object."""
    hass = AsyncMock()
    hass.states = MagicMock()
    hass.services = AsyncMock()
    hass.async_create_task = MagicMock()
    return cast(HomeAssistant, hass)


@pytest.mark.asyncio
async def test_area_state_changed_noop_when_no_state_delta(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No new/lost states should skip decision mapping and execution."""
    switch = MediaPlayerControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch.media_player_group_id = "media_player.test_group"

    execute_mock = AsyncMock()
    decision_mock = MagicMock()

    switch.policy = MagicMock()
    switch.policy.evaluate = decision_mock
    monkeypatch.setattr(switch, "_execute_decision", execute_mock)
    await switch.area_state_changed("test_area", ([], [], ["occupied"]))

    decision_mock.assert_not_called()
    execute_mock.assert_not_awaited()
