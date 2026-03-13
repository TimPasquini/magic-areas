"""Runtime resolution tests for control-group registry consumers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.core.controls import ControlGroupDefinition, GroupRegistry
from custom_components.magic_areas.switch import (
    FanControlSwitch,
    MediaPlayerControlSwitch,
)


def _mock_area_config() -> AreaConfig:
    area = MagicMock()
    area.id = "test_area"
    area.slug = "test_area"
    area.name = "Test Area"
    area.config = {}
    area.icon = None
    area.floor_id = None
    area.area_type = "interior"
    return area


def _mock_coordinator() -> MagicAreasCoordinator:
    coordinator = MagicMock()
    coordinator.data = MagicMock()
    coordinator.data.group_registry = GroupRegistry()
    coordinator.data.entity_references = MagicMock()
    coordinator.data.entity_references.area_state_sensor = None
    coordinator.data.entity_references.fan_group = None
    coordinator.data.entity_references.media_player_group = None
    return coordinator


@pytest.mark.asyncio
async def test_fan_switch_resolves_group_from_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fan control switch should resolve fan group by registry definition unique_id."""
    fake_registry = MagicMock()
    fake_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: (
            "fan.magic_areas_fan_groups_test_area_fan_group"
            if unique_id == "fan_groups_test_area_fan_group"
            else None
        )
    )
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

    registry = GroupRegistry()
    registry.register_area_default(
        "test_area",
        ControlGroupDefinition(
            group_id="fan_groups_test_area_fan_group",
            members=("fan.ceiling",),
            policy_id="fan_groups",
            metadata={"role": "primary"},
        ),
    )
    coordinator = _mock_coordinator()
    coordinator.data.group_registry = registry
    switch = FanControlSwitch(_mock_area_config(), coordinator)
    switch.hass = MagicMock()
    switch.hass.states = MagicMock()
    switch.hass.services = MagicMock()
    switch.hass.async_create_task = MagicMock()

    await switch.async_added_to_hass()

    assert switch._fan_group_entity_id == "fan.magic_areas_fan_groups_test_area_fan_group"


@pytest.mark.asyncio
async def test_media_switch_resolves_group_from_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Media control switch should resolve group by registry definition unique_id."""
    fake_registry = MagicMock()
    fake_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: (
            "media_player.magic_areas_media_player_groups_test_area_media_player_group"
            if unique_id == "media_player_groups_test_area_media_player_group"
            else None
        )
    )
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

    registry = GroupRegistry()
    registry.register_area_default(
        "test_area",
        ControlGroupDefinition(
            group_id="media_player_groups_test_area_media_player_group",
            members=("media_player.tv",),
            policy_id="media_player_groups",
            metadata={"role": "primary"},
        ),
    )
    coordinator = _mock_coordinator()
    coordinator.data.group_registry = registry
    switch = MediaPlayerControlSwitch(_mock_area_config(), coordinator)
    switch.hass = MagicMock()
    switch.hass.states = MagicMock()
    switch.hass.services = MagicMock()
    switch.hass.async_create_task = MagicMock()

    await switch.async_added_to_hass()

    assert switch.media_player_group_id == (
        "media_player.magic_areas_media_player_groups_test_area_media_player_group"
    )


@pytest.mark.asyncio
async def test_fan_switch_returns_none_without_registry_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fan control switch should keep target unresolved without registry definitions."""
    fake_registry = MagicMock()
    fake_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: (
            "fan.magic_areas_fan_groups_test_area_fan_group"
            if unique_id == "fan_groups_test_area_fan_group"
            else None
        )
    )
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
    coordinator = _mock_coordinator()
    coordinator.data.group_registry = GroupRegistry()
    switch = FanControlSwitch(_mock_area_config(), coordinator)
    switch.hass = MagicMock()
    switch.hass.states = MagicMock()
    switch.hass.services = MagicMock()
    switch.hass.async_create_task = MagicMock()

    await switch.async_added_to_hass()

    assert switch._fan_group_entity_id is None


@pytest.mark.asyncio
async def test_media_switch_returns_none_without_registry_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Media control switch should keep target unresolved without registry definitions."""
    fake_registry = MagicMock()
    fake_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: (
            "media_player.magic_areas_media_player_groups_test_area_media_player_group"
            if unique_id == "media_player_groups_test_area_media_player_group"
            else None
        )
    )
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
    coordinator = _mock_coordinator()
    coordinator.data.group_registry = GroupRegistry()
    switch = MediaPlayerControlSwitch(_mock_area_config(), coordinator)
    switch.hass = MagicMock()
    switch.hass.states = MagicMock()
    switch.hass.services = MagicMock()
    switch.hass.async_create_task = MagicMock()

    await switch.async_added_to_hass()

    assert switch.media_player_group_id is None
