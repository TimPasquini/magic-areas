"""Feature metadata (ids, translation keys, icons)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN


class MagicAreasFeatureInfo:
    """Base class for feature information."""

    id: str
    translation_keys: dict[str, str | None]
    icons: dict[str, str] = {}


class MagicAreasFeatureInfoPresenceTracking(MagicAreasFeatureInfo):
    """Feature metadata for presence tracking."""

    id = "presence_tracking"
    translation_keys = {BINARY_SENSOR_DOMAIN: "area_state"}
    icons = {BINARY_SENSOR_DOMAIN: "mdi:texture-box"}


class MagicAreasFeatureInfoPresenceHold(MagicAreasFeatureInfo):
    """Feature metadata for presence hold."""

    id = "presence_hold"
    translation_keys = {SWITCH_DOMAIN: "presence_hold"}
    icons = {SWITCH_DOMAIN: "mdi:car-brake-hold"}


class MagicAreasFeatureInfoBLETrackers(MagicAreasFeatureInfo):
    """Feature metadata for BLE trackers."""

    id = "ble_trackers"
    translation_keys = {BINARY_SENSOR_DOMAIN: "ble_tracker_monitor"}
    icons = {BINARY_SENSOR_DOMAIN: "mdi:bluetooth"}


class MagicAreasFeatureInfoWaspInABox(MagicAreasFeatureInfo):
    """Feature metadata for Wasp in a Box."""

    id = "wasp_in_a_box"
    translation_keys = {BINARY_SENSOR_DOMAIN: "wasp_in_a_box"}
    icons = {BINARY_SENSOR_DOMAIN: "mdi:bee"}


class MagicAreasFeatureInfoAggregates(MagicAreasFeatureInfo):
    """Feature metadata for aggregates."""

    id = "aggregates"
    translation_keys = {
        BINARY_SENSOR_DOMAIN: "aggregate",
        SENSOR_DOMAIN: "aggregate",
    }


class MagicAreasFeatureInfoThreshold(MagicAreasFeatureInfo):
    """Feature metadata for threshold."""

    id = "threshold"
    translation_keys = {BINARY_SENSOR_DOMAIN: "threshold"}


class MagicAreasFeatureInfoHealth(MagicAreasFeatureInfo):
    """Feature metadata for health monitoring."""

    id = "health"
    translation_keys = {BINARY_SENSOR_DOMAIN: "health"}


class MagicAreasFeatureInfoLightGroups(MagicAreasFeatureInfo):
    """Feature metadata for light groups."""

    id = "light_groups"
    translation_keys = {
        LIGHT_DOMAIN: None,  # let light category be appended to it
        SWITCH_DOMAIN: "light_control",
    }
    icons = {SWITCH_DOMAIN: "mdi:lightbulb-auto-outline"}


class MagicAreasFeatureInfoClimateControl(MagicAreasFeatureInfo):
    """Feature metadata for climate control."""

    id = "climate_control"
    translation_keys = {SWITCH_DOMAIN: "climate_control"}
    icons = {SWITCH_DOMAIN: "mdi:thermostat-auto"}


class MagicAreasFeatureInfoFanGroups(MagicAreasFeatureInfo):
    """Feature metadata for fan groups."""

    id = "fan_groups"
    translation_keys = {
        FAN_DOMAIN: "fan_group",
        SWITCH_DOMAIN: "fan_control",
    }
    icons = {SWITCH_DOMAIN: "mdi:fan-auto"}


class MagicAreasFeatureInfoMediaPlayerGroups(MagicAreasFeatureInfo):
    """Feature metadata for media player groups."""

    id = "media_player_groups"
    translation_keys = {
        MEDIA_PLAYER_DOMAIN: "media_player_group",
        SWITCH_DOMAIN: "media_player_control",
    }
    icons = {SWITCH_DOMAIN: "mdi:auto-mode"}


class MagicAreasFeatureInfoCoverGroups(MagicAreasFeatureInfo):
    """Feature metadata for cover groups."""

    id = "cover_groups"
    translation_keys = {COVER_DOMAIN: "cover_group"}


class MagicAreasFeatureInfoAreaAwareMediaPlayer(MagicAreasFeatureInfo):
    """Feature metadata for area-aware media player."""

    id = "area_aware_media_player"
    translation_keys = {MEDIA_PLAYER_DOMAIN: "area_aware_media_player"}
