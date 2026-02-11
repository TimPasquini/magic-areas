"""BLE Tracker binary sensor component."""

from datetime import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.config_keys import (
    CONF_BLE_TRACKER_ENTITIES,
)
from custom_components.magic_areas.attrs import (
    ATTR_ACTIVE_SENSORS,
)
from custom_components.magic_areas.core.listener_registry import (
    ListenerRegistry,
)
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoBLETrackers,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


class AreaBLETrackerBinarySensor(MagicEntity, BinarySensorEntity):
    """BLE Tracker monitoring sensor for the area."""

    feature_info = MagicAreasFeatureInfoBLETrackers()
    _sensors: list[str]
    _listener_registry: ListenerRegistry
    _area_id: str
    _area_name: str
    _area_slug: str

    def __init__(
        self, area_config: "AreaConfig", coordinator: "MagicAreasCoordinator"
    ) -> None:
        """Initialize the area presence binary sensor."""

        MagicEntity.__init__(self, area_config, coordinator, domain=BINARY_SENSOR_DOMAIN)
        BinarySensorEntity.__init__(self)

        feature_config = self.get_feature_config()
        self._sensors = feature_config.get(CONF_BLE_TRACKER_ENTITIES, [])

        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._attr_extra_state_attributes = {
            ATTR_ENTITY_ID: self._sensors,
            ATTR_ACTIVE_SENSORS: [],
        }
        self._attr_is_on: bool = False
        self._listener_registry = ListenerRegistry(logger_name=type(self).__module__)

    async def async_added_to_hass(self) -> None:
        """Call to add the system to hass."""
        await super().async_added_to_hass()
        await self.restore_state()

        # Set up the listeners
        await self._setup_listeners()

        self.hass.loop.call_soon_threadsafe(self._update_state, dt_util.utcnow())

        _LOGGER.debug("%s: BLE Tracker monitor sensor initialized", self._area_name)

    async def _setup_listeners(self) -> None:
        """Attach state change listeners."""
        self._listener_registry.track(
            "sensor_state_change",
            async_track_state_change_event(
                self.hass, self._sensors, self._sensor_state_change
            ),
        )

    def _sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Call update state from track state change event."""

        self._update_state()

    @callback
    def _update_state(self, extra: datetime | None = None) -> None:
        """Calculate state based off BLE tracker sensors."""

        calculated_state: bool = False
        active_sensors: list[str] = []

        for sensor in self._sensors:
            sensor_state = self.hass.states.get(sensor)

            if not sensor_state:
                continue

            normalized_state = sensor_state.state.lower()

            if (
                normalized_state == self._area_slug
                or normalized_state == self._area_id
                or normalized_state == self._area_name.lower()
            ):
                calculated_state = True
                active_sensors.append(sensor)

        _LOGGER.debug(
            "%s: BLE Tracker monitor sensor state change: %s -> %s",
            self._area_name,
            self._attr_is_on,
            calculated_state,
        )

        self._attr_is_on = calculated_state
        self._attr_extra_state_attributes[ATTR_ACTIVE_SENSORS] = active_sensors
        self.schedule_update_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners on removal."""
        self._listener_registry.cleanup()
        await super().async_will_remove_from_hass()
