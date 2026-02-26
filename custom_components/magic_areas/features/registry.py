"""Feature module registry for Magic Areas."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.feature_info import (
    FEATURE_INFO_REGISTRY,
    FeatureInfo,
)
from custom_components.magic_areas.features.base import FeatureModule
from custom_components.magic_areas.features.modules.aggregates import (
    AggregatesFeatureModule,
)
from custom_components.magic_areas.features.modules.area_aware_media_player import (
    AreaAwareMediaPlayerFeatureModule,
)
from custom_components.magic_areas.features.modules.ble_trackers import (
    BLETrackersFeatureModule,
)
from custom_components.magic_areas.features.modules.climate_control import (
    ClimateControlFeatureModule,
)
from custom_components.magic_areas.features.modules.cover_groups import (
    CoverGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.fan_groups import (
    FanGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.health import (
    HealthFeatureModule,
)
from custom_components.magic_areas.features.modules.light_groups import (
    LightGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.media_player_groups import (
    MediaPlayerGroupsFeatureModule,
)
from custom_components.magic_areas.features.modules.presence_hold import (
    PresenceHoldFeatureModule,
)
from custom_components.magic_areas.features.modules.wasp_in_a_box import (
    WaspInABoxFeatureModule,
)

_LOGGER = logging.getLogger(__name__)


class FeatureRegistry:
    """Registry for FeatureModule instances."""

    def __init__(self, modules: Iterable[FeatureModule]) -> None:
        """Initialize the registry with feature modules."""
        self._modules: list[FeatureModule] = list(modules)
        self._by_feature: dict[MagicAreasFeatures, FeatureModule] = {
            module.id: module for module in self._modules
        }
        self._feature_info: dict[MagicAreasFeatures, FeatureInfo] = dict(
            FEATURE_INFO_REGISTRY
        )

    def modules(self) -> list[FeatureModule]:
        """Return all registered modules."""
        return list(self._modules)

    def module_for_feature(
        self, feature: MagicAreasFeatures
    ) -> FeatureModule | None:
        """Return the module for a specific feature."""
        return self._by_feature.get(feature)

    def feature_info_for(self, feature: MagicAreasFeatures) -> FeatureInfo:
        """Return FeatureInfo metadata for a specific feature."""
        return self._feature_info[feature]

    def modules_for_domain(self, domain: str) -> list[FeatureModule]:
        """Return modules that contribute entities to the domain."""
        return [module for module in self._modules if domain in module.domains]

    def enabled_modules(self, data: object) -> list[FeatureModule]:
        """Return modules enabled for the area snapshot."""
        enabled: list[FeatureModule] = []
        for module in self._modules:
            if module.is_enabled(data):  # type: ignore[arg-type]
                enabled.append(module)
        return enabled

    def validate_dependencies(self, data: object) -> None:
        """Log missing feature dependencies for enabled modules."""
        enabled = {module.id for module in self.enabled_modules(data)}
        for module in self._modules:
            if module.id not in enabled:
                continue
            missing = module.depends_on() - enabled
            if missing:
                _LOGGER.warning(
                    "Feature %s missing dependencies: %s",
                    module.id,
                    ", ".join(sorted(f.value for f in missing)),
                )


FEATURE_REGISTRY = FeatureRegistry(
    modules=[
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
    ]
)
