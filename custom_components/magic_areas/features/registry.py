"""Feature module registry for Magic Areas."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from custom_components.magic_areas.area_state import AreaType, META_AREA_GLOBAL
from custom_components.magic_areas.core.config import area_type
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.feature_info import FeatureInfo
from custom_components.magic_areas.feature_info import FEATURE_INFO_BY_FEATURE
from custom_components.magic_areas.features.base import FeatureModule
from custom_components.magic_areas.features.catalog import DEFAULT_FEATURE_MODULES

_LOGGER = logging.getLogger(__name__)
_EXPECTED_META_DETECTION_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


class FeatureRegistry:
    """Registry for FeatureModule instances."""

    def __init__(self, modules: Iterable[FeatureModule]) -> None:
        """Initialize the registry with feature modules."""
        self._modules: list[FeatureModule] = list(modules)
        self._by_feature: dict[MagicAreasFeatures, FeatureModule] = {
            module.id: module for module in self._modules
        }
        self._feature_info: dict[MagicAreasFeatures, FeatureInfo] = dict(FEATURE_INFO_BY_FEATURE)

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

    @staticmethod
    def _is_meta_area(area_config: object | None) -> bool:
        """Return whether area config should be treated as meta."""
        if area_config is None:
            return False

        config = getattr(area_config, "config", None)
        if isinstance(config, dict) and area_type(config) == str(AreaType.META):
            return True

        is_meta = getattr(area_config, "is_meta", None)
        if callable(is_meta):
            try:
                result = is_meta()
                return result if isinstance(result, bool) else False
            except _EXPECTED_META_DETECTION_ERRORS:  # pragma: no cover
                return False
        return False

    def all_features(self) -> list[MagicAreasFeatures]:
        """Return all feature IDs in registry order."""
        return [module.id for module in self._modules]

    def available_features_for_area(
        self, area_config: object | None
    ) -> list[MagicAreasFeatures]:
        """Return features supported for the area type."""
        is_meta = self._is_meta_area(area_config)
        area_id = getattr(area_config, "id", None)
        is_global_meta = bool(area_id == META_AREA_GLOBAL.lower())

        features: list[MagicAreasFeatures] = []
        for module in self._modules:
            if is_global_meta and not module.supports_global_meta_area:
                continue
            if is_meta and not is_global_meta and not module.supports_meta_area:
                continue
            if not is_meta and not module.supports_regular_area:
                continue
            features.append(module.id)
        return features

    def configurable_features_for_area(
        self, area_config: object | None
    ) -> list[MagicAreasFeatures]:
        """Return configurable features supported for the area type."""
        is_meta = self._is_meta_area(area_config)
        area_id = getattr(area_config, "id", None)
        is_global_meta = bool(area_id == META_AREA_GLOBAL.lower())

        features: list[MagicAreasFeatures] = []
        for module in self._modules:
            if module.config_schema() is None:
                continue
            if is_global_meta and (
                not module.supports_global_meta_area
                or not module.configurable_on_global_meta
            ):
                continue
            if is_meta and not is_global_meta and (
                not module.supports_meta_area or not module.configurable_on_meta
            ):
                continue
            if not is_meta and not module.supports_regular_area:
                continue
            features.append(module.id)
        return features

    def enabled_modules(self, data: MagicAreasData) -> list[FeatureModule]:
        """Return modules enabled for the area snapshot."""
        enabled: list[FeatureModule] = []
        for module in self._modules:
            if module.is_enabled(data):
                enabled.append(module)
        return enabled

    def validate_dependencies(self, data: MagicAreasData) -> None:
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


FEATURE_REGISTRY: FeatureRegistry = FeatureRegistry(
    modules=DEFAULT_FEATURE_MODULES
)
