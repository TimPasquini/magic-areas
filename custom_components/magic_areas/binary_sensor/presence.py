"""Main presence tracking entity for Magic Areas."""

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sun.const import STATE_ABOVE_HORIZON
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import (
    CalculationMode,
    MagicAreasEvents,
    MagicAreasFeatures,
)
from custom_components.magic_areas.entity import BinaryMagicEntity
from custom_components.magic_areas.const import (
    ATTR_ACTIVE_SENSORS,
    ATTR_AREAS,
    ATTR_CLEAR_TIMEOUT,
    ATTR_LAST_ACTIVE_SENSORS,
    ATTR_PRESENCE_SENSORS,
    ATTR_STATES,
    ATTR_TYPE,
    DOMAIN,
    ONE_MINUTE,
)
from custom_components.magic_areas.config_keys.area import (
    CONFIGURABLE_AREA_STATE_MAP,
)
from custom_components.magic_areas.core.config import (
    area_type,
    keep_only_entities,
    secondary_states_calculation_mode,
    secondary_states_config,
)
from custom_components.magic_areas.core.listener_registry import ListenerRegistry
from custom_components.magic_areas.core.meta import aggregate_secondary_states
from custom_components.magic_areas.core.presence_tracker import (
    PresenceTracker,
    PresenceUpdate,
    compute_secondary_states,
)
from custom_components.magic_areas.core.runtime_model import (
    build_presence_tracking_unique_id,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL_SECONDS = ONE_MINUTE
_STATE_DISPLAY_ORDER: tuple[str, ...] = (
    AreaStates.CLEAR.value,
    AreaStates.OCCUPIED.value,
    AreaStates.EXTENDED.value,
    AreaStates.SLEEP.value,
    AreaStates.ACCENT.value,
    AreaStates.DARK.value,
    AreaStates.BRIGHT.value,
)
_STATE_LABELS: dict[str, str] = {
    AreaStates.CLEAR.value: "Clear",
    AreaStates.OCCUPIED.value: "Occupied",
    AreaStates.EXTENDED.value: "Extended",
    AreaStates.SLEEP.value: "Sleep",
    AreaStates.ACCENT.value: "Accented",
    AreaStates.DARK.value: "Dark",
    AreaStates.BRIGHT.value: "Bright",
}


class AreaStateTrackerEntity(BinaryMagicEntity):
    """Tracks an area's state by tracking the configured entities."""

    ignore_non_state_change: bool = True
    _area_config_dict: dict[str, object]

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the area tracker."""

        BinaryMagicEntity.__init__(
            self, area_config, coordinator, domain=BINARY_SENSOR_DOMAIN
        )

        # Store config dict for local use (already have _area_id, _area_name, _is_meta from parent)
        self._area_config_dict = area_config.config

        self._clear_timeout_callback: Callable[[], None] | None = None
        self._presence_sensor_listener_remove: Callable[[], None] | None = None

        self._sensors: list[str] = []

        self._presence_tracker = PresenceTracker(
            hass=coordinator.hass,
            area_name=self._area_name,
            config=self._area_config_dict,
            is_meta=self._is_meta,
        )
        self._tracker = self._presence_tracker.tracker

        # Cache current states from tracker (no longer mutating self.area.states)
        self._current_states: list[str] = []

        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

        self._sensors = self._coordinator_presence_sensors()

        _LOGGER.debug("%s: presence tracker initialized", self._area_name)

    def _setup_tracking_listeners(self) -> None:
        # Track presence sensors
        self._track_presence_sensor_listener(self._sensors)

        # Track secondary states
        secondary_state_entities = self._configured_secondary_entity_ids()

        if secondary_state_entities:
            _LOGGER.debug(
                "%s: Secondary state tracking: %s",
                self._area_name,
                str(secondary_state_entities),
            )
            self._listener_registry.track(
                "secondary_state_change",
                async_track_state_change_event(
                    self.hass, secondary_state_entities, self._secondary_state_change
                ),
            )

        # Timed self update
        delta = timedelta(seconds=UPDATE_INTERVAL_SECONDS)
        self._listener_registry.track(
            "periodic_update",
            async_track_time_interval(self.hass, self._update_state, delta),
        )

        self._listener_registry.track("cleanup_timers", self._remove_clear_timeout)
        self._listener_registry.track(
            "cleanup_presence_listener", self._clear_presence_sensor_listener
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()

    # Public methods

    def get_metadata(self) -> dict[str, object]:
        """Return metadata information about the area's occupancy."""
        ordered_states = self._ordered_current_states()
        active_state_flags = {
            f"state_{state}": ("on" if state in ordered_states else "off")
            for state in _STATE_DISPLAY_ORDER
        }
        active_states_summary = ", ".join(
            _STATE_LABELS.get(state, state) for state in ordered_states
        )
        return {
            ATTR_PRESENCE_SENSORS: self._sensors,
            ATTR_ACTIVE_SENSORS: self._tracker.active_sensors,
            ATTR_LAST_ACTIVE_SENSORS: self._tracker.last_active_sensors,
            ATTR_STATES: ordered_states,  # Use cached states, not stale self.area.states
            "active_states": active_states_summary,
            ATTR_CLEAR_TIMEOUT: self._tracker.get_clear_timeout() / ONE_MINUTE,
            **active_state_flags,
        }

    def _ordered_current_states(self) -> list[str]:
        """Return current states in stable display order."""
        current_state_set = {str(state) for state in self._current_states}
        ordered = [
            state for state in _STATE_DISPLAY_ORDER if state in current_state_set
        ]
        remaining = sorted(current_state_set - set(_STATE_DISPLAY_ORDER))
        return [*ordered, *remaining]

    # Helpers

    def _coordinator_presence_sensors(self) -> list[str]:
        """Return presence sensors from coordinator snapshot."""
        if not self._coordinator.data:
            _LOGGER.debug(
                "%s: No coordinator data; skipping presence sensors", self._area_name
            )
            return []
        return self._coordinator.data.presence_sensors.copy()

    def _configured_secondary_entity_ids(self) -> list[str]:
        """Return configured secondary-state entity ids for this area."""
        secondary_config = secondary_states_config(self._area_config_dict)
        return [
            str(entity_id)
            for config_key in CONFIGURABLE_AREA_STATE_MAP.values()
            if (entity_id := secondary_config.get(config_key))
        ]

    def _clear_presence_sensor_listener(self) -> None:
        """Remove the current presence-sensor listener, if present."""
        if self._presence_sensor_listener_remove is None:
            return
        self._presence_sensor_listener_remove()
        self._presence_sensor_listener_remove = None

    def _track_presence_sensor_listener(self, sensors: list[str]) -> None:
        """Track state changes for the current presence sensor inventory."""
        self._clear_presence_sensor_listener()
        if not sensors:
            return
        self._presence_sensor_listener_remove = async_track_state_change_event(
            self.hass, sensors, self._sensor_state_change
        )

    # Entity state tracking & reporting
    def _secondary_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle area secondary state change event."""
        new_state = event.data["new_state"]
        if new_state is None:
            return

        changed = self._presence_tracker.handle_secondary_state_change(
            entity_id=event.data["entity_id"],
            to_state=new_state.state,
        )
        self._handle_tracker_event(changed)

    def _sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Actions when the sensor state has changed."""
        new_state = event.data["new_state"]
        if new_state is None:
            return

        old_state = event.data["old_state"]
        to_state = new_state.state

        changed = self._presence_tracker.handle_sensor_state_change(
            entity_id=event.data["entity_id"],
            to_state=to_state,
            old_state=old_state.state if old_state else None,
            ignore_non_state_change=self.ignore_non_state_change,
        )
        self._handle_tracker_event(changed, to_state=to_state)

    def _handle_tracker_event(
        self, changed: bool, *, to_state: str | None = None
    ) -> None:
        """Apply common event handling once the tracker accepts an event."""
        if not changed:
            return

        if to_state and to_state not in self._tracker.valid_on_states():
            self._remove_clear_timeout()

        self._schedule_state_refresh()

    def _schedule_state_refresh(self) -> None:
        """Schedule one state update on the HA loop."""
        self.hass.loop.call_soon_threadsafe(self._update_state, dt_util.utcnow())

    @callback
    def _update_state(self, extra: datetime | None = None) -> None:
        """Update the area's state and report changes."""
        now = extra if isinstance(extra, datetime) else dt_util.utcnow()
        update = self._evaluate_presence(now)
        self._apply_presence_update(update)

    def _evaluate_presence(self, now: datetime) -> PresenceUpdate:
        """Evaluate presence tracker state for one point in time."""
        secondary = self._get_secondary_states()
        keep_only = keep_only_entities(self._area_config_dict)
        return self._presence_tracker.update(
            sensor_ids=self._sensors,
            secondary_states=secondary,
            keep_only=keep_only,
            now=now,
        )

    def _apply_presence_update(self, update: PresenceUpdate) -> None:
        """Apply evaluated state transitions, timers, and event dispatch."""
        # Cache current states locally for get_metadata()
        self._current_states = list(update.current_states)

        # Handle timeout requests
        if update.cancel_timeout:
            self._remove_clear_timeout()
        if update.request_timeout is not None:
            self._schedule_clear_timeout(update.request_timeout)

        _LOGGER.debug(
            "%s: States updated. New states: %s / Lost states: %s",
            self._area_name,
            str(update.new_states),
            str(update.lost_states),
        )

        if update.new_states or update.lost_states:
            # Pass current_states snapshot to prevent stale reads in handlers.
            self._report_state_change(
                (update.new_states, update.lost_states, set(update.current_states))
            )

    def _report_state_change(
        self, states_tuple: tuple[set[str], set[str], set[str]]
    ) -> None:
        """Fire an event reporting area state change with state snapshot.

        Args:
            states_tuple: (new_states, lost_states, current_states) snapshot

        """
        new_states, lost_states, current_states = states_tuple
        _LOGGER.debug(
            "%s: Reporting state change (new states: %s/lost states: %s)",
            self._area_name,
            str(new_states),
            str(lost_states),
        )
        dispatcher_send(
            self.hass,
            MagicAreasEvents.AREA_STATE_CHANGED,
            self._area_id,
            (list(new_states), list(lost_states), list(current_states)),
        )

    # Area state calculations

    def _get_secondary_states(self) -> list[str]:
        """Return secondary states for an area."""
        configured_secondary_states = {
            key: str(value) if value is not None else None
            for key, value in secondary_states_config(self._area_config_dict).items()
        }
        entity_states: dict[str, str | None] = {}
        for entity_id in self._configured_secondary_entity_ids():
            entity = self.hass.states.get(entity_id)
            entity_states[entity_id] = entity.state if entity else None

        valid_on_states = set(self._tracker.valid_on_states([STATE_ABOVE_HORIZON]))

        return compute_secondary_states(
            secondary_states_config=configured_secondary_states,
            entity_states=entity_states,
            valid_on_states=valid_on_states,
        )

    # Clear timeout

    def _schedule_clear_timeout(self, delay_seconds: float) -> None:
        """Schedule a clear timeout with explicit delay."""
        _LOGGER.debug(
            "%s: Scheduling clear in %s seconds", self._area_name, delay_seconds
        )
        self._clear_timeout_callback = async_call_later(
            self.hass, delay_seconds, self._update_state
        )
        self._presence_tracker.record_timeout_set()

    def _remove_clear_timeout(self) -> None:
        if not self._clear_timeout_callback:
            return

        _LOGGER.debug(
            "%s: Clearing timeout",
            self._area_name,
        )

        # pylint: disable-next=not-callable
        self._clear_timeout_callback()
        self._clear_timeout_callback = None
        self._presence_tracker.record_timeout_cleared()


class AreaStateBinarySensor(AreaStateTrackerEntity, BinarySensorEntity):
    """Create an area presence sensor entity that tracks the current occupied state."""

    feature_id = MagicAreasFeatures.PRESENCE_TRACKING
    _area_icon: str

    # Init & Teardown

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the area presence binary sensor."""

        AreaStateTrackerEntity.__init__(self, area_config, coordinator)
        BinarySensorEntity.__init__(self)

        self._area_icon = area_config.icon or self.feature_info.icons.get(
            BINARY_SENSOR_DOMAIN, ""
        )

        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._attr_extra_state_attributes: dict[str, object] = {}
        self._attr_is_on: bool = False
        self._attr_icon = self._area_icon

    async def async_added_to_hass(self) -> None:
        """Call to add the system to hass."""
        await super().async_added_to_hass()
        await self.restore_state()
        await self._load_attributes()

        # Set up the listeners
        await self._setup_listeners()

        self.hass.loop.call_soon_threadsafe(self._update_state, dt_util.utcnow())

        _LOGGER.debug("%s: area presence binary sensor initialized", self._area_name)

    async def _setup_listeners(self) -> None:
        # Setup state change listener
        self._listener_registry.track(
            "area_state_dispatcher",
            async_dispatcher_connect(
                self.hass, MagicAreasEvents.AREA_STATE_CHANGED, self._area_state_changed
            ),
        )

        self._setup_tracking_listeners()

        # Listen for coordinator updates to pick up new presence sensors
        self._listener_registry.track(
            "coordinator_listener",
            self._coordinator.async_add_listener(self._handle_coordinator_update),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-read presence sensors when coordinator refreshes."""
        new_sensors = self._coordinator_presence_sensors()
        if set(new_sensors) == set(self._sensors):
            return

        self._apply_sensor_inventory_update(new_sensors)
        # HA may deliver this listener callback off-loop; keep scheduler writes.
        self.schedule_update_ha_state()

    # Helpers

    async def _load_attributes(self) -> None:
        self._attr_extra_state_attributes[ATTR_TYPE] = area_type(self._area_config_dict)
        self._sync_attributes()

    # Area change handlers
    def _area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""
        _new_states, _old_states, current_states = states_tuple

        if area_id != self._area_id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (req: %s}/self: %s)",
                self._area_name,
                area_id,
                self._area_id,
            )
            return

        _LOGGER.debug(
            "%s: Binary presence sensor detected area state change.", self._area_name
        )

        self._apply_state_projection(current_states)
        # HA may deliver this dispatcher callback off-loop; keep scheduler writes.
        self.schedule_update_ha_state()

    def _sync_attributes(self) -> None:
        """Refresh exposed metadata attributes."""
        self._attr_extra_state_attributes.update(self.get_metadata())

    def _apply_sensor_inventory_update(self, new_sensors: list[str]) -> None:
        """Apply snapshot-driven presence sensor inventory changes."""
        self._sensors = new_sensors
        self._track_presence_sensor_listener(new_sensors)

        self._sync_attributes()

    def _apply_state_projection(self, current_states: list[str]) -> None:
        """Project tracked current states onto the binary sensor state."""
        self._current_states = list(current_states)
        self._attr_is_on = AreaStates.OCCUPIED.value in current_states
        self._sync_attributes()


class MetaAreaStateBinarySensor(AreaStateBinarySensor):
    """Create an area presence sensor entity that tracks the current occupied state (Meta)."""

    ignore_non_state_change: bool = False

    async def _load_attributes(self) -> None:
        await super()._load_attributes()
        # Get child areas from coordinator snapshot (all child areas, not just active)
        child_areas = self._coordinator_child_areas(active_only=False)
        self._attr_extra_state_attributes.update(
            {
                ATTR_AREAS: child_areas,
            }
        )

    def _get_secondary_states(self) -> list[str]:
        """Return secondary states for an area through calculation."""

        mode: CalculationMode = CalculationMode(
            secondary_states_calculation_mode(self._area_config_dict)
        )

        # Get child areas from coordinator snapshot
        child_areas = self._coordinator_child_areas(active_only=True)
        child_state_lists: list[list[str]] = []

        entity_registry = er.async_get(self.hass)
        for area_id in child_areas:
            if not (
                area_entity_id := entity_registry.async_get_entity_id(
                    BINARY_SENSOR_DOMAIN,
                    DOMAIN,
                    build_presence_tracking_unique_id(area_id=area_id),
                )
            ):
                continue
            if not (area_state := self.hass.states.get(area_entity_id)):
                continue
            if not isinstance(states := area_state.attributes.get(ATTR_STATES), list):
                continue
            child_state_lists.append(states)

        return aggregate_secondary_states(
            child_state_lists=child_state_lists,
            mode=str(mode.value),
            configurable_states=list(CONFIGURABLE_AREA_STATE_MAP.keys()),
        )

    def _coordinator_child_areas(self, *, active_only: bool) -> list[str]:
        """Return child areas from coordinator snapshot."""
        if not self._coordinator.data:
            return []
        if active_only:
            return self._coordinator.data.active_areas
        return self._coordinator.data.child_areas
