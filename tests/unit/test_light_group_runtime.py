"""Unit tests for light_groups.runtime helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from custom_components.magic_areas.core.command_echo import CommandEchoState
from custom_components.magic_areas.light_groups.runtime import (
    is_group_control_enabled,
    resolve_child_group_ids,
    restore_group_state,
)


def _fake_group() -> SimpleNamespace:
    group = SimpleNamespace()
    group.unique_id = "light_groups_test_all"
    group.name = "Test Group"
    group._attr_is_on = False
    group._echo_state = CommandEchoState(
        owner_id=group.unique_id,
        controlling=True,
        awaiting_echo=False,
    )
    group.logger = MagicMock()

    def _set_echo_state(state: CommandEchoState) -> None:
        group._echo_state = state

    group._set_echo_state = _set_echo_state
    return group


def test_restore_group_state_sets_on_and_control_state() -> None:
    """restore_group_state should restore on/off and controlling attributes."""
    group = _fake_group()
    last_state = SimpleNamespace(state="on", attributes={"controlling": False})

    restore_group_state(group, last_state)

    assert group._attr_is_on is True
    assert group._echo_state.controlling is False


def test_restore_group_state_defaults_off_when_missing() -> None:
    """restore_group_state should default group off when no state exists."""
    group = _fake_group()

    restore_group_state(group, None)

    assert group._attr_is_on is False


def test_resolve_child_group_ids_prefers_registry_metadata() -> None:
    """resolve_child_group_ids should use registry metadata mapping first."""
    hass = SimpleNamespace()

    with patch(
        "custom_components.magic_areas.light_groups.runtime.resolve_group_entity_ids_by_metadata",
        return_value={"overhead": "light.overhead", "task": "light.task"},
    ):
        resolved = resolve_child_group_ids(hass, "kitchen", ["task", "overhead"])

    assert resolved == ["light.task", "light.overhead"]


def test_resolve_child_group_ids_falls_back_to_unique_id_lookup() -> None:
    """resolve_child_group_ids should use unique-id fallback when metadata empty."""
    hass = SimpleNamespace()
    registry = MagicMock()
    registry.async_get_entity_id.side_effect = [
        "light.magic_areas_light_groups_kitchen_overhead_lights",
        None,
    ]

    with patch(
        "custom_components.magic_areas.light_groups.runtime.resolve_group_entity_ids_by_metadata",
        return_value={},
    ), patch(
        "custom_components.magic_areas.light_groups.runtime.er.async_get",
        return_value=registry,
    ):
        resolved = resolve_child_group_ids(hass, "kitchen", ["overhead", "task"])

    assert resolved == ["light.magic_areas_light_groups_kitchen_overhead_lights"]


def test_is_group_control_enabled_defaults_true_without_coordinator_data() -> None:
    """is_group_control_enabled should default to enabled when data is unavailable."""
    group = SimpleNamespace(
        _coordinator=SimpleNamespace(data=None),
        hass=SimpleNamespace(states=SimpleNamespace(get=lambda _id: None)),
    )

    assert is_group_control_enabled(group) is True
