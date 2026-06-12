"""Component/domain groupings and ID prefixes."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.device_tracker.const import (
    DOMAIN as DEVICE_TRACKER_DOMAIN,
)
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.features.dispatch import RuntimeController

# Re-export HA domains for runtime modules/tests.
__all__ = [
    "BINARY_SENSOR_DOMAIN",
    "COVER_DOMAIN",
    "DEVICE_TRACKER_DOMAIN",
    "FAN_DOMAIN",
    "LIGHT_DOMAIN",
    "MEDIA_PLAYER_DOMAIN",
    "REMOTE_DOMAIN",
    "SENSOR_DOMAIN",
    "SWITCH_DOMAIN",
]

__all__ += [
    "MagicAreasConfigEntry",
    "MAGIC_AREAS_COMPONENTS",
    "MAGIC_AREAS_COMPONENTS_META",
    "MAGIC_AREAS_COMPONENTS_GLOBAL",
    "MAGICAREAS_UNIQUEID_PREFIX",
    "MAGIC_DEVICE_ID_PREFIX",
    "MagicAreasRuntimeData",
    "MetaAreaIcons",
]

MAGIC_AREAS_COMPONENTS = [
    BINARY_SENSOR_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    COVER_DOMAIN,
    SENSOR_DOMAIN,
    LIGHT_DOMAIN,
    FAN_DOMAIN,
    SWITCH_DOMAIN,
]

MAGIC_AREAS_COMPONENTS_META = [
    BINARY_SENSOR_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    COVER_DOMAIN,
    SENSOR_DOMAIN,
    LIGHT_DOMAIN,
    SWITCH_DOMAIN,
]

MAGIC_AREAS_COMPONENTS_GLOBAL = MAGIC_AREAS_COMPONENTS_META

MAGICAREAS_UNIQUEID_PREFIX = "magic_areas"
MAGIC_DEVICE_ID_PREFIX = "magic_area_device_"


class MetaAreaIcons(StrEnum):
    """Icons for different meta area types."""

    INTERIOR = "mdi:home-import-outline"
    EXTERIOR = "mdi:home-export-outline"
    GLOBAL = "mdi:home"


@dataclass
class MagicAreasRuntimeData:
    """Class to hold magic areas runtime data."""

    coordinator: "MagicAreasCoordinator"
    listeners: list[Callable[[], None]]
    runtime_controllers: list["RuntimeController"] | None = None


type MagicAreasConfigEntry = ConfigEntry[MagicAreasRuntimeData]
