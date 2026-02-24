"""Policy tables and behavior groupings for Magic Areas.

This module is allowed to import Home Assistant enums/constants.
Keep voluptuous/cv out of here.
"""

from __future__ import annotations

from custom_components.magic_areas.enums import MagicAreasFeatures
from homeassistant.components.alarm_control_panel.const import AlarmControlPanelState
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import (
    STATE_ON,
    STATE_OPEN,
    STATE_PLAYING,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

# Aggregates (binary_sensor)
AGGREGATE_BINARY_SENSOR_CLASSES = [
    BinarySensorDeviceClass.WINDOW,
    BinarySensorDeviceClass.DOOR,
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.LIGHT,
]

AGGREGATE_MODE_ALL = [
    BinarySensorDeviceClass.CONNECTIVITY,
    BinarySensorDeviceClass.PLUG,
]

# Aggregates (sensor)
AGGREGATE_SENSOR_CLASSES = (
    SensorDeviceClass.CURRENT,
    SensorDeviceClass.ENERGY,
    SensorDeviceClass.HUMIDITY,
    SensorDeviceClass.ILLUMINANCE,
    SensorDeviceClass.POWER,
    SensorDeviceClass.TEMPERATURE,
)

AGGREGATE_MODE_SUM = [
    SensorDeviceClass.POWER,
    SensorDeviceClass.CURRENT,
    SensorDeviceClass.ENERGY,
]

AGGREGATE_MODE_TOTAL_SENSOR = [
    SensorDeviceClass.ENERGY,
]

AGGREGATE_MODE_TOTAL_INCREASING_SENSOR = [
    SensorDeviceClass.GAS,
    SensorDeviceClass.WATER,
]

# Health related
DISTRESS_SENSOR_CLASSES = [
    BinarySensorDeviceClass.PROBLEM,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.GAS,
]
DISTRESS_STATES = [AlarmControlPanelState.TRIGGERED, STATE_ON, STATE_PROBLEM]

# Wasp in a Box
WASP_IN_A_BOX_WASP_DEVICE_CLASSES = [
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.OCCUPANCY,
    BinarySensorDeviceClass.PRESENCE,
]
WASP_IN_A_BOX_BOX_DEVICE_CLASSES = [
    BinarySensorDeviceClass.DOOR,
    BinarySensorDeviceClass.GARAGE_DOOR,
]

# Lists for config/validation/UI
ALL_BINARY_SENSOR_DEVICE_CLASSES = [cls.value for cls in BinarySensorDeviceClass]
ALL_SENSOR_DEVICE_CLASSES = [cls.value for cls in SensorDeviceClass]

# State groupings
PRESENCE_SENSOR_VALID_ON_STATES = [STATE_ON, STATE_OPEN, STATE_PLAYING]
INVALID_STATES = [STATE_UNAVAILABLE, STATE_UNKNOWN]

# Feature availability by area type
FEATURE_LIST_META = [
    MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
    MagicAreasFeatures.LIGHT_GROUPS,
    MagicAreasFeatures.COVER_GROUPS,
    MagicAreasFeatures.CLIMATE_CONTROL,
    MagicAreasFeatures.AGGREGATES,
    MagicAreasFeatures.HEALTH,
]

FEATURE_LIST = FEATURE_LIST_META + [
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
    MagicAreasFeatures.PRESENCE_HOLD,
    MagicAreasFeatures.BLE_TRACKER,
    MagicAreasFeatures.FAN_GROUPS,
    MagicAreasFeatures.WASP_IN_A_BOX,
]

FEATURE_LIST_GLOBAL = FEATURE_LIST_META
