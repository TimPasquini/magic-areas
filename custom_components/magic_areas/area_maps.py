"""Derived maps tying area-state strings to config keys."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys import (
    CONF_ACCENT_ENTITY,
    CONF_DARK_ENTITY,
    CONF_SLEEP_ENTITY,
)

CONFIGURABLE_AREA_STATE_MAP = {
    AreaStates.SLEEP: CONF_SLEEP_ENTITY,
    AreaStates.DARK: CONF_DARK_ENTITY,
    AreaStates.ACCENT: CONF_ACCENT_ENTITY,
}
