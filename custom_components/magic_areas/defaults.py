"""Defaults and tuning values for cross-cutting area behavior."""

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.enums import CalculationMode
from custom_components.magic_areas.ha_domains import (
    BINARY_SENSOR_DOMAIN,
    DEVICE_TRACKER_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    REMOTE_DOMAIN,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS = [
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.OCCUPANCY,
    BinarySensorDeviceClass.PRESENCE,
]

DEFAULT_TYPE = AreaType.INTERIOR

DEFAULT_PRESENCE_DEVICE_PLATFORMS = [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
]

ALL_PRESENCE_DEVICE_PLATFORMS = [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
    REMOTE_DOMAIN,
    DEVICE_TRACKER_DOMAIN,
]

DEFAULT_RELOAD_ON_REGISTRY_CHANGE = True
DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES = True

DEFAULT_CLEAR_TIMEOUT = 1
DEFAULT_CLEAR_TIMEOUT_META = 0

DEFAULT_SLEEP_TIMEOUT = DEFAULT_CLEAR_TIMEOUT
DEFAULT_EXTENDED_TIME = 5
DEFAULT_EXTENDED_TIMEOUT = 10

DEFAULT_SECONDARY_STATES_CALCULATION_MODE = CalculationMode.MAJORITY
