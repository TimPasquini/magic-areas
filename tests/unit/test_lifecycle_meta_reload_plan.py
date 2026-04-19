"""Unit tests for pure meta lifecycle reload planning helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from unittest.mock import patch

from custom_components.magic_areas.coordinator.pipeline.lifecycle import (
    MetaSnapshotRetryAction,
    ReloadScheduleAction,
    MetaReloadAction,
    build_reload_schedule_plan,
    build_meta_snapshot_retry_plan,
    build_meta_reload_plan,
    should_keep_existing_reload_schedule,
)
from custom_components.magic_areas.coordinator.pipeline.snapshot import MagicAreasData
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.meta_reload import ReloadDecision
from custom_components.magic_areas.core.runtime_model import AreaConfig, AreaRuntime
from custom_components.magic_areas.core.runtime_model.references import EntityReferences


def _make_snapshot(*, child_areas: list[str]) -> MagicAreasData:
    area_config = AreaConfig(
        id="interior",
        name="Interior",
        slug="interior",
        area_type="meta",
        config={},
        hass_config=MagicMock(),
    )
    return MagicAreasData(
        entities={},
        magic_entities={},
        presence_sensors=[],
        active_areas=[],
        child_areas=child_areas,
        config={},
        enabled_features=set(),
        feature_configs={},
        group_registry=GroupRegistry(),
        entity_references=EntityReferences(),
        area_config=area_config,
        area_runtime=AreaRuntime(),
        updated_at=datetime.now(UTC),
    )


def test_build_meta_reload_plan_waits_when_snapshot_missing() -> None:
    """Planning should request bounded retry while snapshot data is missing."""
    now = datetime.now(UTC)
    plan = build_meta_reload_plan(
        snapshot=None,
        meta_slug="interior",
        trigger_area_type="interior",
        trigger_area_id="kitchen",
        last_reload=now - timedelta(seconds=10),
        now=now,
    )
    assert plan.action == MetaReloadAction.WAIT_FOR_SNAPSHOT
    assert plan.delay_seconds == 0.0


def test_build_meta_reload_plan_executes_when_eligible() -> None:
    """Eligible trigger with expired throttle should execute reload."""
    now = datetime.now(UTC)
    plan = build_meta_reload_plan(
        snapshot=_make_snapshot(child_areas=["kitchen"]),
        meta_slug="interior",
        trigger_area_type="interior",
        trigger_area_id="kitchen",
        last_reload=now - timedelta(seconds=30),
        now=now,
    )
    assert plan.action == MetaReloadAction.EXECUTE_RELOAD
    assert plan.delay_seconds >= 0.0


def test_build_meta_reload_plan_retries_when_throttled() -> None:
    """Matched trigger within throttle window should produce retry plan."""
    now = datetime.now(UTC)
    with patch(
        "custom_components.magic_areas.coordinator.pipeline.lifecycle.evaluate_reload",
        return_value=ReloadDecision(
            should_reload=False,
            delay_seconds=0.0,
            reason="Throttled",
            retry_after_seconds=2.5,
        ),
    ):
        plan = build_meta_reload_plan(
            snapshot=_make_snapshot(child_areas=[]),
            meta_slug="global",
            trigger_area_type="interior",
            trigger_area_id="kitchen",
            last_reload=now - timedelta(seconds=1),
            now=now,
        )
    assert plan.action == MetaReloadAction.RETRY_LATER
    assert plan.delay_seconds == 2.5


def test_build_meta_reload_plan_skips_when_unmatched() -> None:
    """Unmatched area signal should skip without retry."""
    now = datetime.now(UTC)
    plan = build_meta_reload_plan(
        snapshot=_make_snapshot(child_areas=["kitchen"]),
        meta_slug="interior",
        trigger_area_type="exterior",
        trigger_area_id="garage",
        last_reload=now - timedelta(seconds=30),
        now=now,
    )
    assert plan.action == MetaReloadAction.SKIP
    assert plan.delay_seconds == 0.0


def test_should_keep_existing_reload_schedule() -> None:
    """Earlier existing schedule wins, later one is replaced."""
    assert should_keep_existing_reload_schedule(existing_when=10.0, next_when=12.0)
    assert should_keep_existing_reload_schedule(existing_when=10.0, next_when=10.0)
    assert not should_keep_existing_reload_schedule(existing_when=12.0, next_when=10.0)
    assert not should_keep_existing_reload_schedule(existing_when=None, next_when=10.0)


def test_build_meta_snapshot_retry_plan_schedules_when_under_cap() -> None:
    """Retry planner should schedule and increment while below cap."""
    plan = build_meta_snapshot_retry_plan(attempts=2, max_attempts=10)
    assert plan.action == MetaSnapshotRetryAction.SCHEDULE_RETRY
    assert plan.next_attempts == 3
    assert plan.retry_reason == "Meta snapshot unavailable; retry 3/10"


def test_build_meta_snapshot_retry_plan_drops_when_cap_reached() -> None:
    """Retry planner should drop and reset attempts at cap."""
    plan = build_meta_snapshot_retry_plan(attempts=10, max_attempts=10)
    assert plan.action == MetaSnapshotRetryAction.DROP_TRIGGER
    assert plan.next_attempts == 0
    assert plan.retry_reason is None


def test_build_reload_schedule_plan_skips_when_reloading() -> None:
    """In-flight reload should block additional scheduling."""
    plan = build_reload_schedule_plan(
        is_reloading=True,
        existing_when=None,
        next_when=10.0,
    )
    assert plan.action == ReloadScheduleAction.SKIP_RELOADING
    assert plan.should_cancel_existing is False


def test_build_reload_schedule_plan_keeps_earlier_existing_schedule() -> None:
    """Earlier existing callback should be retained for coalescing."""
    plan = build_reload_schedule_plan(
        is_reloading=False,
        existing_when=5.0,
        next_when=10.0,
    )
    assert plan.action == ReloadScheduleAction.KEEP_EXISTING
    assert plan.should_cancel_existing is False


def test_build_reload_schedule_plan_replaces_later_existing_schedule() -> None:
    """A sooner new callback should replace a later existing one."""
    plan = build_reload_schedule_plan(
        is_reloading=False,
        existing_when=10.0,
        next_when=5.0,
    )
    assert plan.action == ReloadScheduleAction.SCHEDULE
    assert plan.should_cancel_existing is True


def test_build_reload_schedule_plan_schedules_without_existing_handle() -> None:
    """No existing schedule should create a new callback without cancellation."""
    plan = build_reload_schedule_plan(
        is_reloading=False,
        existing_when=None,
        next_when=5.0,
    )
    assert plan.action == ReloadScheduleAction.SCHEDULE
    assert plan.should_cancel_existing is False
