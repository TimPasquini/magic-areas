"""Parity tests for light policy -> control-group conversion."""

import asyncio
from collections.abc import Coroutine
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.core.controls import ControlActionType
from custom_components.magic_areas.core.controls import execute_control_group_decision
from custom_components.magic_areas.light_groups import (
    LightAction,
    is_valid_origin_state_toggle,
    light_action_to_control_group,
    process_secondary_group_state_change,
    turn_off,
    turn_on,
)
from custom_components.magic_areas.light_groups.runtime import _LightGroupHost


def test_light_turn_on_maps_to_activate_service_action() -> None:
    """TURN_ON should map to a light.turn_on control-group action."""
    decision = light_action_to_control_group(
        LightAction.TURN_ON, "light.magic_areas_light_groups_living_room_overhead"
    )

    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].domain == "light"
    assert decision.actions[0].service == "turn_on"
    assert decision.actions[0].target_entity_ids == (
        "light.magic_areas_light_groups_living_room_overhead",
    )


def test_light_turn_off_maps_to_deactivate_service_action() -> None:
    """TURN_OFF should map to a light.turn_off control-group action."""
    decision = light_action_to_control_group(
        LightAction.TURN_OFF, "light.magic_areas_light_groups_living_room_overhead"
    )

    assert decision.action_type == ControlActionType.DEACTIVATE
    assert decision.actions[0].domain == "light"
    assert decision.actions[0].service == "turn_off"
    assert decision.actions[0].target_entity_ids == (
        "light.magic_areas_light_groups_living_room_overhead",
    )


def test_light_noop_maps_to_noop_without_actions() -> None:
    """NOOP should remain a no-op control-group decision."""
    decision = light_action_to_control_group(
        LightAction.NOOP, "light.magic_areas_light_groups_living_room_overhead"
    )

    assert decision.action_type == ControlActionType.NOOP
    assert decision.actions == ()


def test_light_action_maps_explicit_entity_subset() -> None:
    """Light action conversion should support explicit entity targets."""
    decision = light_action_to_control_group(
        LightAction.TURN_ON,
        ("light.sleep_accent_lamp", "light.sleep_lamp"),
    )

    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].target_entity_ids == (
        "light.sleep_accent_lamp",
        "light.sleep_lamp",
    )


def test_origin_toggle_validation_rejects_restored_state() -> None:
    """Origin state validation should ignore restored state changes."""
    origin_event = SimpleNamespace(
        event_type="state_changed",
        data={
            "old_state": SimpleNamespace(
                state="on",
                attributes={"restored": True},
            ),
            "new_state": SimpleNamespace(
                state="off",
                attributes={},
            ),
        },
    )

    assert not is_valid_origin_state_toggle(origin_event)


def test_origin_toggle_validation_accepts_normal_on_off_transition() -> None:
    """Origin state validation should allow normal on/off toggles."""
    origin_event = SimpleNamespace(
        event_type="state_changed",
        data={
            "old_state": SimpleNamespace(state="on", attributes={}),
            "new_state": SimpleNamespace(state="off", attributes={}),
        },
    )

    assert is_valid_origin_state_toggle(origin_event)


def test_origin_toggle_validation_rejects_same_state_change() -> None:
    """Origin state validation should ignore on->on attribute-only updates."""
    origin_event = SimpleNamespace(
        event_type="state_changed",
        data={
            "old_state": SimpleNamespace(state="on", attributes={"brightness": 100}),
            "new_state": SimpleNamespace(state="on", attributes={"brightness": 200}),
        },
    )

    assert not is_valid_origin_state_toggle(origin_event)


class _FakeLightGroupRuntimeHost:
    def __init__(
        self,
        *,
        is_on: bool | None,
        controlling: bool = True,
        area_states: tuple[str, ...] = (),
        entity_states: dict[str, str] | None = None,
        sleep_members: tuple[str, ...] = (),
        accent_members: tuple[str, ...] = (),
    ) -> None:
        self.unique_id = "light_groups_area_1_overhead_lights"
        self.entity_id = "light.magic_areas_light_groups_area_1_overhead_lights"
        self.is_on = is_on
        self.category = "overhead_lights"
        self._area_id = "area_1"
        self._entity_ids = [
            "light.sleep_accent_lamp",
            "light.sleep_lamp",
            "light.accent_lamp",
        ]
        self._last_known_area_states = list(area_states)
        self._attr_extra_state_attributes: dict[str, object] = {}
        self._sleep_members = sleep_members
        self._accent_members = accent_members
        states = {
            entity_id: SimpleNamespace(state=state)
            for entity_id, state in (entity_states or {}).items()
        }
        self._echo_state = CommandEchoState(
            owner_id=self.unique_id,
            controlling=controlling,
            awaiting_echo=False,
        )
        self.scheduled_tasks: list[asyncio.Task[None]] = []
        self.hass = SimpleNamespace(
            async_create_task=self._async_create_task,
            states=SimpleNamespace(get=lambda entity_id: states.get(entity_id)),
        )
        self.dispatched: list[tuple[LightAction, tuple[str, ...] | None]] = []

    def _set_echo_state(self, state: CommandEchoState) -> None:
        self._echo_state = state

    def current_control_target_is_on(self) -> bool | None:
        return self.is_on

    def _async_create_task(self, coro: object) -> asyncio.Task[None]:
        task = asyncio.create_task(cast(Coroutine[object, object, None], coro))
        self.scheduled_tasks.append(task)
        return task

    def _dispatch_light_action(
        self,
        action: LightAction,
        target_entity_ids: tuple[str, ...] | None = None,
    ) -> None:
        self.dispatched.append((action, target_entity_ids))
        self.hass.async_create_task(
            execute_control_group_decision(
                self.hass,  # type: ignore[arg-type]
                light_action_to_control_group(action, target_entity_ids or self.entity_id),
            )
        )

    def light_member_suppression_members(
        self,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return self._sleep_members, self._accent_members


class _FakeSecondaryStateGroup:
    def __init__(self, *, awaiting_echo: bool) -> None:
        self.name = "Test Group"
        self.logger = SimpleNamespace(debug=lambda *args: None)
        self._echo_state = CommandEchoState(
            owner_id="light_groups_area_1_overhead_lights",
            controlling=True,
            awaiting_echo=awaiting_echo,
        )
        self.last_state: CommandEchoState | None = None

    def _set_echo_state(self, state: CommandEchoState) -> None:
        self.last_state = state
        self._echo_state = state


def test_process_secondary_group_state_change_rejects_invalid_event() -> None:
    """Secondary change processing should short-circuit when validation fails."""
    group = _FakeSecondaryStateGroup(awaiting_echo=False)
    invalid_event = SimpleNamespace(
        event_type="state_changed",
        data={"old_state": None, "new_state": None},
    )
    result = process_secondary_group_state_change(
        cast(_LightGroupHost, group), invalid_event
    )
    assert result is False


def test_process_secondary_group_state_change_applies_when_valid_event() -> None:
    """Secondary change processing should apply state update when event is valid."""
    group = _FakeSecondaryStateGroup(awaiting_echo=True)
    result = process_secondary_group_state_change(cast(_LightGroupHost, group), object())
    assert result is True
    assert group.last_state is not None
    assert group.last_state.awaiting_echo is False
    assert group.last_state.owner_id == "light_groups_area_1_overhead_lights"


def test_process_secondary_group_state_change_marks_external_change() -> None:
    """Secondary change processing should mark external changes when not pending echo."""
    group = _FakeSecondaryStateGroup(awaiting_echo=False)
    result = process_secondary_group_state_change(cast(_LightGroupHost, group), object())
    assert result is True
    assert group.last_state is not None
    assert group.last_state.controlling is False


@pytest.mark.asyncio
async def test_turn_on_uses_control_group_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Light runtime turn_on should delegate execution through control-group executor."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(is_on=False)

    result = turn_on(cast(_LightGroupHost, group))
    assert result is True
    assert group._echo_state.awaiting_echo is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].service == "turn_on"
    assert decision.actions[0].target_entity_ids == (group.entity_id,)
    assert group._attr_extra_state_attributes["last_intent_action"] == "turn_on"
    assert group._attr_extra_state_attributes["last_intent_reason"] == "intent_allowed"
    assert group._attr_extra_state_attributes["last_intent_executed"] is True
    assert group._attr_extra_state_attributes["last_intent_target_entity_ids"] == ()


@pytest.mark.asyncio
async def test_turn_on_dispatches_when_target_state_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown native-helper state should not suppress idempotent turn-on commands."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(is_on=None)

    result = turn_on(cast(_LightGroupHost, group))
    assert result is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert group._attr_extra_state_attributes["last_intent_executed"] is True
    assert "last_intent_target_is_on" not in group._attr_extra_state_attributes


@pytest.mark.asyncio
async def test_turn_on_uses_explicit_subset_when_sleep_suppression_narrows_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime should dispatch explicit entities when suppression narrows target."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(
        is_on=False,
        area_states=("occupied", "sleep"),
        entity_states={
            "light.sleep_accent_lamp": "off",
            "light.sleep_lamp": "off",
            "light.accent_lamp": "off",
        },
        sleep_members=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_members=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    result = turn_on(cast(_LightGroupHost, group))
    assert result is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].target_entity_ids == (
        "light.sleep_accent_lamp",
        "light.sleep_lamp",
    )
    assert group.dispatched == [
        (
            LightAction.TURN_ON,
            ("light.sleep_accent_lamp", "light.sleep_lamp"),
        )
    ]
    assert (
        group._attr_extra_state_attributes["last_intent_reason"]
        == "target_partially_suppressed"
    )
    assert group._attr_extra_state_attributes["last_intent_target_entity_ids"] == (
        "light.sleep_accent_lamp",
        "light.sleep_lamp",
    )
    assert group._attr_extra_state_attributes["last_intent_allowed_entity_ids"] == (
        "light.sleep_accent_lamp",
        "light.sleep_lamp",
    )
    assert group._attr_extra_state_attributes["last_intent_suppressed_entity_ids"] == (
        "light.accent_lamp",
    )


@pytest.mark.asyncio
async def test_turn_on_uses_explicit_subset_when_accent_suppression_narrows_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime should dispatch accent-member entities when accent suppresses target."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(
        is_on=False,
        area_states=("occupied", "accented"),
        entity_states={
            "light.sleep_accent_lamp": "off",
            "light.sleep_lamp": "off",
            "light.accent_lamp": "off",
        },
        sleep_members=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_members=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    result = turn_on(cast(_LightGroupHost, group))
    assert result is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.actions[0].target_entity_ids == (
        "light.sleep_accent_lamp",
        "light.accent_lamp",
    )


@pytest.mark.asyncio
async def test_turn_on_uses_overlap_subset_when_sleep_and_accent_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime should dispatch only overlap members when sleep and accent are active."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(
        is_on=False,
        area_states=("occupied", "sleep", "accented"),
        entity_states={
            "light.sleep_accent_lamp": "off",
            "light.sleep_lamp": "off",
            "light.accent_lamp": "off",
        },
        sleep_members=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_members=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    result = turn_on(cast(_LightGroupHost, group))
    assert result is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.actions[0].target_entity_ids == ("light.sleep_accent_lamp",)


@pytest.mark.asyncio
async def test_turn_on_noops_when_sleep_and_accent_suppress_all_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime should not dispatch activate when no target members survive."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(
        is_on=False,
        area_states=("occupied", "sleep", "accented"),
        entity_states={
            "light.sleep_accent_lamp": "off",
            "light.sleep_lamp": "off",
            "light.accent_lamp": "off",
        },
        sleep_members=("light.sleep_lamp",),
        accent_members=("light.accent_lamp",),
    )

    result = turn_on(cast(_LightGroupHost, group))

    assert result is False
    assert group.dispatched == []
    assert group._attr_extra_state_attributes["last_intent_reason"] == "target_suppressed"
    assert group._attr_extra_state_attributes["last_intent_executed"] is False
    assert group._attr_extra_state_attributes["last_intent_target_entity_ids"] == ()
    assert group._attr_extra_state_attributes["last_intent_suppressed_entity_ids"] == (
        "light.sleep_accent_lamp",
        "light.sleep_lamp",
        "light.accent_lamp",
    )
    execute_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_turn_off_uses_control_group_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Light runtime turn_off should delegate execution through control-group executor."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(is_on=True)

    result = turn_off(cast(_LightGroupHost, group))
    assert result is True
    assert group._echo_state.awaiting_echo is True
    assert group._echo_state.owner_id == group.unique_id

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.action_type == ControlActionType.DEACTIVATE
    assert decision.actions[0].service == "turn_off"
    assert decision.actions[0].target_entity_ids == (group.entity_id,)


@pytest.mark.asyncio
async def test_turn_off_uses_suppressed_subset_when_sleep_suppresses_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime should turn off members that do not survive suppressive state."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(
        is_on=True,
        area_states=("occupied", "sleep"),
        entity_states={
            "light.sleep_accent_lamp": "on",
            "light.sleep_lamp": "on",
            "light.accent_lamp": "on",
        },
        sleep_members=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_members=("light.sleep_accent_lamp", "light.accent_lamp"),
    )

    result = turn_off(cast(_LightGroupHost, group))
    assert result is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.action_type == ControlActionType.DEACTIVATE
    assert decision.actions[0].target_entity_ids == ("light.accent_lamp",)
    assert (
        group._attr_extra_state_attributes["last_intent_reason"]
        == "target_partially_suppressed"
    )
    assert group._attr_extra_state_attributes["last_intent_target_entity_ids"] == (
        "light.accent_lamp",
    )
    assert group._attr_extra_state_attributes["last_intent_allowed_entity_ids"] == (
        "light.sleep_accent_lamp",
        "light.sleep_lamp",
    )
    assert group._attr_extra_state_attributes["last_intent_suppressed_entity_ids"] == (
        "light.accent_lamp",
    )


@pytest.mark.asyncio
async def test_turn_off_noops_when_sleep_and_accent_overlap_preserves_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime should not turn off a member that survives sleep/accent overlap."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "tests.unit.test_light_control_group_parity.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeLightGroupRuntimeHost(
        is_on=True,
        area_states=("occupied", "sleep", "accented"),
        entity_states={"light.sleep_accent_lamp": "on"},
        sleep_members=("light.sleep_accent_lamp", "light.sleep_lamp"),
        accent_members=("light.sleep_accent_lamp", "light.accent_lamp"),
    )
    group._entity_ids = ["light.sleep_accent_lamp"]

    result = turn_off(cast(_LightGroupHost, group))

    assert result is False
    execute_mock.assert_not_awaited()
    assert group._echo_state.awaiting_echo is False
    assert group._attr_extra_state_attributes["last_intent_reason"] == "intent_allowed"
    assert group._attr_extra_state_attributes["last_intent_target_entity_ids"] == ()
    assert group._attr_extra_state_attributes["last_intent_allowed_entity_ids"] == (
        "light.sleep_accent_lamp",
    )
    assert group._attr_extra_state_attributes["last_intent_suppressed_entity_ids"] == ()


def test_turn_off_noop_when_not_controlling() -> None:
    """turn_off should be a no-op when group control is disabled."""
    group = _FakeLightGroupRuntimeHost(is_on=True, controlling=False)

    result = turn_off(cast(_LightGroupHost, group))

    assert result is False
    assert group._echo_state.awaiting_echo is False
    assert group._attr_extra_state_attributes["last_intent_reason"] == "control_disabled"
    assert group._attr_extra_state_attributes["last_intent_executed"] is False


def test_turn_off_noop_when_already_off() -> None:
    """turn_off should be a no-op when group is already off."""
    group = _FakeLightGroupRuntimeHost(is_on=False)

    result = turn_off(cast(_LightGroupHost, group))

    assert result is False
    assert group._echo_state.awaiting_echo is False
    assert group._attr_extra_state_attributes["last_intent_reason"] == (
        "target_state_mismatch"
    )
    assert group._attr_extra_state_attributes["last_intent_target_is_on"] is False
    assert group._attr_extra_state_attributes["last_intent_expected_target_is_on"] is True
