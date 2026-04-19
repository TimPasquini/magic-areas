"""Defaults and tuning values for cross-cutting area behavior."""

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.enums import CalculationMode
from custom_components.magic_areas.components import (
    BINARY_SENSOR_DOMAIN,
    DEVICE_TRACKER_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    REMOTE_DOMAIN,
)
from custom_components.magic_areas.policy import DISTRESS_SENSOR_CLASSES
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor.const import SensorDeviceClass

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

# Feature defaults
DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR = ""
DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED = ""
DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED = ""
DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP = ""

DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS = SensorDeviceClass.TEMPERATURE
DEFAULT_FAN_GROUPS_REQUIRED_STATE = AreaStates.EXTENDED
DEFAULT_FAN_GROUPS_SETPOINT = 0.0

DEFAULT_PRESENCE_HOLD_TIMEOUT = 0

DEFAULT_NOTIFY_STATES = [AreaStates.EXTENDED]

DEFAULT_WASP_IN_A_BOX_DELAY = 90
DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT = 0
DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES = [
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.OCCUPANCY,
]

# Aggregate / health defaults
DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES = [
    BinarySensorDeviceClass.CONNECTIVITY,
    BinarySensorDeviceClass.DOOR,
    BinarySensorDeviceClass.GARAGE_DOOR,
    BinarySensorDeviceClass.GAS,
    BinarySensorDeviceClass.HEAT,
    BinarySensorDeviceClass.LIGHT,
    BinarySensorDeviceClass.LOCK,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.MOVING,
    BinarySensorDeviceClass.OCCUPANCY,
    BinarySensorDeviceClass.PRESENCE,
    BinarySensorDeviceClass.PROBLEM,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.SOUND,
    BinarySensorDeviceClass.TAMPER,
    BinarySensorDeviceClass.UPDATE,
    BinarySensorDeviceClass.VIBRATION,
    BinarySensorDeviceClass.WINDOW,
]

DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES = [
    SensorDeviceClass.AQI,
    SensorDeviceClass.ATMOSPHERIC_PRESSURE,
    SensorDeviceClass.CO,
    SensorDeviceClass.CO2,
    SensorDeviceClass.CURRENT,
    SensorDeviceClass.ENERGY,
    SensorDeviceClass.ENERGY_STORAGE,
    SensorDeviceClass.GAS,
    SensorDeviceClass.HUMIDITY,
    SensorDeviceClass.ILLUMINANCE,
    SensorDeviceClass.IRRADIANCE,
    SensorDeviceClass.MOISTURE,
    SensorDeviceClass.NITROGEN_DIOXIDE,
    SensorDeviceClass.NITROGEN_MONOXIDE,
    SensorDeviceClass.NITROUS_OXIDE,
    SensorDeviceClass.OZONE,
    SensorDeviceClass.POWER,
    SensorDeviceClass.PRESSURE,
    SensorDeviceClass.SULPHUR_DIOXIDE,
    SensorDeviceClass.TEMPERATURE,
    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
]

DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES = DISTRESS_SENSOR_CLASSES

DEFAULT_AGGREGATES_MIN_ENTITIES = 2
DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD = 0
DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS = 0
