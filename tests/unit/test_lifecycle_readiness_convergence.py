"""Unit tests for non-meta readiness convergence reload behavior."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.magic_areas.coordinator.pipeline.lifecycle import (
    ReadinessGateAction,
    ReadinessRequestAction,
    ReadinessConvergenceManager,
    _MAX_WINDOW_RELOADS,
    _snapshot_entity_ids,
    build_readiness_gate_plan,
    build_readiness_request_plan,
    should_trigger_readiness_reload,
)
from custom_components.magic_areas.coordinator.pipeline.snapshot import MagicAreasData
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.runtime_model import AreaConfig, AreaRuntime
from custom_components.magic_areas.core.runtime_model.references import EntityReferences


def _make_snapshot() -> MagicAreasData:
    area_config = AreaConfig(
        id="kitchen",
        name="Kitchen",
        slug="kitchen",
        area_type="interior",
        config={},
        hass_config=MagicMock(),
    )
    refs = EntityReferences(
        area_state_sensor="binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
        threshold_sensor="binary_sensor.magic_areas_threshold_kitchen_light",
    )
    return MagicAreasData(
        entities={"sensor": [{"entity_id": "sensor.kitchen_temperature"}]},
        magic_entities={
            "switch": [{"entity_id": "switch.magic_areas_presence_hold_kitchen"}]
        },
        presence_sensors=["binary_sensor.kitchen_motion"],
        active_areas=[],
        child_areas=[],
        config={},
        enabled_features=set(),
        feature_configs={},
        group_registry=GroupRegistry(),
        entity_references=refs,
        area_config=area_config,
        area_runtime=AreaRuntime(),
        updated_at=datetime.now(UTC),
    )


def _make_manager(*, should_auto_reload: bool = True) -> ReadinessConvergenceManager:
    loop = asyncio.get_running_loop()
    hass = MagicMock()
    hass.loop = loop
    hass.is_running = True
    hass.bus.async_listen.return_value = lambda: None

    config_entry = MagicMock()
    config_entry.data = {"name": "Kitchen"}

    return ReadinessConvergenceManager(
        hass=hass,
        config_entry=config_entry,
        area_config=_make_snapshot().area_config,
        get_snapshot=_make_snapshot,
        should_auto_reload=lambda: should_auto_reload,
    )


def test_snapshot_entity_ids_includes_all_relevant_sources() -> None:
    """Snapshot entity id collection should include refs and tracked lists."""
    snapshot = _make_snapshot()

    entity_ids = _snapshot_entity_ids(snapshot)

    assert "sensor.kitchen_temperature" in entity_ids
    assert "switch.magic_areas_presence_hold_kitchen" in entity_ids
    assert "binary_sensor.kitchen_motion" in entity_ids
    assert snapshot.entity_references.area_state_sensor in entity_ids
    assert snapshot.entity_references.threshold_sensor in entity_ids


@pytest.mark.asyncio
async def test_convergence_request_reload_skips_when_disabled() -> None:
    """Convergence manager should not schedule reloads when auto-reload is disabled."""
    manager = _make_manager(should_auto_reload=False)

    manager.request_reload(reason="disabled")

    assert manager._pending_reload_handle is None
    assert manager._reload_count == 0


@pytest.mark.asyncio
async def test_convergence_request_reload_respects_window_cap() -> None:
    """Convergence manager should stop scheduling when bounded cap is reached."""
    manager = _make_manager(should_auto_reload=True)
    manager._window_started_at = manager._hass.loop.time()
    manager._reload_count = _MAX_WINDOW_RELOADS

    manager.request_reload(reason="cap")

    assert manager._pending_reload_handle is None


@pytest.mark.asyncio
async def test_state_readiness_triggers_reload_for_tracked_entity() -> None:
    """State transitions from invalid->valid should trigger convergence reloads."""
    manager = _make_manager()
    event = MagicMock()
    event.data = {
        "entity_id": "sensor.kitchen_temperature",
        "old_state": MagicMock(state="unavailable"),
        "new_state": MagicMock(state="21"),
    }

    with patch.object(manager, "request_reload") as request_reload:
        await manager._async_handle_state_readiness(event)

    request_reload.assert_called_once()


@pytest.mark.asyncio
async def test_state_readiness_ignores_untracked_or_non_recovery_events() -> None:
    """Irrelevant entities and non-recovery transitions should not trigger reloads."""
    manager = _make_manager()

    events = [
        {
            "entity_id": "sensor.other",
            "old_state": MagicMock(state="unavailable"),
            "new_state": MagicMock(state="10"),
        },
        {
            "entity_id": "sensor.kitchen_temperature",
            "old_state": MagicMock(state="10"),
            "new_state": MagicMock(state="11"),
        },
        {
            "entity_id": "sensor.kitchen_temperature",
            "old_state": MagicMock(state="unknown"),
            "new_state": MagicMock(state="unknown"),
        },
    ]

    with patch.object(manager, "request_reload") as request_reload:
        for event_data in events:
            event = MagicMock()
            event.data = event_data
            await manager._async_handle_state_readiness(event)

    request_reload.assert_not_called()


@pytest.mark.asyncio
async def test_convergence_execute_reload_resets_in_flight_guard() -> None:
    """Convergence execution should clear in-flight guard even if reload errors."""
    manager = _make_manager()

    with (
        patch(
            "custom_components.magic_areas.coordinator.pipeline.lifecycle.async_reload_entry",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        pytest.raises(RuntimeError),
    ):
        await manager._async_execute_reload()

    assert manager._reload_in_flight is False


def test_build_readiness_request_plan_resets_window_and_schedules() -> None:
    """Stale/missing window should reset and allow scheduling."""
    plan = build_readiness_request_plan(
        now=200.0,
        window_started_at=0.0,
        reload_count=3,
        has_pending_handle=False,
    )

    assert plan.action == ReadinessRequestAction.SCHEDULE
    assert plan.window_started_at == 200.0
    assert plan.reload_count == 0


def test_build_readiness_request_plan_skips_when_cap_reached() -> None:
    """Window cap should block scheduling."""
    plan = build_readiness_request_plan(
        now=50.0,
        window_started_at=10.0,
        reload_count=_MAX_WINDOW_RELOADS,
        has_pending_handle=False,
    )

    assert plan.action == ReadinessRequestAction.SKIP_CAP


def test_build_readiness_request_plan_keeps_pending_schedule() -> None:
    """Existing pending callback should be preserved."""
    plan = build_readiness_request_plan(
        now=50.0,
        window_started_at=10.0,
        reload_count=1,
        has_pending_handle=True,
    )

    assert plan.action == ReadinessRequestAction.KEEP_PENDING
    assert plan.window_started_at == 10.0
    assert plan.reload_count == 1


def test_should_trigger_readiness_reload_requires_tracked_entity() -> None:
    """Readiness triggers only for tracked entities with recovery transitions."""
    tracked_entity_ids = {"sensor.kitchen_temperature"}
    assert not should_trigger_readiness_reload(
        entity_id="sensor.other",
        tracked_entity_ids=tracked_entity_ids,
        old_value="unavailable",
        new_value="20",
    )
    assert should_trigger_readiness_reload(
        entity_id="sensor.kitchen_temperature",
        tracked_entity_ids=tracked_entity_ids,
        old_value="unknown",
        new_value="20",
    )
    assert not should_trigger_readiness_reload(
        entity_id="switch.magic_areas_presence_hold_kitchen",
        tracked_entity_ids={
            "switch.magic_areas_presence_hold_kitchen",
        },
        old_value="unknown",
        new_value="on",
    )


def test_should_trigger_readiness_reload_rejects_non_recovery_transitions() -> None:
    """Only invalid->valid transitions should trigger convergence reload."""
    tracked_entity_ids = {"sensor.kitchen_temperature"}
    assert not should_trigger_readiness_reload(
        entity_id=None,
        tracked_entity_ids=tracked_entity_ids,
        old_value="unknown",
        new_value="20",
    )
    assert not should_trigger_readiness_reload(
        entity_id="sensor.kitchen_temperature",
        tracked_entity_ids=tracked_entity_ids,
        old_value="20",
        new_value="21",
    )
    assert not should_trigger_readiness_reload(
        entity_id="sensor.kitchen_temperature",
        tracked_entity_ids=tracked_entity_ids,
        old_value="unknown",
        new_value="unavailable",
    )


def test_build_readiness_gate_plan_disabled() -> None:
    """Auto-reload disabled should block readiness request."""
    plan = build_readiness_gate_plan(
        auto_reload_enabled=False,
        hass_is_running=True,
        reload_in_flight=False,
    )
    assert plan.action == ReadinessGateAction.SKIP_DISABLED


def test_build_readiness_gate_plan_not_running() -> None:
    """Stopped HA should block readiness request."""
    plan = build_readiness_gate_plan(
        auto_reload_enabled=True,
        hass_is_running=False,
        reload_in_flight=False,
    )
    assert plan.action == ReadinessGateAction.SKIP_NOT_RUNNING


def test_build_readiness_gate_plan_in_flight() -> None:
    """In-flight reload should block readiness request."""
    plan = build_readiness_gate_plan(
        auto_reload_enabled=True,
        hass_is_running=True,
        reload_in_flight=True,
    )
    assert plan.action == ReadinessGateAction.SKIP_IN_FLIGHT


def test_build_readiness_gate_plan_proceeds() -> None:
    """Eligible state should proceed to request planning."""
    plan = build_readiness_gate_plan(
        auto_reload_enabled=True,
        hass_is_running=True,
        reload_in_flight=False,
    )
    assert plan.action == ReadinessGateAction.PROCEED
