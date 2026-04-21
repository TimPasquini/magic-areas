"""Area-level configuration keys."""

from custom_components.magic_areas.area_state import AreaStates

CONF_ID = "id"
CONF_NAME = "name"
CONF_TYPE = "type"

CONF_ENABLED_FEATURES = "features"
CONF_CUSTOM_CONTROL_GROUPS = "custom_control_groups"
CONF_SECONDARY_STATES = "secondary_states"

# Entity selection keys
CONF_INCLUDE_ENTITIES = "include_entities"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_KEEP_ONLY_ENTITIES = "keep_only_entities"

# System-level area options
CONF_RELOAD_ON_REGISTRY_CHANGE = "reload_on_registry_change"
CONF_IGNORE_DIAGNOSTIC_ENTITIES = "ignore_diagnostic_entities"

# Presence/secondary-state keys
CONF_PRESENCE_DEVICE_PLATFORMS = "presence_device_platforms"
CONF_PRESENCE_SENSOR_DEVICE_CLASS = "presence_sensor_device_class"
CONF_CLEAR_TIMEOUT = "clear_timeout"
CONF_DARK_ENTITY = "dark_entity"
CONF_ACCENT_ENTITY = "accent_entity"
CONF_SLEEP_TIMEOUT = "sleep_timeout"
CONF_SLEEP_ENTITY = "sleep_entity"
CONF_EXTENDED_TIME = "extended_time"
CONF_EXTENDED_TIMEOUT = "extended_timeout"
CONF_SECONDARY_STATES_CALCULATION_MODE = "calculation_mode"

# Feature-level keys
CONF_AGGREGATES_MIN_ENTITIES = "aggregates_min_entities"
CONF_AGGREGATES_SENSOR_DEVICE_CLASSES = "aggregates_sensor_device_classes"
CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES = "aggregates_binary_sensor_device_classes"
CONF_AGGREGATES_ILLUMINANCE_THRESHOLD = "aggregates_illuminance_threshold"
CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS = (
    "aggregates_illuminance_threshold_hysteresis"
)
CONF_HEALTH_SENSOR_DEVICE_CLASSES = "health_binary_sensor_device_classes"

CONF_BLE_TRACKER_ENTITIES = "ble_tracker_entities"

CONF_NOTIFICATION_DEVICES = "notification_devices"
CONF_NOTIFY_STATES = "notification_states"

CONF_PRESENCE_HOLD_TIMEOUT = "presence_hold_timeout"

CONF_WASP_IN_A_BOX_DELAY = "delay"
CONF_WASP_IN_A_BOX_WASP_TIMEOUT = "wasp_timeout"
CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES = "wasp_device_classes"

CONF_FAN_GROUPS_REQUIRED_STATE = "required_state"
CONF_FAN_GROUPS_TRACKED_DEVICE_CLASS = "tracked_device_class"
CONF_FAN_GROUPS_SETPOINT = "setpoint"
CONF_LIGHT_GROUP_BRIGHTNESS_MODE = "brightness_mode"
CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS = "bright_min_on_seconds"
CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS = "bright_dwell_seconds"
CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE = "outside_context_source"
CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY = "outside_lux_entity"
CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN = "outside_lux_min"
CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY = "outside_lux_inside_entity"
CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA = "outside_lux_inside_delta"
CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_RATIO_MIN_PERCENT = (
    "outside_lux_inside_ratio_min_percent"
)
CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS = "bright_attribution_hold_seconds"
CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE = "adaptive_require_ambient_rise"
CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS = "ambient_rise_window_seconds"
CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA = "ambient_rise_min_delta"

CONF_CLIMATE_CONTROL_ENTITY_ID = "entity_id"
CONF_CLIMATE_CONTROL_PRESET_CLEAR = "preset_clear"
CONF_CLIMATE_CONTROL_PRESET_OCCUPIED = "preset_occupied"
CONF_CLIMATE_CONTROL_PRESET_EXTENDED = "preset_extended"
CONF_CLIMATE_CONTROL_PRESET_SLEEP = "preset_sleep"
CLIMATE_CONTROL_PRESET_KEYS = (
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
    CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
)
CLIMATE_CONTROL_PRESET_KEY_BY_STATE = {
    str(AreaStates.CLEAR): CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    str(AreaStates.OCCUPIED): CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    str(AreaStates.SLEEP): CONF_CLIMATE_CONTROL_PRESET_SLEEP,
    str(AreaStates.EXTENDED): CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
}

# Secondary-state config-key mapping
CONFIGURABLE_AREA_STATE_MAP = {
    AreaStates.SLEEP: CONF_SLEEP_ENTITY,
    AreaStates.DARK: CONF_DARK_ENTITY,
    AreaStates.ACCENT: CONF_ACCENT_ENTITY,
}
