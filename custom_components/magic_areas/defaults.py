"""Defaults that depend on Home Assistant enums."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor.const import SensorDeviceClass

from custom_components.magic_areas.policy import DISTRESS_SENSOR_CLASSES

DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS = [
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.OCCUPANCY,
    BinarySensorDeviceClass.PRESENCE,
]

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

DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES = [
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.OCCUPANCY,
]

DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES = DISTRESS_SENSOR_CLASSES

DEFAULT_FAN_GROUPS_TRACKED_DEVICE_CLASS = SensorDeviceClass.TEMPERATURE

FAN_GROUPS_ALLOWED_TRACKED_DEVICE_CLASS = [
    SensorDeviceClass.TEMPERATURE,
    SensorDeviceClass.HUMIDITY,
    SensorDeviceClass.CO,
    SensorDeviceClass.CO2,
    SensorDeviceClass.AQI,
    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
    SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
    SensorDeviceClass.NITROGEN_DIOXIDE,
    SensorDeviceClass.NITROGEN_MONOXIDE,
    SensorDeviceClass.GAS,
    SensorDeviceClass.OZONE,
    SensorDeviceClass.PM1,
    SensorDeviceClass.PM10,
    SensorDeviceClass.PM25,
    SensorDeviceClass.SULPHUR_DIOXIDE,
]
