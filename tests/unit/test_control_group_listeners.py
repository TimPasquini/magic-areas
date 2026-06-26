"""Unit tests for control-group listener helpers on runtime surface."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.controls import (
    read_area_presence_states,
    register_area_and_group_state_listeners,
    resolve_area_presence_states,
)
from custom_components.magic_areas.const import ATTR_STATES
from custom_components.magic_areas.area_state import AreaStates


def test_register_area_and_group_state_listeners_tracks_two_listeners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Listener helper should register area dispatcher + group state listeners."""
    area_remove = MagicMock()
    group_remove = MagicMock()
    track_listener = MagicMock()

    monkeypatch.setattr(
        "custom_components.magic_areas.core.controls.control_group_runtime.async_dispatcher_connect",
        lambda hass, signal, handler: area_remove,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.controls.control_group_runtime.async_track_state_change_event",
        lambda hass, entity_ids, handler: group_remove,
    )

    hass = MagicMock(spec=HomeAssistant)
    register_area_and_group_state_listeners(
        hass=hass,
        track_listener=track_listener,
        area_state_handler=MagicMock(),
        group_entity_id="light.magic_areas_light_groups_kitchen_overhead_lights",
        group_state_handler=MagicMock(),
    )

    assert track_listener.call_count == 2
    assert track_listener.call_args_list[0].args == (
        area_remove,
        "area_state_dispatcher",
    )
    assert track_listener.call_args_list[1].args == (group_remove, "group_state_change")


def test_read_area_presence_states_returns_states_from_presence_sensor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Presence reader should return normalized area states from sensor attributes."""
    fake_registry = SimpleNamespace(
        async_get_entity_id=lambda domain,
        platform,
        unique_id: "binary_sensor.test_presence"
    )
    fake_states = SimpleNamespace(
        get=lambda entity_id: SimpleNamespace(
            attributes={ATTR_STATES: [AreaStates.OCCUPIED, "dark"]}
        )
    )
    hass = MagicMock(spec=HomeAssistant)
    hass.states = fake_states

    monkeypatch.setattr(
        "custom_components.magic_areas.core.controls.control_group_runtime.entity_registry_module.async_get",
        lambda _hass: fake_registry,
    )

    states = read_area_presence_states(hass, "kitchen")
    assert states == [AreaStates.OCCUPIED.value, "dark"]


def test_read_area_presence_states_returns_empty_when_presence_entity_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Presence reader should return empty list when entity cannot be resolved."""
    fake_registry = SimpleNamespace(
        async_get_entity_id=lambda domain, platform, unique_id: None
    )
    hass = MagicMock(spec=HomeAssistant)
    hass.states = SimpleNamespace(get=lambda entity_id: None)

    monkeypatch.setattr(
        "custom_components.magic_areas.core.controls.control_group_runtime.entity_registry_module.async_get",
        lambda _hass: fake_registry,
    )

    states = read_area_presence_states(hass, "kitchen")
    assert states == []


def test_resolve_area_presence_states_prefers_cache_when_valid() -> None:
    """Resolver should return cached states when no fallback is required."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = SimpleNamespace(get=lambda _id: None)
    states = resolve_area_presence_states(
        hass=hass,
        area_id="kitchen",
        cached_states=["occupied", "dark"],
    )
    assert states == ["occupied", "dark"]


def test_resolve_area_presence_states_falls_back_when_cache_missing_occupied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolver should read presence sensor when occupied is required and absent."""
    monkeypatch.setattr(
        "custom_components.magic_areas.core.controls.control_group_runtime.read_area_presence_states",
        lambda hass, area_id: ["occupied"],
    )
    hass = MagicMock(spec=HomeAssistant)
    hass.states = SimpleNamespace(get=lambda _id: None)

    states = resolve_area_presence_states(
        hass=hass,
        area_id="kitchen",
        cached_states=["clear"],
        require_occupied=True,
    )
    assert states == ["occupied"]
