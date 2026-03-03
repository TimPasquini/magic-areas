"""Parity tests for light policy -> control-group conversion."""

import asyncio
from collections.abc import Coroutine
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from custom_components.magic_areas.core.command_echo import CommandEchoState
from custom_components.magic_areas.core.control_group import ControlActionType
from custom_components.magic_areas.light_groups.entities import AreaLightGroup
from custom_components.magic_areas.light_groups.policy import (
    LightAction,
    light_action_to_control_group,
)


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


class _FakeAreaLightGroup:
    def __init__(self, *, is_on: bool) -> None:
        self.unique_id = "light_groups_area_1_overhead_lights"
        self.entity_id = "light.magic_areas_light_groups_area_1_overhead_lights"
        self.is_on = is_on
        self._echo_state = CommandEchoState(
            owner_id=self.unique_id,
            controlling=True,
            awaiting_echo=False,
        )
        self.scheduled_tasks: list[asyncio.Task] = []
        self.hass = SimpleNamespace(async_create_task=self._async_create_task)

    def _set_echo_state(self, state: CommandEchoState) -> None:
        self._echo_state = state

    def _async_create_task(self, coro: object) -> asyncio.Task:
        task: asyncio.Task[None] = asyncio.create_task(
            cast(Coroutine[Any, Any, None], coro)
        )
        self.scheduled_tasks.append(task)
        return task


@pytest.mark.asyncio
async def test_turn_on_uses_control_group_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AreaLightGroup._turn_on should delegate execution through control-group executor."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeAreaLightGroup(is_on=False)

    result = AreaLightGroup._turn_on(group)  # type: ignore[arg-type]
    assert result is True
    assert group._echo_state.awaiting_echo is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].service == "turn_on"
    assert decision.actions[0].target_entity_ids == (group.entity_id,)


@pytest.mark.asyncio
async def test_turn_off_uses_control_group_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AreaLightGroup._turn_off should delegate execution through control-group executor."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.execute_control_group_decision",
        execute_mock,
    )
    group = _FakeAreaLightGroup(is_on=True)

    result = AreaLightGroup._turn_off(group)  # type: ignore[arg-type]
    assert result is True

    await asyncio.gather(*group.scheduled_tasks)
    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.action_type == ControlActionType.DEACTIVATE
    assert decision.actions[0].service == "turn_off"
    assert decision.actions[0].target_entity_ids == (group.entity_id,)
