"""Health monitoring feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    create_health_sensors,
)
from custom_components.magic_areas.config_keys.aggregates import (
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.core.aggregate_defaults import (
    DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


HEALTH_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_HEALTH_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
    },
    extra=vol.REMOVE_EXTRA,
)


class HealthFeatureModule(BaseFeatureModule):
    """Feature module for health monitoring."""

    id = MagicAreasFeatures.HEALTH
    domains = {BINARY_SENSOR_DOMAIN}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return HEALTH_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.HEALTH in data.enabled_features

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the health feature."""
        entities = create_health_sensors(
            data,
            data.entities,
            area_config,
            coordinator,
        )
        return cast(list[Entity], entities)

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.HEALTH,
                step_id="feature_conf_health",
                schema=HEALTH_FEATURE_SCHEMA,
            )
        ]


__all__ = ["HealthFeatureModule"]
