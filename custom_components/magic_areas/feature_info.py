"""Feature metadata contract (ids, translation keys, icons)."""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN

from custom_components.magic_areas.enums import MagicAreasFeatures


@dataclass(frozen=True)
class FeatureInfo:
    """Feature metadata for entities."""

    id: MagicAreasFeatures
    translation_keys: dict[str, str | None]
    icons: dict[str, str] = field(default_factory=dict)


FEATURE_INFO_BY_FEATURE: dict[MagicAreasFeatures, FeatureInfo] = {
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER: FeatureInfo(
        id=MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
        translation_keys={MEDIA_PLAYER_DOMAIN: "area_aware_media_player"},
    ),
    MagicAreasFeatures.AGGREGATES: FeatureInfo(
        id=MagicAreasFeatures.AGGREGATES,
        translation_keys={
            BINARY_SENSOR_DOMAIN: "aggregate",
            SENSOR_DOMAIN: "aggregate",
        },
    ),
    MagicAreasFeatures.BLE_TRACKER: FeatureInfo(
        id=MagicAreasFeatures.BLE_TRACKER,
        translation_keys={BINARY_SENSOR_DOMAIN: "ble_tracker_monitor"},
        icons={BINARY_SENSOR_DOMAIN: "mdi:bluetooth"},
    ),
    MagicAreasFeatures.CLIMATE_CONTROL: FeatureInfo(
        id=MagicAreasFeatures.CLIMATE_CONTROL,
        translation_keys={SWITCH_DOMAIN: "climate_control"},
        icons={SWITCH_DOMAIN: "mdi:thermostat-auto"},
    ),
    MagicAreasFeatures.COVER_GROUPS: FeatureInfo(
        id=MagicAreasFeatures.COVER_GROUPS,
        translation_keys={
            COVER_DOMAIN: "cover_group",
            SWITCH_DOMAIN: "cover_control",
        },
        icons={SWITCH_DOMAIN: "mdi:blinds"},
    ),
    MagicAreasFeatures.FAN_GROUPS: FeatureInfo(
        id=MagicAreasFeatures.FAN_GROUPS,
        translation_keys={
            FAN_DOMAIN: "fan_group",
            SWITCH_DOMAIN: "fan_control",
        },
        icons={SWITCH_DOMAIN: "mdi:fan-auto"},
    ),
    MagicAreasFeatures.HEALTH: FeatureInfo(
        id=MagicAreasFeatures.HEALTH,
        translation_keys={BINARY_SENSOR_DOMAIN: "health"},
    ),
    MagicAreasFeatures.LIGHT_GROUPS: FeatureInfo(
        id=MagicAreasFeatures.LIGHT_GROUPS,
        translation_keys={
            LIGHT_DOMAIN: None,
            SWITCH_DOMAIN: "light_control",
        },
        icons={SWITCH_DOMAIN: "mdi:lightbulb-auto-outline"},
    ),
    MagicAreasFeatures.MEDIA_PLAYER_GROUPS: FeatureInfo(
        id=MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
        translation_keys={
            MEDIA_PLAYER_DOMAIN: "media_player_group",
            SWITCH_DOMAIN: "media_player_control",
        },
        icons={SWITCH_DOMAIN: "mdi:auto-mode"},
    ),
    MagicAreasFeatures.PRESENCE_HOLD: FeatureInfo(
        id=MagicAreasFeatures.PRESENCE_HOLD,
        translation_keys={SWITCH_DOMAIN: "presence_hold"},
        icons={SWITCH_DOMAIN: "mdi:car-brake-hold"},
    ),
    MagicAreasFeatures.WASP_IN_A_BOX: FeatureInfo(
        id=MagicAreasFeatures.WASP_IN_A_BOX,
        translation_keys={BINARY_SENSOR_DOMAIN: "wasp_in_a_box"},
        icons={BINARY_SENSOR_DOMAIN: "mdi:bee"},
    ),
    MagicAreasFeatures.PRESENCE_TRACKING: FeatureInfo(
        id=MagicAreasFeatures.PRESENCE_TRACKING,
        translation_keys={BINARY_SENSOR_DOMAIN: "area_state"},
        icons={BINARY_SENSOR_DOMAIN: "mdi:texture-box"},
    ),
    MagicAreasFeatures.THRESHOLD: FeatureInfo(
        id=MagicAreasFeatures.THRESHOLD,
        translation_keys={BINARY_SENSOR_DOMAIN: "threshold"},
    ),
}


def get_feature_info(feature: MagicAreasFeatures) -> FeatureInfo:
    """Return FeatureInfo metadata for a feature."""
    return FEATURE_INFO_BY_FEATURE[feature]
