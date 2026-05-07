"""Core primitive constants for Magic Areas (no HA imports)."""

ONE_MINUTE = 60  # seconds, for conversion

DOMAIN = "magic_areas"

# Private config-entry data used by managed-surface reconciliation.
MANAGED_LABEL_SURFACES_DATA_KEY = "managed_label_surfaces"

# Common entity attributes
ATTR_STATES = "states"
ATTR_AREAS = "areas"
ATTR_ACTIVE_AREAS = "active_areas"
ATTR_TYPE = "type"
ATTR_CLEAR_TIMEOUT = "clear_timeout"
ATTR_ACTIVE_SENSORS = "active_sensors"
ATTR_LAST_ACTIVE_SENSORS = "last_active_sensors"
ATTR_FEATURES = "features"
ATTR_PRESENCE_SENSORS = "presence_sensors"
