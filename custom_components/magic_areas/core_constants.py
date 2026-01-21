"""Core primitive constants for Magic Areas (no HA imports)."""

ONE_MINUTE = 60  # seconds, for conversion
EMPTY_STRING = ""

DOMAIN = "magic_areas"

ADDITIONAL_LIGHT_TRACKING_ENTITIES = ["sun.sun"]
DEFAULT_SENSOR_PRECISION = 2
UPDATE_INTERVAL = ONE_MINUTE

EVENT_MAGICAREAS_AREA_STATE_CHANGED = "magicareas_area_state_changed"
