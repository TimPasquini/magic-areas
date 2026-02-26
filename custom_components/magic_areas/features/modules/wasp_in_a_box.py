"""Wasp-in-a-Box feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    create_wasp_in_a_box_sensor,
)
from custom_components.magic_areas.config_keys import (
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    CONF_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_WASP_IN_A_BOX_DELAY,
    DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


WASP_IN_A_BOX_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_WASP_IN_A_BOX_DELAY, default=DEFAULT_WASP_IN_A_BOX_DELAY
        ): cv.positive_int,
        vol.Optional(
            CONF_WASP_IN_A_BOX_WASP_TIMEOUT, default=DEFAULT_WASP_IN_A_BOX_WASP_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
            default=DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
        ): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)


class WaspInABoxFeatureModule(BaseFeatureModule):
    """Feature module for Wasp in a Box."""

    id = MagicAreasFeatures.WASP_IN_A_BOX
    domains = {"binary_sensor"}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return WASP_IN_A_BOX_FEATURE_SCHEMA

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
        entities = create_wasp_in_a_box_sensor(data, area_config, coordinator)
        return cast(list[Entity], entities)

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.WASP_IN_A_BOX,
                step_id="feature_conf_wasp_in_a_box",
                schema=WASP_IN_A_BOX_FEATURE_SCHEMA,
            )
        ]


__all__ = ["WaspInABoxFeatureModule"]
