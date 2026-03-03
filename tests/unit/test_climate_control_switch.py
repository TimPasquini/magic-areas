"""Unit tests for ClimateControlSwitch runtime resolution behavior."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.switch.climate_control import ClimateControlSwitch


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
    coordinator.data.entity_references.area_state_sensor = None
    coordinator.data.feature_configs = {}
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
async def test_async_added_to_hass_resolves_climate_entity_from_registry_member(
    mock_area_config: Any,
    mock_coordinator: Any,
    mock_hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switch should resolve climate entity via control-group runtime helper."""
    fake_registry = MagicMock()
    fake_registry.async_get_entity_id.return_value = None
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_registry,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.base.SwitchBase.async_added_to_hass",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.climate_control.async_dispatcher_connect",
        lambda *args, **kwargs: (lambda: None),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.climate_control.async_track_state_change_event",
        lambda *args, **kwargs: (lambda: None),
    )

    resolver_mock = MagicMock(return_value="climate.test_area")
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.climate_control.resolve_group_member_entity_id",
        resolver_mock,
    )

    switch = ClimateControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch.climate_entity_id = None
    await switch.async_added_to_hass()

    resolver_mock.assert_called_once_with(
        area_id="test_area",
        policy_id="climate_control",
    )
    assert switch.climate_entity_id == "climate.test_area"


@pytest.mark.asyncio
async def test_apply_preset_by_name_noop_when_climate_entity_unresolved(
    mock_area_config: Any,
    mock_coordinator: Any,
    mock_hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preset application should no-op when climate entity is unavailable."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.climate_control.execute_control_group_decision",
        execute_mock,
    )

    switch = ClimateControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_name = "Climate Control"
    switch.climate_entity_id = None
    policy_mock = MagicMock()
    switch.policy = policy_mock

    await switch.apply_preset_by_name("sleep")

    policy_mock.evaluate.assert_not_called()
    execute_mock.assert_not_awaited()
