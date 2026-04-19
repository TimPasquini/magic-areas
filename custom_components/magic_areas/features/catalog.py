"""Canonical feature module catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from custom_components.magic_areas.feature_info import FeatureInfo
from custom_components.magic_areas.feature_info import FEATURE_INFO_BY_FEATURE
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
    """Canonical registration record for one feature module."""

    module: FeatureModule
    info: FeatureInfo


DEFAULT_FEATURE_MODULES: tuple[FeatureModule, ...] = (
    AreaAwareMediaPlayerFeatureModule(),
    AggregatesFeatureModule(),
    BLETrackersFeatureModule(),
    ClimateControlFeatureModule(),
    CoverGroupsFeatureModule(),
    FanGroupsFeatureModule(),
    HealthFeatureModule(),
    LightGroupsFeatureModule(),
    MediaPlayerGroupsFeatureModule(),
    PresenceHoldFeatureModule(),
    WaspInABoxFeatureModule(),
)

for _module in DEFAULT_FEATURE_MODULES:
    if _module.id not in FEATURE_INFO_BY_FEATURE:
        raise ValueError(f"Missing feature info entry for {_module.id}")

FEATURE_REGISTRATIONS: tuple[FeatureRegistration, ...] = tuple(
    FeatureRegistration(
        module=module,
        info=FEATURE_INFO_BY_FEATURE[module.id],
    )
    for module in DEFAULT_FEATURE_MODULES
)

__all__ = [
    "DEFAULT_FEATURE_MODULES",
    "FEATURE_REGISTRATIONS",
    "FeatureRegistration",
]
