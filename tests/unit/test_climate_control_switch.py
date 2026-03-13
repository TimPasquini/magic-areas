"""Unit tests for ClimateControlSwitch runtime resolution behavior."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.switch import ClimateControlSwitch


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
    coordinator.data.entity_references.area_state_sensor = None
    coordinator.data.feature_configs = {}
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
async def test_async_added_to_hass_resolves_climate_entity_from_registry_member(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: HomeAssistant,
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
        "custom_components.magic_areas.switch.base.ControlSwitchBase._track_area_state_dispatcher",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.base.ControlSwitchBase._track_state_change",
        lambda *args, **kwargs: None,
    )

    resolver_mock = MagicMock(return_value="climate.test_area")
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.base.ControlSwitchBase._resolve_primary_group_member_entity_id",
        resolver_mock,
    )

    switch = ClimateControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch.climate_entity_id = None
    await switch.async_added_to_hass()

    resolver_mock.assert_called_once_with(
        policy_id="climate_control",
    )
    assert switch.climate_entity_id == "climate.test_area"


@pytest.mark.asyncio
async def test_apply_preset_by_name_noop_when_climate_entity_unresolved(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preset application should no-op when climate entity is unavailable."""
    switch = ClimateControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    switch._attr_name = "Climate Control"
    switch.climate_entity_id = None
    policy_mock = MagicMock()
    execute_mock = AsyncMock()
    switch.policy = policy_mock
    monkeypatch.setattr(switch, "_execute_decision", execute_mock)

    await switch.apply_preset_by_name("sleep")

    policy_mock.evaluate.assert_not_called()
    execute_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_added_to_hass_does_not_fallback_area_sensor_entity_id(
    mock_area_config: AreaConfig,
    mock_coordinator: MagicAreasCoordinator,
    mock_hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Area sensor listener should not use a slug-based fallback entity id."""
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.base.SwitchBase.async_added_to_hass",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.base.ControlSwitchBase._track_area_state_dispatcher",
        lambda *args, **kwargs: None,
    )

    track_state_change_mock = MagicMock()
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.base.ControlSwitchBase._track_state_change",
        track_state_change_mock,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.switch.base.ControlSwitchBase._resolve_area_state_sensor_entity_id",
        MagicMock(return_value=None),
    )

    switch = ClimateControlSwitch(mock_area_config, mock_coordinator)
    switch.hass = mock_hass
    await switch.async_added_to_hass()

    assert switch._area_sensor_entity_id is None
    track_state_change_mock.assert_called_once_with(
        "area_sensor_state_change",
        None,
        switch._area_sensor_state_changed,
    )
