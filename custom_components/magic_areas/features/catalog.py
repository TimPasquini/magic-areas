"""Canonical feature registration catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.feature_info import FeatureInfo
from custom_components.magic_areas.features.modules import AggregatesFeatureModule
from custom_components.magic_areas.features.modules import (
    AreaAwareMediaPlayerFeatureModule,
)
from custom_components.magic_areas.features.modules import BLETrackersFeatureModule
from custom_components.magic_areas.features.modules import ClimateControlFeatureModule
from custom_components.magic_areas.features.modules import CoverGroupsFeatureModule
from custom_components.magic_areas.features.modules import FanGroupsFeatureModule
from custom_components.magic_areas.features.modules import HealthFeatureModule
from custom_components.magic_areas.features.modules import LightGroupsFeatureModule
from custom_components.magic_areas.features.modules import (
    MediaPlayerGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules import PresenceHoldFeatureModule
from custom_components.magic_areas.features.modules import WaspInABoxFeatureModule

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.features.base import FeatureModule


@dataclass(frozen=True)
class FeatureRegistration:
    """Canonical registration record for one feature."""

    module: FeatureModule
    info: FeatureInfo


FEATURE_REGISTRATIONS: tuple[FeatureRegistration, ...] = (
    FeatureRegistration(
        module=AreaAwareMediaPlayerFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
            translation_keys={MEDIA_PLAYER_DOMAIN: "area_aware_media_player"},
        ),
    ),
    FeatureRegistration(
        module=AggregatesFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.AGGREGATES,
            translation_keys={
                BINARY_SENSOR_DOMAIN: "aggregate",
                SENSOR_DOMAIN: "aggregate",
            },
        ),
    ),
    FeatureRegistration(
        module=BLETrackersFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.BLE_TRACKER,
            translation_keys={BINARY_SENSOR_DOMAIN: "ble_tracker_monitor"},
            icons={BINARY_SENSOR_DOMAIN: "mdi:bluetooth"},
        ),
    ),
    FeatureRegistration(
        module=ClimateControlFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.CLIMATE_CONTROL,
            translation_keys={SWITCH_DOMAIN: "climate_control"},
            icons={SWITCH_DOMAIN: "mdi:thermostat-auto"},
        ),
    ),
    FeatureRegistration(
        module=CoverGroupsFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.COVER_GROUPS,
            translation_keys={COVER_DOMAIN: "cover_group"},
        ),
    ),
    FeatureRegistration(
        module=FanGroupsFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.FAN_GROUPS,
            translation_keys={
                FAN_DOMAIN: "fan_group",
                SWITCH_DOMAIN: "fan_control",
            },
            icons={SWITCH_DOMAIN: "mdi:fan-auto"},
        ),
    ),
    FeatureRegistration(
        module=HealthFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.HEALTH,
            translation_keys={BINARY_SENSOR_DOMAIN: "health"},
        ),
    ),
    FeatureRegistration(
        module=LightGroupsFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.LIGHT_GROUPS,
            translation_keys={
                LIGHT_DOMAIN: None,
                SWITCH_DOMAIN: "light_control",
            },
            icons={SWITCH_DOMAIN: "mdi:lightbulb-auto-outline"},
        ),
    ),
    FeatureRegistration(
        module=MediaPlayerGroupsFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
            translation_keys={
                MEDIA_PLAYER_DOMAIN: "media_player_group",
                SWITCH_DOMAIN: "media_player_control",
            },
            icons={SWITCH_DOMAIN: "mdi:auto-mode"},
        ),
    ),
    FeatureRegistration(
        module=PresenceHoldFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.PRESENCE_HOLD,
            translation_keys={SWITCH_DOMAIN: "presence_hold"},
            icons={SWITCH_DOMAIN: "mdi:car-brake-hold"},
        ),
    ),
    FeatureRegistration(
        module=WaspInABoxFeatureModule(),
        info=FeatureInfo(
            id=MagicAreasFeatures.WASP_IN_A_BOX,
            translation_keys={BINARY_SENSOR_DOMAIN: "wasp_in_a_box"},
            icons={BINARY_SENSOR_DOMAIN: "mdi:bee"},
        ),
    ),
)

FEATURE_INFO_ONLY: tuple[FeatureInfo, ...] = (
    FeatureInfo(
        id=MagicAreasFeatures.PRESENCE_TRACKING,
        translation_keys={BINARY_SENSOR_DOMAIN: "area_state"},
        icons={BINARY_SENSOR_DOMAIN: "mdi:texture-box"},
    ),
    FeatureInfo(
        id=MagicAreasFeatures.THRESHOLD,
        translation_keys={BINARY_SENSOR_DOMAIN: "threshold"},
    ),
)

for _registration in FEATURE_REGISTRATIONS:
    if _registration.module.id != _registration.info.id:
        raise ValueError(
            "Feature registration mismatch: module id "
            f"{_registration.module.id} != info id {_registration.info.id}"
        )

DEFAULT_FEATURE_MODULES: tuple[FeatureModule, ...] = tuple(
    registration.module for registration in FEATURE_REGISTRATIONS
)

FEATURE_INFO_BY_FEATURE: dict[MagicAreasFeatures, FeatureInfo] = {
    registration.info.id: registration.info for registration in FEATURE_REGISTRATIONS
}
for _info in FEATURE_INFO_ONLY:
    if _info.id in FEATURE_INFO_BY_FEATURE:
        raise ValueError(f"Duplicate feature info entry for {_info.id}")
    FEATURE_INFO_BY_FEATURE[_info.id] = _info

