"""Meta-area lifecycle orchestration for coordinator reload behavior."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Collection, Coroutine, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

from homeassistant.const import (
    ATTR_NAME,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_STATE_CHANGED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.device_registry import (
    EVENT_DEVICE_REGISTRY_UPDATED,
    EventDeviceRegistryUpdatedData,
    async_get as devicereg_async_get,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EventEntityRegistryUpdatedData,
    async_get as entityreg_async_get,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.components import (
    MAGICAREAS_UNIQUEID_PREFIX,
    MAGIC_DEVICE_ID_PREFIX,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.core.config import reload_on_registry_change
from custom_components.magic_areas.core.meta_reload import evaluate_reload
from custom_components.magic_areas.coordinator.pipeline.snapshot import MagicAreasData
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.components import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)
_EXPECTED_RELOAD_SCHEDULE_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)
_RELOAD_DEBOUNCE_SECONDS = 1.0
_RELOAD_WINDOW_SECONDS = 180.0
_MAX_WINDOW_RELOADS = 6


class MetaReloadAction(str, Enum):
    """Lifecycle action to apply for a meta snapshot-ready trigger."""

    WAIT_FOR_SNAPSHOT = "wait_for_snapshot"
    EXECUTE_RELOAD = "execute_reload"
    RETRY_LATER = "retry_later"
    SKIP = "skip"


class MetaSnapshotRetryAction(str, Enum):
    """Action for bounded retries while waiting for meta snapshot data."""

    SCHEDULE_RETRY = "schedule_retry"
    DROP_TRIGGER = "drop_trigger"


class ReloadScheduleAction(str, Enum):
    """Action to apply when processing a new scheduled callback request."""

    SKIP_RELOADING = "skip_reloading"
    KEEP_EXISTING = "keep_existing"
    SCHEDULE = "schedule"


@dataclass(frozen=True, slots=True)
class MetaReloadPlan:
    """Pure plan output for one meta-area snapshot-ready trigger."""

    action: MetaReloadAction
    delay_seconds: float
    reason: str


@dataclass(frozen=True, slots=True)
class MetaSnapshotRetryPlan:
    """Pure decision for one meta snapshot-unavailable retry attempt."""

    action: MetaSnapshotRetryAction
    next_attempts: int
    retry_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReloadSchedulePlan:
    """Pure decision for coalescing/scheduling one reload callback."""

    action: ReloadScheduleAction
    should_cancel_existing: bool


class ReadinessRequestAction(str, Enum):
    """Readiness convergence action for one request trigger."""

    SCHEDULE = "schedule"
    KEEP_PENDING = "keep_pending"
    SKIP_CAP = "skip_cap"


class ReadinessGateAction(str, Enum):
    """Initial gate action before readiness request planning."""

    PROCEED = "proceed"
    SKIP_DISABLED = "skip_disabled"
    SKIP_NOT_RUNNING = "skip_not_running"
    SKIP_IN_FLIGHT = "skip_in_flight"


@dataclass(frozen=True, slots=True)
class ReadinessRequestPlan:
    """Pure decision for handling one readiness reload request."""

    action: ReadinessRequestAction
    window_started_at: float
    reload_count: int


@dataclass(frozen=True, slots=True)
class ReadinessGatePlan:
    """Pure gate decision for readiness reload requests."""

    action: ReadinessGateAction


class ReadinessConvergenceManager:
    """Bounded convergence scheduler for non-meta runtime readiness signals."""

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        config_entry: MagicAreasConfigEntry,
        area_config: AreaConfig,
        get_snapshot: Callable[[], MagicAreasData | None],
        should_auto_reload: Callable[[], bool],
    ) -> None:
        """Initialize convergence manager."""
        self._hass = hass
        self._config_entry = config_entry
        self._area_config = area_config
        self._get_snapshot = get_snapshot
        self._should_auto_reload = should_auto_reload

        self._window_started_at: float | None = None
        self._reload_count = 0
        self._reload_in_flight = False
        self._pending_reload_handle: asyncio.TimerHandle | None = None
        self._pending_reason: str | None = None
        self._unsubscribe_state: Callable[[], None] | None = None

    def start(self) -> None:
        """Attach readiness listeners."""
        if self._unsubscribe_state is not None:
            return
        self._unsubscribe_state = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED,
            self._async_handle_state_readiness,
        )

    def shutdown(self) -> None:
        """Clean up listeners and pending callbacks."""
        if self._unsubscribe_state is not None:
            self._unsubscribe_state()
            self._unsubscribe_state = None
        if self._pending_reload_handle is not None:
            self._pending_reload_handle.cancel()
            self._pending_reload_handle = None

    @callback
    def request_reload(self, *, reason: str) -> None:
        """Request one coalesced reload with bounded retries."""
        gate_plan = build_readiness_gate_plan(
            auto_reload_enabled=self._should_auto_reload(),
            hass_is_running=self._hass.is_running,
            reload_in_flight=self._reload_in_flight,
        )

        if gate_plan.action == ReadinessGateAction.SKIP_DISABLED:
            _LOGGER.debug(
                "%s: Auto-Reloading disabled; skipping readiness reload (%s)",
                self._config_entry.data[ATTR_NAME],
                reason,
            )
            return
        if gate_plan.action == ReadinessGateAction.SKIP_NOT_RUNNING:
            return
        if gate_plan.action == ReadinessGateAction.SKIP_IN_FLIGHT:
            return

        plan = build_readiness_request_plan(
            now=self._hass.loop.time(),
            window_started_at=self._window_started_at,
            reload_count=self._reload_count,
            has_pending_handle=self._pending_reload_handle is not None,
        )
        self._window_started_at = plan.window_started_at
        self._reload_count = plan.reload_count

        if plan.action == ReadinessRequestAction.SKIP_CAP:
            _LOGGER.debug(
                "%s: Reached convergence reload cap (%s in %ss), skipping trigger (%s)",
                self._config_entry.data[ATTR_NAME],
                _MAX_WINDOW_RELOADS,
                _RELOAD_WINDOW_SECONDS,
                reason,
            )
            return

        self._pending_reason = reason
        if plan.action == ReadinessRequestAction.KEEP_PENDING:
            return

        self._pending_reload_handle = self._hass.loop.call_later(
            _RELOAD_DEBOUNCE_SECONDS,
            lambda: self._hass.async_create_task(self._async_execute_reload()),
        )

    async def _async_execute_reload(self) -> None:
        """Execute one scheduled readiness reload."""
        self._pending_reload_handle = None
        if self._reload_in_flight:
            return
        self._reload_in_flight = True
        self._reload_count += 1
        reason = self._pending_reason or "readiness trigger"
        _LOGGER.debug(
            "%s: Reloading entry due readiness convergence (%s)",
            self._config_entry.data[ATTR_NAME],
            reason,
        )
        try:
            await async_reload_entry(self._hass, self._config_entry)
        finally:
            self._reload_in_flight = False

    async def _async_handle_state_readiness(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Trigger convergence reload when tracked entities recover to a valid state."""
        snapshot = self._get_snapshot()
        if snapshot is None:
            return

        tracked_entity_ids = _snapshot_entity_ids(snapshot)
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        old_value = old_state.state if old_state is not None else None
        new_value = new_state.state if new_state is not None else None
        if not should_trigger_readiness_reload(
            entity_id=entity_id,
            tracked_entity_ids=tracked_entity_ids,
            old_value=old_value,
            new_value=new_value,
        ):
            return

        self.request_reload(reason=f"state readiness: {entity_id}")


def _snapshot_entity_ids(snapshot: MagicAreasData) -> set[str]:
    """Return all known entity IDs represented in a snapshot."""
    entity_ids: set[str] = set()
    for entities_by_domain in (snapshot.entities, snapshot.magic_entities):
        for entities in entities_by_domain.values():
            for entity in entities:
                entity_id = entity.get("entity_id")
                if isinstance(entity_id, str):
                    entity_ids.add(entity_id)
    entity_ids.update(snapshot.presence_sensors)
    entity_ids.update(
        entity_id
        for entity_id in (
            snapshot.entity_references.area_state_sensor,
            snapshot.entity_references.presence_hold_switch,
            snapshot.entity_references.light_control_switch,
            snapshot.entity_references.fan_group,
            snapshot.entity_references.fan_control_switch,
            snapshot.entity_references.media_player_group,
            snapshot.entity_references.media_player_control_switch,
            snapshot.entity_references.climate_control_switch,
            snapshot.entity_references.cover_group,
            snapshot.entity_references.cover_control_switch,
            snapshot.entity_references.wasp_in_a_box_sensor,
            snapshot.entity_references.ble_tracker_monitor,
            snapshot.entity_references.threshold_sensor,
            snapshot.entity_references.health_sensor,
        )
        if entity_id is not None
    )
    return entity_ids


def build_readiness_request_plan(
    *,
    now: float,
    window_started_at: float | None,
    reload_count: int,
    has_pending_handle: bool,
) -> ReadinessRequestPlan:
    """Build pure readiness convergence decision for one trigger request."""
    window_start = window_started_at
    count = reload_count
    if window_start is None or now - window_start > _RELOAD_WINDOW_SECONDS:
        window_start = now
        count = 0

    if count >= _MAX_WINDOW_RELOADS:
        return ReadinessRequestPlan(
            action=ReadinessRequestAction.SKIP_CAP,
            window_started_at=window_start,
            reload_count=count,
        )

    if has_pending_handle:
        return ReadinessRequestPlan(
            action=ReadinessRequestAction.KEEP_PENDING,
            window_started_at=window_start,
            reload_count=count,
        )

    return ReadinessRequestPlan(
        action=ReadinessRequestAction.SCHEDULE,
        window_started_at=window_start,
        reload_count=count,
    )


def build_readiness_gate_plan(
    *,
    auto_reload_enabled: bool,
    hass_is_running: bool,
    reload_in_flight: bool,
) -> ReadinessGatePlan:
    """Build pure initial gate decision for readiness reload requests."""
    if not auto_reload_enabled:
        return ReadinessGatePlan(action=ReadinessGateAction.SKIP_DISABLED)
    if not hass_is_running:
        return ReadinessGatePlan(action=ReadinessGateAction.SKIP_NOT_RUNNING)
    if reload_in_flight:
        return ReadinessGatePlan(action=ReadinessGateAction.SKIP_IN_FLIGHT)
    return ReadinessGatePlan(action=ReadinessGateAction.PROCEED)


def should_trigger_readiness_reload(
    *,
    entity_id: str | None,
    tracked_entity_ids: set[str],
    old_value: str | None,
    new_value: str | None,
) -> bool:
    """Return whether a state transition should trigger readiness convergence."""
    if entity_id is None:
        return False
    if _is_magicareas_entity(entity_id):
        # Ignore state recovery of Magic Areas entities themselves; those
        # transitions are a normal side effect of reloading and can form loops.
        return False
    if entity_id not in tracked_entity_ids:
        return False
    if new_value is None:
        return False
    if old_value not in (None, STATE_UNKNOWN, STATE_UNAVAILABLE):
        return False
    return new_value not in (STATE_UNKNOWN, STATE_UNAVAILABLE)


def _is_magicareas_entity(entity_id: str) -> bool:
    """Return whether an entity_id belongs to Magic Areas runtime entities."""
    parts = entity_id.split(".", 1)
    if len(parts) != 2:
        return False
    entity_part = parts[1]
    return entity_part.startswith(MAGICAREAS_UNIQUEID_PREFIX)


def _has_magicareas_device_identifier(
    identifiers: Collection[tuple[str, str]],
) -> bool:
    """Return whether device identifiers belong to a Magic Areas room device."""
    return any(
        domain == DOMAIN and identifier.startswith(MAGIC_DEVICE_ID_PREFIX)
        for domain, identifier in identifiers
    )


def _is_registry_event_relevant_to_area(
    *,
    area_id: str,
    action: str,
    changed_area_id: str | None,
    member_area_id: str | None,
) -> bool:
    """Return whether one registry event should trigger a reload for an area."""
    if action == "update" and changed_area_id is not None:
        if changed_area_id == area_id:
            return True
        return member_area_id == area_id
    if action in ("create", "remove"):
        return member_area_id == area_id or changed_area_id == area_id
    return False


def _extract_changed_area_id(changes: object) -> str | None:
    """Extract a normalized `changes.area_id` value from registry event payload."""
    if not isinstance(changes, Mapping):
        return None
    changed_area_id = changes.get("area_id")
    return changed_area_id if isinstance(changed_area_id, str) else None


class MetaAreaReloadManager:
    """Own meta-area snapshot-ready orchestration and reload scheduling."""

    _MAX_META_DATA_RETRIES = 10
    _META_DATA_RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        area_config: AreaConfig,
        get_snapshot: Callable[[], MagicAreasData | None],
        get_entry_id: Callable[[], str | None],
        schedule_reload: Callable[[str], None],
    ) -> None:
        """Initialize lifecycle manager."""
        self._hass = hass
        self._area_config = area_config
        self._get_snapshot = get_snapshot
        self._get_entry_id = get_entry_id
        self._schedule_reload = schedule_reload

        self._last_reload: datetime = datetime.min.replace(tzinfo=dt_util.UTC)
        self._reloading: bool = False
        self._unsubscribe_ready: Callable[[], None] | None = None
        self._unsubscribe_startup: Callable[[], None] | None = None
        self._pending_reload_handle: asyncio.TimerHandle | None = None
        self._reloading_guard_handle: asyncio.TimerHandle | None = None
        self._pending_trigger: tuple[str, str] | None = None
        self._meta_data_retry_attempts: int = 0

    def start(self) -> None:
        """Attach snapshot-ready listener."""
        if self._unsubscribe_ready is not None:
            return
        self._unsubscribe_ready = async_dispatcher_connect(
            self._hass,
            MagicAreasEvents.AREA_SNAPSHOT_READY,
            self.handle_snapshot_ready,
        )

    async def shutdown(self) -> None:
        """Clean up listeners and pending callbacks."""
        if self._unsubscribe_ready is not None:
            self._unsubscribe_ready()
            self._unsubscribe_ready = None
        if self._unsubscribe_startup is not None:
            self._unsubscribe_startup()
            self._unsubscribe_startup = None
        if self._pending_reload_handle is not None:
            self._pending_reload_handle.cancel()
            self._pending_reload_handle = None
        if self._reloading_guard_handle is not None:
            self._reloading_guard_handle.cancel()
            self._reloading_guard_handle = None

    @callback
    def handle_snapshot_ready(
        self,
        area_type: str,
        floor_id: int | None,
        area_id: str,
        _updated_at: str | None = None,
    ) -> None:
        """Handle snapshot-ready signals for meta-area reload."""
        _LOGGER.debug(
            "%s: Received area snapshot-ready signal (type=%s, floor_id=%s, area_id=%s)",
            self._area_config.name,
            area_type,
            floor_id,
            area_id,
        )

        if self._reloading:
            return

        self._pending_trigger = (area_type, area_id)

        if not self._hass.is_running:
            self._schedule_startup_retry()
            return

        self.evaluate_and_schedule_reload(
            trigger_area_type=area_type,
            trigger_area_id=area_id,
        )

    @callback
    def _schedule_startup_retry(self) -> None:
        """Schedule one startup callback to process pending readiness trigger."""
        if self._unsubscribe_startup is not None:
            return
        self._unsubscribe_startup = self._hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED,
            self.handle_started,
        )

    @callback
    def handle_started(self, *_args: object) -> None:
        """Process pending trigger once Home Assistant startup completes."""
        if self._unsubscribe_startup is not None:
            self._unsubscribe_startup()
            self._unsubscribe_startup = None
        if self._pending_trigger is None:
            return
        trigger_area_type, trigger_area_id = self._pending_trigger
        self.evaluate_and_schedule_reload(
            trigger_area_type=trigger_area_type,
            trigger_area_id=trigger_area_id,
        )

    @callback
    def evaluate_and_schedule_reload(
        self, trigger_area_type: str, trigger_area_id: str
    ) -> None:
        """Evaluate reload policy and schedule bounded convergence callbacks."""
        plan = build_meta_reload_plan(
            snapshot=self._get_snapshot(),
            meta_slug=self._area_config.slug,
            trigger_area_type=trigger_area_type,
            trigger_area_id=trigger_area_id,
            last_reload=self._last_reload,
            now=dt_util.utcnow(),
        )

        if plan.action == MetaReloadAction.WAIT_FOR_SNAPSHOT:
            self._schedule_meta_data_retry(trigger_area_type, trigger_area_id)
            return

        if plan.action == MetaReloadAction.EXECUTE_RELOAD:
            self._schedule_meta_reload_callback(
                delay=plan.delay_seconds,
                callback=self.async_execute_reload,
                trigger_area_type=trigger_area_type,
                trigger_area_id=trigger_area_id,
                reason=plan.reason,
            )
            return

        if plan.action == MetaReloadAction.RETRY_LATER:
            self._schedule_meta_reload_callback(
                delay=plan.delay_seconds,
                callback=self.async_retry_reload,
                trigger_area_type=trigger_area_type,
                trigger_area_id=trigger_area_id,
                reason=plan.reason,
            )
            return

        _LOGGER.debug("%s: Reload skipped - %s", self._area_config.name, plan.reason)
        self._meta_data_retry_attempts = 0

    def _schedule_meta_reload_callback(
        self,
        *,
        delay: float,
        callback: Callable[[str, str], Coroutine[object, object, None]],
        trigger_area_type: str,
        trigger_area_id: str,
        reason: str,
    ) -> None:
        """Schedule meta callback and reset retry attempts."""
        self._meta_data_retry_attempts = 0
        self.schedule_reload_handle(
            delay=delay,
            callback=callback,
            trigger_area_type=trigger_area_type,
            trigger_area_id=trigger_area_id,
            reason=reason,
        )

    @callback
    def _schedule_meta_data_retry(
        self, trigger_area_type: str, trigger_area_id: str
    ) -> None:
        """Schedule bounded retries while waiting for meta snapshot data."""
        retry_plan = build_meta_snapshot_retry_plan(
            attempts=self._meta_data_retry_attempts,
            max_attempts=self._MAX_META_DATA_RETRIES,
        )

        if retry_plan.action == MetaSnapshotRetryAction.DROP_TRIGGER:
            _LOGGER.warning(
                "%s: Snapshot-ready trigger dropped after %s retries for area %s",
                self._area_config.name,
                self._MAX_META_DATA_RETRIES,
                trigger_area_id,
            )
            self._meta_data_retry_attempts = retry_plan.next_attempts
            return

        self._meta_data_retry_attempts = retry_plan.next_attempts
        self.schedule_reload_handle(
            delay=self._META_DATA_RETRY_DELAY_SECONDS,
            callback=self.async_retry_reload,
            trigger_area_type=trigger_area_type,
            trigger_area_id=trigger_area_id,
            reason=retry_plan.retry_reason or "Meta snapshot unavailable",
        )

    @callback
    def schedule_reload_handle(
        self,
        *,
        delay: float,
        callback: Callable[[str, str], Coroutine[object, object, None]],
        trigger_area_type: str,
        trigger_area_id: str,
        reason: str,
    ) -> None:
        """Schedule one coalesced reload callback."""
        loop = self._hass.loop
        when = loop.time() + delay
        existing_when = (
            self._pending_reload_handle.when() if self._pending_reload_handle else None
        )
        plan = build_reload_schedule_plan(
            is_reloading=self._reloading,
            existing_when=existing_when,
            next_when=when,
        )

        if plan.action == ReloadScheduleAction.SKIP_RELOADING:
            return
        if plan.action == ReloadScheduleAction.KEEP_EXISTING:
            _LOGGER.debug(
                "%s: Keeping existing reload schedule (new trigger: %s)",
                self._area_config.name,
                reason,
            )
            return

        if plan.should_cancel_existing and self._pending_reload_handle is not None:
            self._pending_reload_handle.cancel()

        _LOGGER.debug(
            "%s: Scheduled reload callback in %.2fs (%s)",
            self._area_config.name,
            delay,
            reason,
        )
        self._pending_reload_handle = loop.call_later(
            delay,
            lambda: self._hass.async_create_task(
                callback(trigger_area_type, trigger_area_id)
            ),
        )

    async def async_retry_reload(
        self, trigger_area_type: str, trigger_area_id: str
    ) -> None:
        """Re-evaluate a throttled trigger after waiting out throttle."""
        self._pending_reload_handle = None
        self.evaluate_and_schedule_reload(
            trigger_area_type=trigger_area_type,
            trigger_area_id=trigger_area_id,
        )

    async def async_execute_reload(
        self, trigger_area_type: str, trigger_area_id: str
    ) -> None:
        """Execute one scheduled reload."""
        self._pending_reload_handle = None
        if self._reloading:
            return
        entry_id = self._get_entry_id()
        if not entry_id:
            return
        self._last_reload = dt_util.utcnow()
        self._reloading = True
        if self._reloading_guard_handle is not None:
            self._reloading_guard_handle.cancel()
        self._reloading_guard_handle = self._hass.loop.call_later(
            30.0, self._clear_reloading_guard
        )
        _LOGGER.info(
            "%s: Reloading entry from snapshot-ready signal (type=%s, area=%s)",
            self._area_config.name,
            trigger_area_type,
            trigger_area_id,
        )
        try:
            self._schedule_reload(entry_id)
        except _EXPECTED_RELOAD_SCHEDULE_ERRORS:
            self._reloading = False
            if self._reloading_guard_handle is not None:
                self._reloading_guard_handle.cancel()
                self._reloading_guard_handle = None
            raise

    @callback
    def _clear_reloading_guard(self) -> None:
        """Reset stale in-flight reload guard when manager remains alive."""
        self._reloading_guard_handle = None
        if not self._reloading:
            return
        _LOGGER.debug("%s: Clearing stale reload guard", self._area_config.name)
        self._reloading = False


def build_meta_reload_plan(
    *,
    snapshot: MagicAreasData | None,
    meta_slug: str,
    trigger_area_type: str,
    trigger_area_id: str,
    last_reload: datetime,
    now: datetime,
) -> MetaReloadPlan:
    """Build a pure execution plan for one meta reload trigger."""
    if snapshot is None:
        return MetaReloadPlan(
            action=MetaReloadAction.WAIT_FOR_SNAPSHOT,
            delay_seconds=0.0,
            reason="Meta snapshot unavailable",
        )

    decision = evaluate_reload(
        meta_slug=meta_slug,
        trigger_area_type=trigger_area_type,
        trigger_area_id=trigger_area_id,
        child_areas=snapshot.child_areas,
        last_reload=last_reload,
        now=now,
    )

    if decision.should_reload:
        return MetaReloadPlan(
            action=MetaReloadAction.EXECUTE_RELOAD,
            delay_seconds=max(0.0, decision.delay_seconds),
            reason=decision.reason,
        )

    if decision.retry_after_seconds > 0:
        return MetaReloadPlan(
            action=MetaReloadAction.RETRY_LATER,
            delay_seconds=decision.retry_after_seconds,
            reason=decision.reason,
        )

    return MetaReloadPlan(
        action=MetaReloadAction.SKIP,
        delay_seconds=0.0,
        reason=decision.reason,
    )


def build_meta_snapshot_retry_plan(
    *,
    attempts: int,
    max_attempts: int,
) -> MetaSnapshotRetryPlan:
    """Build bounded retry plan while waiting for meta snapshot data."""
    if attempts >= max_attempts:
        return MetaSnapshotRetryPlan(
            action=MetaSnapshotRetryAction.DROP_TRIGGER,
            next_attempts=0,
            retry_reason=None,
        )

    next_attempts = attempts + 1
    return MetaSnapshotRetryPlan(
        action=MetaSnapshotRetryAction.SCHEDULE_RETRY,
        next_attempts=next_attempts,
        retry_reason=f"Meta snapshot unavailable; retry {next_attempts}/{max_attempts}",
    )


def build_reload_schedule_plan(
    *,
    is_reloading: bool,
    existing_when: float | None,
    next_when: float,
) -> ReloadSchedulePlan:
    """Build pure coalescing/scheduling decision for a reload callback."""
    if is_reloading:
        return ReloadSchedulePlan(
            action=ReloadScheduleAction.SKIP_RELOADING,
            should_cancel_existing=False,
        )

    if should_keep_existing_reload_schedule(
        existing_when=existing_when,
        next_when=next_when,
    ):
        return ReloadSchedulePlan(
            action=ReloadScheduleAction.KEEP_EXISTING,
            should_cancel_existing=False,
        )

    return ReloadSchedulePlan(
        action=ReloadScheduleAction.SCHEDULE,
        should_cancel_existing=existing_when is not None,
    )


def should_keep_existing_reload_schedule(
    *,
    existing_when: float | None,
    next_when: float,
) -> bool:
    """Return True when existing scheduled callback should be preserved."""
    return existing_when is not None and existing_when <= next_when


def make_entity_registry_filter(
    hass: HomeAssistant, area_id: str
) -> Callable[[EventEntityRegistryUpdatedData], bool]:
    """Create entity register filter for an area."""

    def _entity_registry_filter(event_data: EventEntityRegistryUpdatedData) -> bool:
        """Filter entity registry events relevant to this area."""
        entity_id = event_data["entity_id"]

        if _is_magicareas_entity(entity_id):
            return False

        entity_registry = entityreg_async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)
        entity_area_id = entity_entry.area_id if entity_entry else None
        changed_area_id = _extract_changed_area_id(event_data.get("changes"))

        return _is_registry_event_relevant_to_area(
            area_id=area_id,
            action=event_data["action"],
            changed_area_id=changed_area_id,
            member_area_id=entity_area_id,
        )

    return callback(_entity_registry_filter)


def make_device_registry_filter(
    hass: HomeAssistant, area_id: str
) -> Callable[[EventDeviceRegistryUpdatedData], bool]:
    """Create device register filter for an area."""

    def _device_registry_filter(event_data: EventDeviceRegistryUpdatedData) -> bool:
        """Filter device registry events relevant to this area."""
        device_registry = devicereg_async_get(hass)
        device_entry = device_registry.async_get(event_data["device_id"])
        if device_entry and _has_magicareas_device_identifier(device_entry.identifiers):
            return False
        device_area_id = device_entry.area_id if device_entry else None
        changed_area_id = _extract_changed_area_id(event_data.get("changes"))

        return _is_registry_event_relevant_to_area(
            area_id=area_id,
            action=event_data["action"],
            changed_area_id=changed_area_id,
            member_area_id=device_area_id,
        )

    return callback(_device_registry_filter)


async def async_reload_entry(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> None:
    """Trigger a reload by updating the entry data timestamp."""
    if not hass.is_running:
        return

    hass.config_entries.async_update_entry(
        config_entry,
        data={**config_entry.data, "entity_ts": dt_util.utcnow()},
    )


def _merged_area_config_data(config_entry: MagicAreasConfigEntry) -> dict[str, object]:
    """Return merged config+options data used by reload policy checks."""
    area_data: dict[str, object] = dict(config_entry.data)
    if config_entry.options:
        area_data.update(config_entry.options)
    return area_data


def _runtime_snapshot(config_entry: MagicAreasConfigEntry) -> MagicAreasData | None:
    """Return current coordinator snapshot from runtime entry data when available."""
    runtime_data = getattr(config_entry, "runtime_data", None)
    if runtime_data is None:
        return None
    coordinator = getattr(runtime_data, "coordinator", None)
    if coordinator is None:
        return None
    data = getattr(coordinator, "data", None)
    return data if isinstance(data, MagicAreasData) else None


def attach_registry_listeners(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    area_config: AreaConfig,
    tracked_listeners: list[Callable[[], None]],
) -> None:
    """Attach entity/device registry listeners for a non-meta area."""

    def _auto_reload_enabled() -> bool:
        return reload_on_registry_change(_merged_area_config_data(config_entry))

    manager = ReadinessConvergenceManager(
        hass=hass,
        config_entry=config_entry,
        area_config=area_config,
        get_snapshot=lambda: _runtime_snapshot(config_entry),
        should_auto_reload=_auto_reload_enabled,
    )
    manager.start()
    tracked_listeners.append(manager.shutdown)

    async def _handle_registry(
        _event: Event[EventEntityRegistryUpdatedData]
        | Event[EventDeviceRegistryUpdatedData],
    ) -> None:
        manager.request_reload(reason="entity registry change")

    entity_filter = make_entity_registry_filter(hass, area_config.id)
    tracked_listeners.append(
        hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, _handle_registry, entity_filter)
    )
    device_filter = make_device_registry_filter(hass, area_config.id)
    tracked_listeners.append(
        hass.bus.async_listen(EVENT_DEVICE_REGISTRY_UPDATED, _handle_registry, device_filter)
    )
