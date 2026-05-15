"""Unit tests for AreaLightGroup runtime helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
import pytest

from custom_components.magic_areas.core.controls import (
    ControlActionType,
    ControlRuntimeEffect,
    ControlRuntimeEffectType,
)
from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.light_groups import AreaLightGroup
from custom_components.magic_areas.light_groups import LightAction
from custom_components.magic_areas.light_groups import (
    schedule_adaptive_lighting_manual_restore,
    schedule_adaptive_lighting_state_coordination,
)
from custom_components.magic_areas.light_groups import turn_on
from custom_components.magic_areas.light_groups import apply_runtime_effect
from tests.unit.adaptive_lighting_testkit import setup_adaptive_lighting_harness


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


def test_hide_policy_entity_marks_visible_registry_entry_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Custom light policy entities should be hidden but remain enabled."""
    registry_entry = SimpleNamespace(hidden_by=None)
    updated_entry = SimpleNamespace(hidden_by="integration")
    entity_registry = SimpleNamespace(
        async_get=Mock(return_value=registry_entry),
        async_update_entity=Mock(return_value=updated_entry),
    )
    group = SimpleNamespace(
        hass=object(),
        entity_id="light.magic_areas_light_groups_living_room_overhead",
        registry_entry=None,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.er.async_get",
        Mock(return_value=entity_registry),
    )

    AreaLightGroup._hide_policy_entity(group)  # type: ignore[arg-type]

    entity_registry.async_update_entity.assert_called_once_with(
        group.entity_id,
        hidden_by=er.RegistryEntryHider.INTEGRATION,
    )
    assert group.registry_entry is updated_entry


def test_hide_policy_entity_preserves_existing_hidden_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing hidden entries should not be rewritten on every setup."""
    entity_registry = SimpleNamespace(
        async_get=Mock(),
        async_update_entity=Mock(),
    )
    group = SimpleNamespace(
        hass=object(),
        entity_id="light.magic_areas_light_groups_living_room_overhead",
        registry_entry=SimpleNamespace(hidden_by="user"),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.er.async_get",
        Mock(return_value=entity_registry),
    )

    AreaLightGroup._hide_policy_entity(group)  # type: ignore[arg-type]

    entity_registry.async_update_entity.assert_not_called()


def test_group_state_change_uses_clear_cache_before_presence_fallback(
    monkeypatch: pytest.MonkeyPatch,
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


def test_control_target_entity_resolves_native_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Light actions should prefer the reconciled native helper target."""
    hass = object()
    registry = object()
    group = SimpleNamespace(
        hass=hass,
        entity_id="light.magic_areas_light_groups_living_room_overhead",
        _native_control_target_unique_id="magic_areas:entry:area:light_groups:config_entry_helper:light_group_overhead_lights",
    )
    async_get = Mock(return_value=registry)
    resolve = Mock(return_value="light.magic_areas_native_living_room_overhead")
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.er.async_get",
        async_get,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.resolve_managed_surface_entity_id",
        resolve,
    )

    target = AreaLightGroup._control_target_entity_id(group)  # type: ignore[arg-type]

    assert target == "light.magic_areas_native_living_room_overhead"
    async_get.assert_called_once_with(hass)
    resolve.assert_called_once_with(
        hass,
        registry,
        unique_id=group._native_control_target_unique_id,
        entity_domain="light",
        config_entry_domain="group",
    )


def test_control_target_entity_falls_back_to_policy_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Light actions should still work before the native helper exists."""
    group = SimpleNamespace(
        hass=object(),
        entity_id="light.magic_areas_light_groups_living_room_overhead",
        _native_control_target_unique_id="missing",
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.er.async_get",
        Mock(return_value=object()),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.resolve_managed_surface_entity_id",
        Mock(return_value=None),
    )

    target = AreaLightGroup._control_target_entity_id(group)  # type: ignore[arg-type]

    assert target == "light.magic_areas_light_groups_living_room_overhead"


def test_current_control_target_state_prefers_native_helper() -> None:
    """Runtime on/off checks should read the native helper state first."""
    group = SimpleNamespace(
        hass=SimpleNamespace(
            states=SimpleNamespace(
                get=lambda entity_id: SimpleNamespace(state="on")
                if entity_id == "light.magic_areas_native_living_room_overhead"
                else None
            )
        ),
        _control_target_entity_id=Mock(
            return_value="light.magic_areas_native_living_room_overhead"
        ),
        is_on=False,
    )

    assert AreaLightGroup.current_control_target_is_on(group) is True  # type: ignore[arg-type]


def test_current_control_target_state_falls_back_to_policy_entity_state() -> None:
    """Unknown native helper state should not block the legacy fallback path."""
    group = SimpleNamespace(
        hass=SimpleNamespace(
            states=SimpleNamespace(
                get=lambda _entity_id: SimpleNamespace(state="unknown")
            )
        ),
        _control_target_entity_id=Mock(
            return_value="light.magic_areas_native_living_room_overhead"
        ),
        is_on=True,
    )

    assert AreaLightGroup.current_control_target_is_on(group) is True  # type: ignore[arg-type]


def test_light_member_suppression_members_prefers_reconciled_labels(
    hass: HomeAssistant,
) -> None:
    """Sleep/accent suppression should read HA labels before config fallback."""
    entity_registry = er.async_get(hass)
    sleep_lamp = entity_registry.async_get_or_create("light", "test", "sleep_lamp")
    accent_lamp = entity_registry.async_get_or_create("light", "test", "accent_lamp")
    other_room_sleep_lamp = entity_registry.async_get_or_create(
        "light",
        "test",
        "other_room_sleep_lamp",
    )
    sleep_label = lr.async_get(hass).async_create("ma:sleep")
    for entry in (sleep_lamp, other_room_sleep_lamp):
        entity_registry.async_update_entity(
            entry.entity_id, labels={sleep_label.label_id}
        )

    group = SimpleNamespace(
        hass=hass,
        _area_id="living_room",
        _entity_ids=[sleep_lamp.entity_id, accent_lamp.entity_id],
        _feature_config={
            "sleep_lights": [],
            "accent_lights": [accent_lamp.entity_id],
        },
    )
    group._resolved_role_members = lambda preset: AreaLightGroup._resolved_role_members(
        cast(AreaLightGroup, group),
        preset,
    )

    sleep_members, accent_members = AreaLightGroup.light_member_suppression_members(
        group,  # type: ignore[arg-type]
    )

    assert sleep_members == (sleep_lamp.entity_id,)
    assert accent_members == (accent_lamp.entity_id,)


def test_turn_on_uses_control_target_state_for_dispatch_gate() -> None:
    """Policy dispatch gating should not depend on stale custom group state."""
    group = _fake_group()
    group.is_on = True
    group.current_control_target_is_on = Mock(return_value=False)
    group._last_control_activity_monotonic = None
    group._last_turn_on_monotonic = None
    group._dispatch_light_action = Mock()

    assert turn_on(group) is True
    group._dispatch_light_action.assert_called_once_with(LightAction.TURN_ON)


@pytest.mark.asyncio
async def test_dispatch_light_action_targets_native_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dispatch should execute against the native helper without moving policy ownership."""
    execute_mock = AsyncMock()
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.entities.execute_control_group_decision",
        execute_mock,
    )
    scheduled_tasks: list[asyncio.Task[None]] = []

    def async_create_task(coro: object) -> asyncio.Task[None]:
        task = asyncio.create_task(cast(Coroutine[object, object, None], coro))
        scheduled_tasks.append(task)
        return task

    group = SimpleNamespace(
        hass=SimpleNamespace(async_create_task=async_create_task),
        entity_id="light.magic_areas_light_groups_living_room_overhead",
        _control_target_entity_id=Mock(
            return_value="light.magic_areas_native_living_room_overhead"
        ),
    )

    AreaLightGroup._dispatch_light_action(group, LightAction.TURN_ON)  # type: ignore[arg-type]
    await asyncio.gather(*scheduled_tasks)

    execute_mock.assert_awaited_once()
    assert execute_mock.await_args is not None
    _hass, decision = execute_mock.await_args.args
    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].target_entity_ids == (
        "light.magic_areas_native_living_room_overhead",
    )


@pytest.mark.asyncio
async def test_adaptive_lighting_coordination_schedules_area_state_intents(
    hass: HomeAssistant,
) -> None:
    """Light runtime should schedule AL side effects without changing policy actions."""
    harness = await setup_adaptive_lighting_harness(hass)
    group = _fake_group()
    group.hass = hass
    group._adaptive_lighting_switch_set = harness.switch_set

    scheduled = schedule_adaptive_lighting_state_coordination(
        group,
        (["sleep", "accented"], [], ["occupied", "sleep", "accented"]),
    )
    await hass.async_block_till_done()

    assert scheduled
    assert [call.service for call in harness.calls] == [
        "switch.turn_on",
        "switch.turn_off",
        "switch.turn_off",
    ]


@pytest.mark.asyncio
async def test_adaptive_lighting_coordination_is_inert_without_switch_set(
    hass: HomeAssistant,
) -> None:
    """Runtime hook should do nothing until a target has opted into AL coordination."""
    group = _fake_group()
    group.hass = hass

    scheduled = schedule_adaptive_lighting_state_coordination(
        group,
        (["sleep"], [], ["occupied", "sleep"]),
    )
    await hass.async_block_till_done()

    assert not scheduled


@pytest.mark.asyncio
async def test_adaptive_lighting_manual_restore_schedules_after_control_reset(
    hass: HomeAssistant,
) -> None:
    """Runtime should clear AL manual-control when MA control is explicitly restored."""
    harness = await setup_adaptive_lighting_harness(hass)
    group = _fake_group()
    group.hass = hass
    group._entity_ids = ["light.lamp"]
    group._adaptive_lighting_switch_set = harness.switch_set

    scheduled = schedule_adaptive_lighting_manual_restore(group)
    await hass.async_block_till_done()

    assert scheduled
    assert harness.calls[-1].service == "set_manual_control"
    assert harness.calls[-1].data == {
        "entity_id": harness.switch_set.main_switch_entity_id,
        "lights": ("light.lamp",),
        "manual_control": False,
    }


@pytest.mark.asyncio
async def test_runtime_effect_reclaiming_control_restores_adaptive_lighting_manual_control(
    hass: HomeAssistant,
) -> None:
    """Policy effects that end MA manual override should also release AL manual control."""
    harness = await setup_adaptive_lighting_harness(hass)
    group = _fake_group()
    group.hass = hass
    group._entity_ids = ["light.lamp"]
    group._adaptive_lighting_switch_set = harness.switch_set
    group._echo_state = CommandEchoState(controlling=False, awaiting_echo=False)

    apply_runtime_effect(
        group,
        ControlRuntimeEffect(
            effect_type=ControlRuntimeEffectType.SET_STATE,
            namespace="command_echo",
            key="state",
            value=CommandEchoState(controlling=True, awaiting_echo=False),
        ),
    )
    await hass.async_block_till_done()

    assert group._echo_state.controlling is True
    assert harness.calls[-1].service == "set_manual_control"


@pytest.mark.asyncio
async def test_adaptive_lighting_manual_restore_is_inert_without_switch_set(
    hass: HomeAssistant,
) -> None:
    """Manual restore hook should do nothing until AL coordination is configured."""
    group = _fake_group()
    group.hass = hass
    group._entity_ids = ["light.lamp"]
    group._adaptive_lighting_switch_set = None

    scheduled = schedule_adaptive_lighting_manual_restore(group)
    await hass.async_block_till_done()

    assert not scheduled
