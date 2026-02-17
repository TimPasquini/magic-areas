"""Main presence tracking entity for Magic Areas."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

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

from custom_components.magic_areas.policy import (
    INVALID_STATES,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import MagicAreasEvents

from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfo,
    MagicAreasFeatureInfoPresenceTracking,
)
from custom_components.magic_areas.base.entities import BinaryMagicEntity
from custom_components.magic_areas.attrs import (
    ATTR_ACTIVE_SENSORS,
    ATTR_AREAS,
    ATTR_CLEAR_TIMEOUT,
    ATTR_LAST_ACTIVE_SENSORS,
    ATTR_PRESENCE_SENSORS,
    ATTR_STATES,
    ATTR_TYPE,
)
from custom_components.magic_areas.config_keys import (
    CONF_KEEP_ONLY_ENTITIES,
    CONF_SECONDARY_STATES,
    CONF_SECONDARY_STATES_CALCULATION_MODE,
    CONF_TYPE,
    DEFAULT_SECONDARY_STATES_CALCULATION_MODE,
    EMPTY_STRING,
    CalculationMode,
)
from custom_components.magic_areas.area_maps import (
    CONFIGURABLE_AREA_STATE_MAP,
)
from custom_components.magic_areas.const import (
    DOMAIN,
    ONE_MINUTE,
    UPDATE_INTERVAL,
)
from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)
from custom_components.magic_areas.core.meta import aggregate_secondary_states
from custom_components.magic_areas.core.occupancy import AreaOccupancyTracker

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


class AreaStateTrackerEntity(BinaryMagicEntity):
    """Tracks an area's state by tracking the configured entities."""

    ignore_non_state_change: bool = True
    _area_config_dict: dict[str, Any]

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the area tracker."""

        BinaryMagicEntity.__init__(self, area_config, coordinator, domain=BINARY_SENSOR_DOMAIN)

        # Store config dict for local use (already have _area_id, _area_name, _is_meta from parent)
        self._area_config_dict = area_config.config

        self._clear_timeout_callback: Callable[[], None] | None = None

        self._sensors: list[str] = []

        self._tracker = AreaOccupancyTracker(
            config=self._area_config_dict, is_meta=self._is_meta
        )

        # Cache current states from tracker (no longer mutating self.area.states)
        self._current_states: list[str] = []

        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

        self._load_presence_sensors()

        _LOGGER.debug("%s: presence tracker initialized", self._area_name)

    def _setup_tracking_listeners(self) -> None:
        # Track presence sensor
        self._listener_registry.track(
            "presence_sensor_state_change",
            async_track_state_change_event(
                self.hass, self._sensors, self._sensor_state_change
            ),
        )

        # Track secondary states
        secondary_state_entities: list[str] = []
        configurable_states = self._get_configured_secondary_states()

        for configurable_state in configurable_states:
            configurable_state_entity = CONFIGURABLE_AREA_STATE_MAP[configurable_state]
            tracked_entity = self._area_config_dict.get(CONF_SECONDARY_STATES, {}).get(
                configurable_state_entity, None
            )
            if not tracked_entity:
                continue

            secondary_state_entities.append(tracked_entity)

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
        delta = timedelta(seconds=UPDATE_INTERVAL)
        self._listener_registry.track(
            "periodic_update",
            async_track_time_interval(self.hass, self._update_state, delta),
        )

        self._listener_registry.track("cleanup_timers", self._cleanup_timers)

    @callback
    def _cleanup_timers(self) -> None:
        """Remove pending timers."""
        self._remove_clear_timeout()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()

    # Public methods

    def get_sensors(self) -> list[str]:
        """Return sensors used for tracking."""
        return self._sensors

    def get_metadata(self) -> dict[str, Any]:
        """Return metadata information about the area's occupancy."""
        return {
            ATTR_PRESENCE_SENSORS: self._sensors,
            ATTR_ACTIVE_SENSORS: self._tracker.active_sensors,
            ATTR_LAST_ACTIVE_SENSORS: self._tracker.last_active_sensors,
            ATTR_STATES: self._current_states,  # Use cached states, not stale self.area.states
            ATTR_CLEAR_TIMEOUT: self._tracker.get_clear_timeout() / ONE_MINUTE,
        }

    # Helpers

    def _get_configured_secondary_states(self) -> list[AreaStates]:
        """Return configured secondary states."""
        secondary_states: list[AreaStates] = []

        for (
            configurable_state,
            configurable_state_entity,
        ) in CONFIGURABLE_AREA_STATE_MAP.items():
            secondary_state_entity = self._area_config_dict.get(
                CONF_SECONDARY_STATES, {}
            ).get(configurable_state_entity, None)

            if not secondary_state_entity:
                continue

            secondary_states.append(configurable_state)

        return secondary_states

    # Entity loading

    def _load_presence_sensors(self) -> None:
        """Load sensors that are relevant for presence sensing."""
        if self._coordinator.data:
            self._sensors = self._coordinator.data.presence_sensors.copy()
            return

        _LOGGER.debug(
            "%s: No coordinator data; skipping presence sensors", self._area_name
        )
        self._sensors = []

    # Entity state tracking & reporting
    def _secondary_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle area secondary state change event."""
        if event.data["new_state"] is None:
            return None

        to_state = event.data["new_state"].state
        entity_id = event.data["entity_id"]

        _LOGGER.debug(
            "%s: Secondary state change: entity '%s' changed to %s",
            self._area_name,
            entity_id,
            to_state,
        )

        if to_state in INVALID_STATES:
            _LOGGER.debug(
                "%s: sensor '%s' has invalid state %s",
                self._area_name,
                entity_id,
                to_state,
            )
            return None

        self.hass.loop.call_soon_threadsafe(self._update_state, dt_util.utcnow())
        return None

    def _sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Actions when the sensor state has changed."""
        if event.data["new_state"] is None:
            return

        # Ignore state reports that aren't really a state change
        if (
            self.ignore_non_state_change
            and event.data["old_state"]
            and event.data["new_state"].state == event.data["old_state"].state
        ):
            return

        to_state = event.data["new_state"].state
        entity_id = event.data["entity_id"]

        _LOGGER.debug(
            "%s: sensor '%s' changed to {%s}",
            self._area_name,
            entity_id,
            to_state,
        )

        if to_state in INVALID_STATES:
            _LOGGER.debug(
                "%s: sensor '%s' has invalid state %s",
                self._area_name,
                entity_id,
                to_state,
            )
            return

        if to_state and to_state not in self._tracker.valid_on_states():
            _LOGGER.debug(
                "Setting last non-normal time %s %s",
                event.data["old_state"],
                event.data["new_state"],
            )
            self._tracker.record_sensor_off(dt_util.utcnow())
            # Clear the timeout
            self._remove_clear_timeout()

        self.hass.loop.call_soon_threadsafe(self._update_state, dt_util.utcnow())

    async def _async_update_state(self, timeout: int) -> None:
        await asyncio.sleep(timeout)
        self._update_state()

    @callback
    def _update_state(self, extra: datetime | None = None) -> None:
        """Update the area's state and report changes."""
        now = extra if isinstance(extra, datetime) else dt_util.utcnow()

        # Build sensor state dict from HA
        sensor_states: dict[str, str | None] = {}
        for sensor_id in self._sensors:
            try:
                entity = self.hass.states.get(sensor_id)
                sensor_states[sensor_id] = entity.state if entity else None
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.error(
                    "%s: Error getting entity state for '%s': %s",
                    self._area_name,
                    sensor_id,
                    str(e),
                )
                sensor_states[sensor_id] = None

        # Compute secondary states (overridden in MetaAreaStateBinarySensor)
        secondary = self._get_secondary_states()
        keep_only = self._area_config_dict.get(CONF_KEEP_ONLY_ENTITIES, [])

        # Run state machine
        update = self._tracker.update(sensor_states, secondary, keep_only, now)

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

        # Always report (matches original — dispatches even on no-change)
        # Pass current_states snapshot to prevent stale reads in handlers
        self._report_state_change((update.new_states, update.lost_states, set(update.current_states)))

    def _report_state_change(
        self, states_tuple: tuple[set[str], set[str], set[str]] = (set(), set(), set())
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

        states: list[str] = []

        configurable_states = self._get_configured_secondary_states()

        # Assume AreaStates.DARK if not configured
        if AreaStates.DARK not in configurable_states:
            states.append(AreaStates.DARK)

        for configurable_state in configurable_states:
            configurable_state_entity = CONFIGURABLE_AREA_STATE_MAP[configurable_state]

            secondary_state_entity = self._area_config_dict.get(
                CONF_SECONDARY_STATES, {}
            ).get(configurable_state_entity, None)

            if not secondary_state_entity:
                continue

            entity = self.hass.states.get(secondary_state_entity)
            if not entity:
                continue

            has_valid_state = entity.state.lower() in self._tracker.valid_on_states(
                [STATE_ABOVE_HORIZON]
            )
            state_to_add = None

            # Handle dark state from light sensor as an inverted configurable state
            inverted_states = [AreaStates.DARK]

            # Handle both forward and inverted configurable state
            if configurable_state in inverted_states:
                if not has_valid_state:
                    state_to_add = configurable_state
            else:
                if has_valid_state:
                    state_to_add = configurable_state

            if state_to_add:
                _LOGGER.debug(
                    "%s: Secondary state: %s is at %s, adding %s",
                    self._area_name,
                    secondary_state_entity,
                    entity.state.lower(),
                    configurable_state,
                )
                states.append(configurable_state)

        # Meta-state bright
        if AreaStates.DARK in configurable_states and AreaStates.DARK not in states:
            states.append(AreaStates.BRIGHT)

        return states

    # Clear timeout

    def _schedule_clear_timeout(self, delay_seconds: float) -> None:
        """Schedule a clear timeout with explicit delay."""
        _LOGGER.debug(
            "%s: Scheduling clear in %s seconds", self._area_name, delay_seconds
        )
        self._clear_timeout_callback = async_call_later(
            self.hass, delay_seconds, self._update_state
        )
        self._tracker.on_timeout_set()

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
        self._tracker.on_timeout_cleared()


class AreaStateBinarySensor(AreaStateTrackerEntity, BinarySensorEntity):
    """Create an area presence sensor entity that tracks the current occupied state."""

    feature_info: MagicAreasFeatureInfo = MagicAreasFeatureInfoPresenceTracking()
    _area_icon: str

    # Init & Teardown

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the area presence binary sensor."""

        AreaStateTrackerEntity.__init__(self, area_config, coordinator)
        BinarySensorEntity.__init__(self)

        self._area_icon = area_config.icon or self.feature_info.icons.get(
            BINARY_SENSOR_DOMAIN, EMPTY_STRING
        )

        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._attr_extra_state_attributes: dict[str, Any] = {}
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
            self._coordinator.async_add_listener(
                self._handle_coordinator_update
            ),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-read presence sensors when coordinator refreshes."""
        if not self._coordinator.data:
            return

        new_sensors = self._coordinator.data.presence_sensors.copy()
        if set(new_sensors) == set(self._sensors):
            return

        added = set(new_sensors) - set(self._sensors)
        self._sensors = new_sensors

        # Track newly added sensors for state changes
        if added:
            self._listener_registry.track(
                "added_sensor_state_change",
                async_track_state_change_event(
                    self.hass, list(added), self._sensor_state_change
                ),
            )

        # Update attributes with new sensor list
        self._attr_extra_state_attributes.update(self.get_metadata())
        self.schedule_update_ha_state()

    # Helpers

    async def _load_attributes(self) -> None:
        # Add common attributes
        self._attr_extra_state_attributes.update(
            {
                ATTR_STATES: [],
                ATTR_ACTIVE_SENSORS: [],
                ATTR_LAST_ACTIVE_SENSORS: [],
                ATTR_PRESENCE_SENSORS: [],
                ATTR_TYPE: self._area_config_dict.get(CONF_TYPE),
                ATTR_CLEAR_TIMEOUT: 0,
            }
        )

    # Area change handlers
    def _area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        new_states, old_states, current_states = states_tuple

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

        # Update local state cache from event payload (prevents stale metadata)
        self._current_states = list(current_states)

        # Use current_states from event payload (not stale HA state)
        # This ensures we get the correct occupied state immediately
        occupied_state = AreaStates.OCCUPIED.value
        self._attr_is_on = occupied_state in [str(s) for s in current_states]
        self._attr_extra_state_attributes.update(self.get_metadata())
        self.schedule_update_ha_state()


class MetaAreaStateBinarySensor(AreaStateBinarySensor):
    """Create an area presence sensor entity that tracks the current occupied state (Meta)."""

    ignore_non_state_change: bool = False

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the area presence binary sensor."""

        AreaStateBinarySensor.__init__(self, area_config, coordinator)

    async def _load_attributes(self) -> None:
        await super()._load_attributes()
        # Get child areas from coordinator snapshot (all child areas, not just active)
        child_areas = []
        if self._coordinator.data:
            child_areas = self._coordinator.data.child_areas
        self._attr_extra_state_attributes.update(
            {
                ATTR_AREAS: child_areas,
            }
        )

    def _get_secondary_states(self) -> list[str]:
        """Return secondary states for an area through calculation."""

        mode: CalculationMode = CalculationMode(
            self._area_config_dict.get(CONF_SECONDARY_STATES, {}).get(
                CONF_SECONDARY_STATES_CALCULATION_MODE,
                DEFAULT_SECONDARY_STATES_CALCULATION_MODE,
            )
        )

        # Get child areas from coordinator snapshot
        child_areas: list[str] = []
        if self._coordinator.data:
            child_areas = self._coordinator.data.active_areas
        child_state_lists: list[list[str]] = []

        entity_registry = er.async_get(self.hass)
        for area_slug in child_areas:
            area_entity_id = entity_registry.async_get_entity_id(
                BINARY_SENSOR_DOMAIN,
                DOMAIN,
                f"presence_tracking_{area_slug}_area_state",
            )
            if not area_entity_id:
                continue
            area_state = self.hass.states.get(area_entity_id)

            if not area_state:
                continue
            if ATTR_STATES not in area_state.attributes:
                continue
            child_state_lists.append(area_state.attributes[ATTR_STATES])

        return aggregate_secondary_states(
            child_state_lists=child_state_lists,
            mode=str(mode.value),
            configurable_states=list(CONFIGURABLE_AREA_STATE_MAP.keys()),
        )
