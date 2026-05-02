"""Unit tests for AreaLightGroup runtime helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import Mock

from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.light_groups import AreaLightGroup


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
    """AreaLightGroup restore helper should restore on/off and controlling attributes."""
    group = _fake_group()
    last_state = SimpleNamespace(state="on", attributes={"controlling": False})

    AreaLightGroup._restore_group_state(group, last_state)  # type: ignore[arg-type]

    assert group._attr_is_on is True
    assert group._echo_state.controlling is False


def test_restore_group_state_defaults_off_when_missing() -> None:
    """AreaLightGroup restore helper should default group off when no state exists."""
    group = _fake_group()

    AreaLightGroup._restore_group_state(group, None)  # type: ignore[arg-type]

    assert group._attr_is_on is False


def test_is_control_enabled_defaults_true_without_coordinator_data() -> None:
    """is_control_enabled should default to enabled when data is unavailable."""
    group = SimpleNamespace(
        _coordinator=SimpleNamespace(data=None),
        hass=SimpleNamespace(states=SimpleNamespace(get=lambda _id: None)),
    )

    assert AreaLightGroup.is_control_enabled(group) is True  # type: ignore[arg-type]


def test_group_state_change_uses_clear_cache_before_presence_fallback(
    monkeypatch,
) -> None:
    """Clear-state cache should prevent stale presence reads from releasing control."""
    group = _fake_group()
    group._area_id = "kitchen"
    group._last_known_area_states = ["clear"]
    group._last_known_area_states_from_dispatcher = True
    group._attr_extra_state_attributes = {}
    group.hass = SimpleNamespace(states=SimpleNamespace(get=lambda _id: None))
    group.category = "overhead_lights"
    group.controlling = True
    group.async_write_ha_state = Mock()
    reset_control = Mock()
    group._reset_control_state = reset_control

    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.resolve_area_presence_states",
        Mock(side_effect=AssertionError("stale presence fallback should not be read")),
    )

    origin_event = SimpleNamespace(
        event_type="state_changed",
        data={
            "old_state": SimpleNamespace(state="on", attributes={}),
            "new_state": SimpleNamespace(state="off", attributes={}),
        },
    )
    event = SimpleNamespace(
        context=SimpleNamespace(origin_event=origin_event),
    )

    assert AreaLightGroup.group_state_changed(group, event) is True  # type: ignore[arg-type]
    reset_control.assert_called_once_with()
    group.async_write_ha_state.assert_called_once_with()
