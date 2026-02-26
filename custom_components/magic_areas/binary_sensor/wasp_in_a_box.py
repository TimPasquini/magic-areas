"""Wasp in a box binary sensor component."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, EventStateChangedData, State, callback
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.magic_areas.entity import MagicEntity
from custom_components.magic_areas.config_keys import (
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_WASP_IN_A_BOX_DELAY,
    DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.const import (
    ONE_MINUTE,
)
from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)
from custom_components.magic_areas.core.wasp_state_machine import (
    WaspStateMachine,
    WaspStateUpdate,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.policy import (
    WASP_IN_A_BOX_BOX_DEVICE_CLASSES,
)
from custom_components.magic_areas.helpers.timer import ReusableTimer

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


ATTR_BOX = "box"
ATTR_WASP = "wasp"


class AreaWaspInABoxBinarySensor(MagicEntity, BinarySensorEntity):
    """Wasp In The Box logic tracking sensor for the area."""

    feature_id = MagicAreasFeatures.WASP_IN_A_BOX
    _area_id: str

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the area presence binary sensor."""

        MagicEntity.__init__(self, area_config, coordinator, domain=BINARY_SENSOR_DOMAIN)
        BinarySensorEntity.__init__(self)

        feature_config = self.get_feature_config()

        self._delay: int = feature_config.get(
            CONF_WASP_IN_A_BOX_DELAY, DEFAULT_WASP_IN_A_BOX_DELAY
        )

        self._wasp_timeout: int = feature_config.get(
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT, DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT
        )

        self._attr_device_class = BinarySensorDeviceClass.PRESENCE
        self._attr_is_on = False
        self._attr_extra_state_attributes = {
            ATTR_BOX: STATE_OFF,
            ATTR_WASP: STATE_OFF,
        }

        self._machine = WaspStateMachine(wasp_timeout=self._wasp_timeout)
        self._wasp_timer: ReusableTimer | None = None
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

        self._wasp_sensors: list[str] = []
        self._box_sensors: list[str] = []

    async def async_added_to_hass(self) -> None:
        """Call to add the entity to hass."""
        await super().async_added_to_hass()
        await self.restore_state()

        # Resolve aggregate sensor entity IDs from coordinator snapshot or entity registry
        from homeassistant.helpers import entity_registry as er
        from custom_components.magic_areas.const import DOMAIN

        entity_refs = None
        if self._coordinator.data:
            entity_refs = self._coordinator.data.entity_references

        entity_registry = er.async_get(self.hass)

        feature_config = self.get_feature_config()
        wasp_device_classes = feature_config.get(
            CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
            DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
        )

        for device_class in wasp_device_classes:
            dc_entity_id = (
                entity_refs.binary_aggregates_by_device_class.get(device_class)
                if entity_refs
                else None
            )
            if not dc_entity_id:
                dc_entity_id = entity_registry.async_get_entity_id(
                    BINARY_SENSOR_DOMAIN,
                    DOMAIN,
                    f"aggregates_{self._area_id}_aggregate_{device_class}",
                )
            if dc_entity_id:
                dc_state = self.hass.states.get(dc_entity_id)
                if dc_state:
                    self._wasp_sensors.append(dc_entity_id)

        for device_class in WASP_IN_A_BOX_BOX_DEVICE_CLASSES:
            dc_entity_id = (
                entity_refs.binary_aggregates_by_device_class.get(device_class)
                if entity_refs
                else None
            )
            if not dc_entity_id:
                dc_entity_id = entity_registry.async_get_entity_id(
                    BINARY_SENSOR_DOMAIN,
                    DOMAIN,
                    f"aggregates_{self._area_id}_aggregate_{device_class}",
                )
            if dc_entity_id:
                dc_state = self.hass.states.get(dc_entity_id)
                if dc_state:
                    self._box_sensors.append(dc_entity_id)

        # Initialize timer if timeout configured
        if self._wasp_timeout > 0:

            async def forget_wasp(now: Any) -> None:
                update = self._machine.on_wasp_timeout()
                self._apply_update(update)
                self.schedule_update_ha_state()

            self._wasp_timer = ReusableTimer(
                self.hass, self._wasp_timeout * ONE_MINUTE, forget_wasp
            )

        # Add listeners
        if self._wasp_sensors:
            self._listener_registry.track(
                "wasp_sensor_state_change",
                async_track_state_change_event(
                    self.hass, self._wasp_sensors, self._async_wasp_sensor_state_change
                ),
            )
        if self._box_sensors:
            self._listener_registry.track(
                "box_sensor_state_change",
                async_track_state_change_event(
                    self.hass, self._box_sensors, self._async_box_sensor_state_change
                ),
            )

    async def async_will_remove_from_hass(self) -> None:
        """Call to remove the entity to hass."""
        if self._wasp_timer:
            await self._wasp_timer.async_remove()
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()

    @callback
    async def _async_wasp_sensor_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Register wasp sensor state change event."""

        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")

        # Ignore state reports that aren't really a state change
        if new_state is None or old_state is None:
            return
        if new_state.state == old_state.state:
            return

        # Build current sensor states and update machine
        wasp_states = self._get_current_wasp_states()
        box_states = self._get_current_box_states()
        update = self._machine.update_all(wasp_states, box_states)
        self._apply_update(update)

    @callback
    async def _async_box_sensor_state_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Register box sensor state change event."""

        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")

        # Ignore state reports that aren't really a state change
        if new_state is None or old_state is None:
            return
        if new_state.state == old_state.state:
            return

        if self._delay:
            # Cancel timer and schedule delayed update
            if self._wasp_timer:
                self._wasp_timer.cancel()
            self.hass.loop.call_later(
                self._delay, self._on_box_delay_complete, new_state.state
            )
        else:
            # Immediate update
            wasp_states = self._get_current_wasp_states()
            box_states = self._get_current_box_states()
            update = self._machine.update_all(wasp_states, box_states)
            self._apply_update(update)

    def _on_box_delay_complete(self, box_state_at_event: str) -> None:
        """Handle completion of box sensor delay after close event."""
        # Get current states now that delay has elapsed
        wasp_states = self._get_current_wasp_states()
        box_states = self._get_current_box_states()
        update = self._machine.on_delay_complete(wasp_states, box_states)
        self._apply_update(update)

    def _get_current_wasp_states(self) -> dict[str, str]:
        """Get current state of all wasp sensors."""
        states = {}
        for sensor_id in self._wasp_sensors:
            state = self.hass.states.get(sensor_id)
            states[sensor_id] = state.state if state else STATE_OFF
        return states

    def _get_current_box_states(self) -> dict[str, str]:
        """Get current state of all box sensors."""
        states = {}
        for sensor_id in self._box_sensors:
            state = self.hass.states.get(sensor_id)
            states[sensor_id] = state.state if state else STATE_OFF
        return states

    def _apply_update(self, update: WaspStateUpdate) -> None:
        """Apply state machine update to HA state.

        Args:
            update: WaspStateUpdate result from state machine.

        """
        # Handle timer requests/cancellations
        if update.cancel_timer and self._wasp_timer:
            self._wasp_timer.cancel()
        elif update.request_timer is not None and self._wasp_timer:
            self._wasp_timer.cancel()  # Cancel existing

            # Start new timer with wasp timeout callback
            async def on_timer_expire(now: Any) -> None:
                result = self._machine.on_wasp_timeout()
                self._apply_update(result)
                self.schedule_update_ha_state()

            self._wasp_timer = ReusableTimer(
                self.hass, int(update.request_timer), on_timer_expire
            )
            self._wasp_timer.start()

        # Update HA state
        if self._attr_extra_state_attributes is None:
            self._attr_extra_state_attributes = {}

        # Determine current wasp and box states for attributes
        wasp_states = self._get_current_wasp_states()
        box_states = self._get_current_box_states()
        current_wasp = (
            STATE_ON if any(s == STATE_ON for s in wasp_states.values()) else STATE_OFF
        )
        current_box = (
            STATE_ON if any(s == STATE_ON for s in box_states.values()) else STATE_OFF
        )

        self._attr_extra_state_attributes[ATTR_BOX] = current_box
        self._attr_extra_state_attributes[ATTR_WASP] = current_wasp
        self._attr_is_on = update.is_present

        self.schedule_update_ha_state()
