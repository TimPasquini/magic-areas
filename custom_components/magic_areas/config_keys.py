"""Configuration keys organized by domain.

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

Note: This module contains configuration *keys* only. Defaults and tuning values
live in defaults.py. Complex schema validation is in schemas/features.py.
"""

from __future__ import annotations

CONF_ID = "id"
CONF_NAME = "name"
CONF_TYPE = "type"

CONF_ENABLED_FEATURES = "features"

CONF_SECONDARY_STATES = "secondary_states"

CONF_INCLUDE_ENTITIES = "include_entities"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_KEEP_ONLY_ENTITIES = "keep_only_entities"

CONF_PRESENCE_DEVICE_PLATFORMS = "presence_device_platforms"

CONF_PRESENCE_SENSOR_DEVICE_CLASS = "presence_sensor_device_class"

CONF_AGGREGATES_MIN_ENTITIES = "aggregates_min_entities"
CONF_AGGREGATES_SENSOR_DEVICE_CLASSES = "aggregates_sensor_device_classes"
CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES = "aggregates_binary_sensor_device_classes"

CONF_AGGREGATES_ILLUMINANCE_THRESHOLD = "aggregates_illuminance_threshold"
CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS = (
    "aggregates_illuminance_threshold_hysteresis"
)

CONF_HEALTH_SENSOR_DEVICE_CLASSES = "health_binary_sensor_device_classes"

CONF_RELOAD_ON_REGISTRY_CHANGE = "reload_on_registry_change"

CONF_IGNORE_DIAGNOSTIC_ENTITIES = "ignore_diagnostic_entities"

CONF_CLEAR_TIMEOUT = "clear_timeout"

CONF_NOTIFICATION_DEVICES = "notification_devices"

CONF_NOTIFY_STATES = "notification_states"

CONF_DARK_ENTITY = "dark_entity"
CONF_ACCENT_ENTITY = "accent_entity"
CONF_SLEEP_TIMEOUT = "sleep_timeout"
CONF_SLEEP_ENTITY = "sleep_entity"
CONF_EXTENDED_TIME = "extended_time"
CONF_EXTENDED_TIMEOUT = "extended_timeout"

CONF_BLE_TRACKER_ENTITIES = "ble_tracker_entities"

CONF_WASP_IN_A_BOX_DELAY = "delay"
CONF_WASP_IN_A_BOX_WASP_TIMEOUT = "wasp_timeout"
CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES = "wasp_device_classes"

CONF_PRESENCE_HOLD_TIMEOUT = "presence_hold_timeout"

CONF_CLIMATE_CONTROL_ENTITY_ID = "entity_id"
CONF_CLIMATE_CONTROL_PRESET_CLEAR = "preset_clear"
CONF_CLIMATE_CONTROL_PRESET_OCCUPIED = "preset_occupied"
CONF_CLIMATE_CONTROL_PRESET_EXTENDED = "preset_extended"
CONF_CLIMATE_CONTROL_PRESET_SLEEP = "preset_sleep"

CONF_FAN_GROUPS_REQUIRED_STATE = "required_state"
CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS = "tracked_device_class"
CONF_FAN_GROUPS_SETPOINT = "setpoint"

CONF_SECONDARY_STATES_CALCULATION_MODE = "calculation_mode"

EMPTY_STRING = ""
