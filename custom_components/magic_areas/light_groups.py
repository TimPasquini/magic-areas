"""Light group configuration constants and tables.

Extracted from const.py.
"""
from custom_components.magic_areas.enums import StrEnum, auto

# Light group options
CONF_OVERHEAD_LIGHTS = "overhead_lights"  # cv.entity_ids
CONF_OVERHEAD_LIGHTS_STATES = "overhead_lights_states"  # cv.ensure_list
CONF_OVERHEAD_LIGHTS_ACT_ON = "overhead_lights_act_on"  # cv.ensure_list
CONF_SLEEP_LIGHTS = "sleep_lights"
CONF_SLEEP_LIGHTS_STATES = "sleep_lights_states"
CONF_SLEEP_LIGHTS_ACT_ON = "sleep_lights_act_on"
CONF_ACCENT_LIGHTS = "accent_lights"
CONF_ACCENT_LIGHTS_STATES = "accent_lights_states"
CONF_ACCENT_LIGHTS_ACT_ON = "accent_lights_act_on"
CONF_TASK_LIGHTS = "task_lights"
CONF_TASK_LIGHTS_STATES = "task_lights_states"
CONF_TASK_LIGHTS_ACT_ON = "task_lights_act_on"

LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE = "occupancy"
LIGHT_GROUP_ACT_ON_STATE_CHANGE = "state"
DEFAULT_LIGHT_GROUP_ACT_ON = [
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
]
LIGHT_GROUP_ACT_ON_OPTIONS = [
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
]

LIGHT_GROUP_DEFAULT_ICON = "mdi:lightbulb-group"

LIGHT_GROUP_ICONS = {
    CONF_OVERHEAD_LIGHTS: "mdi:ceiling-light",
    CONF_SLEEP_LIGHTS: "mdi:sleep",
    CONF_ACCENT_LIGHTS: "mdi:outdoor-lamp",
    CONF_TASK_LIGHTS: "mdi:desk-lamp",
}

LIGHT_GROUP_STATES = {
    CONF_OVERHEAD_LIGHTS: CONF_OVERHEAD_LIGHTS_STATES,
    CONF_SLEEP_LIGHTS: CONF_SLEEP_LIGHTS_STATES,
    CONF_ACCENT_LIGHTS: CONF_ACCENT_LIGHTS_STATES,
    CONF_TASK_LIGHTS: CONF_TASK_LIGHTS_STATES,
}

LIGHT_GROUP_ACT_ON = {
    CONF_OVERHEAD_LIGHTS: CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_SLEEP_LIGHTS: CONF_SLEEP_LIGHTS_ACT_ON,
    CONF_ACCENT_LIGHTS: CONF_ACCENT_LIGHTS_ACT_ON,
    CONF_TASK_LIGHTS: CONF_TASK_LIGHTS_ACT_ON,
}


class CalculationMode(StrEnum):
    """Modes for calculating values."""

    ANY = auto()
    ALL = auto()
    MAJORITY = auto()


class LightGroupCategory(StrEnum):
    """Categories of light groups."""

    ALL = "all_lights"
    OVERHEAD = "overhead_lights"
    TASK = "task_lights"
    ACCENT = "accent_lights"
    SLEEP = "sleep_lights"


LIGHT_GROUP_CATEGORIES = [
    CONF_OVERHEAD_LIGHTS,
    CONF_SLEEP_LIGHTS,
    CONF_ACCENT_LIGHTS,
    CONF_TASK_LIGHTS,
]
