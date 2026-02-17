"""Icon definitions for Magic Areas."""

from enum import StrEnum


class MetaAreaIcons(StrEnum):
    """Icons for different meta area types."""

    INTERIOR = "mdi:home-import-outline"
    EXTERIOR = "mdi:home-export-outline"
    GLOBAL = "mdi:home"


class FeatureIcons(StrEnum):
    """Icons for feature control switches."""

    PRESENCE_HOLD_SWITCH = "mdi:car-brake-hold"
    LIGHT_CONTROL_SWITCH = "mdi:lightbulb-auto-outline"
    MEDIA_CONTROL_SWITCH = "mdi:auto-mode"
    CLIMATE_CONTROL_SWITCH = "mdi:thermostat-auto"
