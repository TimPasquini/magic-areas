"""Local facade for feature-registry access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.feature_info import FeatureInfo

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.features.base import FeatureModule
    from custom_components.magic_areas.features.registry import FeatureRegistry


def _runtime_registry() -> FeatureRegistry:
    """Resolve runtime registry lazily to avoid import cycles."""
    from custom_components.magic_areas.features.registry import FEATURE_REGISTRY

    return FEATURE_REGISTRY


class _FeatureRegistryProxy:
    """Lazy proxy for the runtime feature registry."""

    def modules(self) -> list[FeatureModule]:
        """Return all registered feature modules."""
        return _runtime_registry().modules()

    def all_features(self) -> list[MagicAreasFeatures]:
        """Return feature ids in registry order."""
        return _runtime_registry().all_features()

    def available_features_for_area(
        self, area_config: object | None
    ) -> list[MagicAreasFeatures]:
        """Return features supported for the area type."""
        return _runtime_registry().available_features_for_area(area_config)

    def configurable_features_for_area(
        self, area_config: object | None
    ) -> list[MagicAreasFeatures]:
        """Return configurable features supported for the area type."""
        return _runtime_registry().configurable_features_for_area(area_config)

    def feature_info_for(self, feature: MagicAreasFeatures) -> FeatureInfo:
        """Return metadata for one feature."""
        return _runtime_registry().feature_info_for(feature)


RUNTIME_FEATURE_REGISTRY = _FeatureRegistryProxy()


def get_feature_info(feature: MagicAreasFeatures) -> FeatureInfo:
    """Return metadata for a runtime feature."""
    return _runtime_registry().feature_info_for(feature)


__all__ = ["RUNTIME_FEATURE_REGISTRY", "get_feature_info"]
