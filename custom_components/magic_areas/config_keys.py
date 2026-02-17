"""Configuration keys and primitive defaults organized by domain.

This module centralizes all configuration constants and their default values
for the Magic Areas integration. Keys are organized by functional category:

Categories:
    - **Area Identity**: CONF_ID, CONF_NAME, CONF_TYPE (basic area metadata)
    - **Feature Management**: CONF_ENABLED_FEATURES, CONF_SECONDARY_STATES
    - **Entity Selection**: Include/exclude/filter entity selection
    - **Presence Tracking**: Device platform selection and device class detection
    - **Aggregates**: Sensor grouping by device class and thresholds
    - **Health Monitoring**: Health sensor device classes
    - **Control Behavior**: Registry reload, diagnostic filtering
    - **Secondary State Timing**: Timeouts for area state transitions (clear, sleep, extended)
    - **Secondary State Entities**: Selectors for dark/accent/sleep state entities
    - **Notifications**: Media devices and trigger states
    - **Climate Control**: Entity selection and preset naming
    - **Fan Control**: Required state, device tracking, setpoint thresholds
    - **BLE Trackers**: Entity selection for Bluetooth tracking
    - **Wasp in a Box**: Door+motion hybrid detection tuning
    - **Presence Hold**: Manual occupancy override timeout
    - **Calculation Mode**: Aggregation strategy for secondary states

Note: This module contains configuration *keys* and *primitive* defaults only.
Feature-specific enum defaults (device class lists, state lists) are in defaults.py
to keep enum imports separate. Complex schema validation is in schemas/features.py.
"""

from __future__ import annotations

from typing import Any

from .const import EMPTY_STRING
from .area_state import (
    AreaStates,
    AreaType,
)
from .enums import CalculationMode
from .ha_domains import (
    BINARY_SENSOR_DOMAIN,
    DEVICE_TRACKER_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    REMOTE_DOMAIN,
)

CONF_ID = "id"
CONF_NAME, DEFAULT_NAME = "name", ""
CONF_TYPE, DEFAULT_TYPE = "type", AreaType.INTERIOR

CONF_ENABLED_FEATURES = "features"
DEFAULT_ENABLED_FEATURES: dict[str, Any] = {}

CONF_SECONDARY_STATES = "secondary_states"
DEFAULT_AREA_STATES: dict[str, Any] = {}

CONF_INCLUDE_ENTITIES = "include_entities"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_KEEP_ONLY_ENTITIES = "keep_only_entities"

(CONF_PRESENCE_DEVICE_PLATFORMS, DEFAULT_PRESENCE_DEVICE_PLATFORMS) = (
    "presence_device_platforms",
    [
        MEDIA_PLAYER_DOMAIN,
        BINARY_SENSOR_DOMAIN,
    ],
)
ALL_PRESENCE_DEVICE_PLATFORMS = [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
    REMOTE_DOMAIN,
    DEVICE_TRACKER_DOMAIN,
]

CONF_PRESENCE_SENSOR_DEVICE_CLASS = "presence_sensor_device_class"

CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES = (
    "aggregates_min_entities",
    2,
)
CONF_AGGREGATES_SENSOR_DEVICE_CLASSES = "aggregates_sensor_device_classes"
CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES = "aggregates_binary_sensor_device_classes"

CONF_AGGREGATES_ILLUMINANCE_THRESHOLD, DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD = (
    "aggregates_illuminance_threshold",
    0,
)
(
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
) = (
    "aggregates_illuminance_threshold_hysteresis",
    0,
)

CONF_HEALTH_SENSOR_DEVICE_CLASSES = "health_binary_sensor_device_classes"

CONF_RELOAD_ON_REGISTRY_CHANGE, DEFAULT_RELOAD_ON_REGISTRY_CHANGE = (
    "reload_on_registry_change",
    True,
)

CONF_IGNORE_DIAGNOSTIC_ENTITIES, DEFAULT_IGNORE_DIAGNOSTIC_ENTITIES = (
    "ignore_diagnostic_entities",
    True,
)

(CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT_META) = (
    "clear_timeout",
    1,
    0,
)

CONF_NOTIFICATION_DEVICES = "notification_devices"
DEFAULT_NOTIFICATION_DEVICES: list[str] = []

CONF_NOTIFY_STATES, DEFAULT_NOTIFY_STATES = (
    "notification_states",
    [AreaStates.EXTENDED],
)

CONF_DARK_ENTITY = "dark_entity"
CONF_ACCENT_ENTITY = "accent_entity"
CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT = (
    "sleep_timeout",
    DEFAULT_CLEAR_TIMEOUT,
)
CONF_SLEEP_ENTITY = "sleep_entity"
CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME = "extended_time", 5
CONF_EXTENDED_TIMEOUT, DEFAULT_EXTENDED_TIMEOUT = "extended_timeout", 10

CONF_BLE_TRACKER_ENTITIES = "ble_tracker_entities"
DEFAULT_BLE_TRACKER_ENTITIES: list[str] = []

CONF_WASP_IN_A_BOX_DELAY, DEFAULT_WASP_IN_A_BOX_DELAY = (
    "delay",
    90,
)
CONF_WASP_IN_A_BOX_WASP_TIMEOUT, DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT = (
    "wasp_timeout",
    0,
)
CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES = "wasp_device_classes"

CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT = (
    "presence_hold_timeout",
    0,
)

CONF_CLIMATE_CONTROL_ENTITY_ID, DEFAULT_CLIMATE_CONTROL_ENTITY_ID = ("entity_id", None)
CONF_CLIMATE_CONTROL_PRESET_CLEAR, DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR = (
    "preset_clear",
    EMPTY_STRING,
)
CONF_CLIMATE_CONTROL_PRESET_OCCUPIED, DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED = (
    "preset_occupied",
    EMPTY_STRING,
)
CONF_CLIMATE_CONTROL_PRESET_EXTENDED, DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED = (
    "preset_extended",
    EMPTY_STRING,
)
CONF_CLIMATE_CONTROL_PRESET_SLEEP, DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP = (
    "preset_sleep",
    EMPTY_STRING,
)

CONF_FAN_GROUPS_REQUIRED_STATE, DEFAULT_FAN_GROUPS_REQUIRED_STATE = (
    "required_state",
    AreaStates.EXTENDED,
)
CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS = "tracked_device_class"
CONF_FAN_GROUPS_SETPOINT, DEFAULT_FAN_GROUPS_SETPOINT = ("setpoint", 0.0)

CONF_SECONDARY_STATES_CALCULATION_MODE, DEFAULT_SECONDARY_STATES_CALCULATION_MODE = (
    "calculation_mode",
    CalculationMode.MAJORITY,
)
