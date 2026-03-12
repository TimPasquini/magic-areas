"""Aggregate/health feature default values."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor.const import SensorDeviceClass

from custom_components.magic_areas.policy import DISTRESS_SENSOR_CLASSES

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
