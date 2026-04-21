"""Enumerations for Magic Areas integration."""

from enum import IntEnum, StrEnum, auto


class CalculationMode(StrEnum):
    """Calculation mode for aggregating area states."""

    ANY = auto()
    ALL = auto()
    MAJORITY = auto()


class LightGroupCategory(StrEnum):
    """Categories of light groups in an area."""

    ALL = "all_lights"
    OVERHEAD = "overhead_lights"
    TASK = "task_lights"
    ACCENT = "accent_lights"
    SLEEP = "sleep_lights"


class MagicConfigEntryVersion(IntEnum):
    """Config entry version numbers."""

    MAJOR = 2
    MINOR = 3


class MagicAreasFeatures(StrEnum):
    """Feature identifiers for Magic Areas integration."""

    AREA = "area"
    PRESENCE_TRACKING = "presence_tracking"
    PRESENCE_HOLD = "presence_hold"
    LIGHT_GROUPS = "light_groups"
    CLIMATE_CONTROL = "climate_control"
    COVER_GROUPS = "cover_groups"
    MEDIA_PLAYER_GROUPS = "media_player_groups"
    AREA_AWARE_MEDIA_PLAYER = "area_aware_media_player"
    AGGREGATES = "aggregates"
    HEALTH = "health"
    THRESHOLD = "threshold"
    FAN_GROUPS = "fan_groups"
    WASP_IN_A_BOX = "wasp_in_a_box"
    BLE_TRACKER = "ble_trackers"



class MagicAreasEvents(StrEnum):
    """Event identifiers dispatched by Magic Areas."""

    AREA_STATE_CHANGED = "magicareas_area_state_changed"
    AREA_SNAPSHOT_READY = "magicareas_area_snapshot_ready"


class SelectorTranslationKeys(StrEnum):
    """Translation keys for selector options."""

    CLIMATE_PRESET_LIST = auto()
    AREA_TYPE = auto()
    AREA_STATES = auto()
    CONTROL_ON = auto()
    CALCULATION_MODE = auto()
