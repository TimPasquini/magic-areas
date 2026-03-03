"""Unit tests for MediaPlayerControlSwitch with mocked dependencies."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.switch.media_player_control import (
    MediaPlayerControlSwitch,
)


@pytest.fixture
def mock_area_config() -> Any:
    """Create a mock AreaConfig."""
    config = MagicMock(spec=AreaConfig)
    config.id = "test_area"
    config.name = "Test Area"
    config.slug = "test_area"
    config.config = {}
    config.icon = None
    config.floor_id = None
    config.area_type = "interior"
    return config


@pytest.fixture
def mock_coordinator() -> Any:
    """Create a mock coordinator."""
    coordinator = AsyncMock()
    coordinator.data = MagicMock()
    coordinator.data.entity_references = MagicMock()
    coordinator.data.entity_references.media_player_group = "media_player.test_group"
    return coordinator


@pytest.fixture
def mock_hass() -> Any:
    """Create a mock hass object."""
    hass = AsyncMock()
    hass.states = MagicMock()
    hass.services = AsyncMock()
    hass.async_create_task = MagicMock()
    return hass


@pytest.mark.asyncio
async def test_area_state_changed_noop_when_no_state_delta(
    mock_area_config: Any,
    mock_coordinator: Any,
    mock_hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No new/lost states should skip decision mapping and execution."""
    switch = MediaPlayerControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_is_on = True
    switch.media_player_group_id = "media_player.test_group"

    execute_mock = AsyncMock()
    decision_mock = MagicMock()

    monkeypatch.setattr(
        "custom_components.magic_areas.switch.media_player_control.execute_control_group_decision",
        execute_mock,
    )
    switch.policy = MagicMock()
    switch.policy.evaluate = decision_mock
    await switch.area_state_changed("test_area", ([], [], ["occupied"]))

    decision_mock.assert_not_called()
    execute_mock.assert_not_awaited()
