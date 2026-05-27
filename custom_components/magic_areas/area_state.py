"""Area state and type enumerations."""

from enum import StrEnum


class AreaStates(StrEnum):
    """Possible states for an area."""

    CLEAR = "clear"
    OCCUPIED = "occupied"
    EXTENDED = "extended"
    DARK = "dark"
    BRIGHT = "bright"
    SLEEP = "sleep"
    ACCENT = "accented"
    HOT = "hot"
    HUMID = "humid"
    ODOR = "odor"


AREA_PRIORITY_STATES = [AreaStates.SLEEP, AreaStates.ACCENT]
BUILTIN_AREA_STATES = [AreaStates.OCCUPIED, AreaStates.EXTENDED]
CONFIGURABLE_AREA_STATES = [AreaStates.DARK, AreaStates.ACCENT, AreaStates.SLEEP]


class AreaType(StrEnum):
    """Types of areas supported by Magic Areas."""

    INTERIOR = "interior"
    EXTERIOR = "exterior"
    META = "meta"


AREA_TYPES = [AreaType.INTERIOR, AreaType.EXTERIOR, AreaType.META]


class MetaAreaType(StrEnum):
    """Types of meta-areas for grouping child areas."""

    GLOBAL = "global"
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    FLOOR = "floor"


META_AREA_GLOBAL = "Global"
META_AREA_INTERIOR = "Interior"
META_AREA_EXTERIOR = "Exterior"
META_AREAS = [META_AREA_GLOBAL, META_AREA_INTERIOR, META_AREA_EXTERIOR]
