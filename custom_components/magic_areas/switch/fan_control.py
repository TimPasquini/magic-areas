"""Fan Control switch."""

import logging
from enum import Enum
from typing import TYPE_CHECKING

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import (
    EntityCategory,
    STATE_OFF,
)
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.fan_control import (
    build_fan_control_group_policy,
    FanControlGroupPolicy,
    FanPolicySignals,
)
from custom_components.magic_areas.core.control_group import ControlGroupContext
from custom_components.magic_areas.core.control_group_executor import (
    execute_control_group_decision,
)
from custom_components.magic_areas.config_keys import (
    CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS,
)
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)
from custom_components.magic_areas.core.control_group_runtime import (
    resolve_group_entity_id,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.switch.base import SwitchBase

_LOGGER = logging.getLogger(__name__)


class FanControlSwitch(SwitchBase):
    """Switch to enable/disable fan control."""

    feature_id = MagicAreasFeatures.FAN_GROUPS
    _attr_entity_category = EntityCategory.CONFIG

    policy: FanControlGroupPolicy
    tracked_entity_id: str | None
    _tracked_device_class: str
    _last_states: list[str]
    _area_sensor_entity_id: str | None
    _fan_group_entity_id: str | None
    _listener_registry: ListenerRegistry

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the Fan control switch."""

        SwitchBase.__init__(self, area_config, coordinator)

        feature_config = self.get_feature_config()

        self._tracked_device_class = feature_config.get(
            CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS,
            DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS,
        )
        # Entity IDs resolved in async_added_to_hass from coordinator snapshot
        self.tracked_entity_id = None
        self._area_sensor_entity_id = None
        self._fan_group_entity_id = None

        # Build canonical control-group policy from feature configuration.
        self.policy = build_fan_control_group_policy(feature_config)
        self._last_states = []
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Resolve entity IDs from coordinator snapshot
        if self._coordinator.data:
            entity_refs = self._coordinator.data.entity_references
            self._area_sensor_entity_id = entity_refs.area_state_sensor
            self.tracked_entity_id = entity_refs.aggregates_by_device_class.get(
                self._tracked_device_class
            )
            self._fan_group_entity_id = entity_refs.fan_group

        # Direct entity registry lookup for any unresolved references
        from homeassistant.helpers import entity_registry as er
        from homeassistant.components.binary_sensor import DOMAIN as BS_DOMAIN
        from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN

        entity_registry = er.async_get(self.hass)
        if not self._area_sensor_entity_id:
            self._area_sensor_entity_id = entity_registry.async_get_entity_id(
                BS_DOMAIN, DOMAIN, f"presence_tracking_{self._area_id}_area_state"
            )
        if not self.tracked_entity_id:
            self.tracked_entity_id = entity_registry.async_get_entity_id(
                SENSOR_DOMAIN,
                DOMAIN,
                f"aggregates_{self._area_id}_aggregate_{self._tracked_device_class}",
            )
        if not self._fan_group_entity_id:
            self._fan_group_entity_id = resolve_group_entity_id(
                self.hass,
                area_id=self._area_id,
                policy_id="fan_groups",
                domain=FAN_DOMAIN,
            )

        self._listener_registry.track(
            "area_state_dispatcher",
            async_dispatcher_connect(
                self.hass, MagicAreasEvents.AREA_STATE_CHANGED, self.area_state_changed
            ),
        )
        if self.tracked_entity_id:
            self._listener_registry.track(
                "aggregate_sensor_state_change",
                async_track_state_change_event(
                    self.hass,
                    [self.tracked_entity_id],
                    self.aggregate_sensor_state_changed,
                ),
            )
        if self._area_sensor_entity_id:
            self._listener_registry.track(
                "area_sensor_state_change",
                async_track_state_change_event(
                    self.hass,
                    [self._area_sensor_entity_id],
                    self._area_sensor_state_changed,
                ),
            )

    async def aggregate_sensor_state_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Call update state from track state change event."""

        # Get current states from presence binary sensor (resolved in async_added_to_hass)
        current_states = self._last_states
        if not current_states and self._area_sensor_entity_id:
            state = self.hass.states.get(self._area_sensor_entity_id)
            if state and "states" in state.attributes:
                current_states = [
                    str(s.value) if isinstance(s, Enum) else str(s)
                    for s in state.attributes["states"]
                ]

        await self.run_logic(current_states)

    async def area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        if area_id != self._area_id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (event: %s/self: %s)",
                self.name,
                area_id,
                self._area_id,
            )
            return

        new_states, lost_states, current_states = states_tuple
        if not new_states and not lost_states:
            return
        self._last_states = current_states
        await self.run_logic(states=current_states)

    @callback
    def _area_sensor_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Ensure clear-state transitions trigger control reevaluation."""
        if not self.is_on:
            return

        new_state = event.data.get("new_state")
        if not new_state:
            return

        if new_state.state != STATE_OFF:
            return

        self.hass.async_create_task(self.run_logic([str(AreaStates.CLEAR)]))

    async def run_logic(self, states: list[str]) -> None:
        """Run fan control logic."""

        if not self.is_on:
            _LOGGER.debug("%s: Control disabled, skipping.", self.name)
            return

        # Read sensor value
        sensor_value = None
        if self.tracked_entity_id:
            sensor_state = self.hass.states.get(self.tracked_entity_id)
            if sensor_state:
                try:
                    sensor_value = float(sensor_state.state)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "%s: Could not parse sensor value from '%s'",
                        self.name,
                        sensor_state.state,
                    )
                    sensor_value = None
            else:
                _LOGGER.warning(
                    "%s: Tracked sensor entity '%s' is not found. Please ensure aggregates are enabled and the selected device class is configured.",
                    self.name,
                    self.tracked_entity_id,
                )

        fan_state = (
            self.hass.states.get(self._fan_group_entity_id)
            if self._fan_group_entity_id
            else None
        )
        context = ControlGroupContext(
            group_id=f"fan_groups_{self._area_id}",
            current_states=tuple(states),
            signals=FanPolicySignals(
                sensor_value=sensor_value,
                fan_group_entity_id=self._fan_group_entity_id,
                fan_group_state=fan_state.state if fan_state else None,
            ),
            is_enabled=self.is_on,
        )
        decision = self.policy.evaluate(context)
        _LOGGER.debug("%s: Decision: %s", self.name, decision.reason)

        await execute_control_group_decision(self.hass, decision)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()
