"""Wasp-in-a-Box feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    create_wasp_in_a_box_sensor,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.features.config.readers import WASP_IN_A_BOX_OPTION_KEYS

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


WASP_IN_A_BOX_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.WASP_IN_A_BOX,
    keys_and_validators=(
        (WASP_IN_A_BOX_OPTION_KEYS[0], cv.positive_int),
        (WASP_IN_A_BOX_OPTION_KEYS[1], cv.positive_int),
        (WASP_IN_A_BOX_OPTION_KEYS[2], cv.ensure_list),
    ),
)


class WaspInABoxFeatureModule(BaseFeatureModule):
    """Feature module for Wasp in a Box."""

    id = MagicAreasFeatures.WASP_IN_A_BOX
    domains = {"binary_sensor"}
    feature_schema = WASP_IN_A_BOX_FEATURE_SCHEMA
    supports_meta_area = False
    supports_global_meta_area = False

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return (
            MagicAreasFeatures.WASP_IN_A_BOX in data.enabled_features
            and MagicAreasFeatures.AGGREGATES in data.enabled_features
        )

    def depends_on(self) -> set[MagicAreasFeatures]:
        """Return feature dependencies required for this module."""
        return {MagicAreasFeatures.AGGREGATES}

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the Wasp-in-a-Box feature."""
        if area_config.is_meta():
            return []
        entities: list[Entity] = list(
            create_wasp_in_a_box_sensor(data, area_config, coordinator)
        )
        return entities

__all__ = ["WaspInABoxFeatureModule"]
