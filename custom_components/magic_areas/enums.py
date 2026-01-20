from enum import IntEnum, StrEnum, auto


class MetaAreaAutoReloadSettings(IntEnum):
    DELAY = 3
    DELAY_MULTIPLIER = 4
    THROTTLE = 5


class CalculationMode(StrEnum):
    ANY = auto()
    ALL = auto()
    MAJORITY = auto()


class LightGroupCategory(StrEnum):
    ALL = "all_lights"
    OVERHEAD = "overhead_lights"
    TASK = "task_lights"
    ACCENT = "accent_lights"
    SLEEP = "sleep_lights"


class MagicConfigEntryVersion(IntEnum):
    MAJOR = 2
    MINOR = 1


class MagicAreasFeatures(StrEnum):
    AREA = "area"
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
    AREA_STATE_CHANGED = "magicareas_area_state_changed"
    AREA_LOADED = "magicareas_area_loaded"


class SelectorTranslationKeys(StrEnum):
    CLIMATE_PRESET_LIST = auto()
    AREA_TYPE = auto()
    AREA_STATES = auto()
    CONTROL_ON = auto()
    CALCULATION_MODE = auto()


class MetaAreaIcons(StrEnum):
    INTERIOR = "mdi:home-import-outline"
    EXTERIOR = "mdi:home-export-outline"
    GLOBAL = "mdi:home"


class FeatureIcons(StrEnum):
    PRESENCE_HOLD_SWITCH = "mdi:car-brake-hold"
    LIGHT_CONTROL_SWITCH = "mdi:lightbulb-auto-outline"
    MEDIA_CONTROL_SWITCH = "mdi:auto-mode"
    CLIMATE_CONTROL_SWITCH = "mdi:thermostat-auto"


class AreaStates(StrEnum):
    CLEAR = "clear"
    OCCUPIED = "occupied"
    EXTENDED = "extended"
    DARK = "dark"
    BRIGHT = "bright"
    SLEEP = "sleep"
    ACCENT = "accented"


class AreaType(StrEnum):
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    META = "meta"


class MetaAreaType(StrEnum):
    GLOBAL = "global"
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    FLOOR = "floor"
