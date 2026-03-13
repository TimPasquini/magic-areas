"""Health monitoring feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    create_health_sensors,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.features.config.readers import HEALTH_OPTION_KEYS

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


HEALTH_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.HEALTH,
    keys_and_validators=((HEALTH_OPTION_KEYS[0], cv.ensure_list),),
)


class HealthFeatureModule(BaseFeatureModule):
    """Feature module for health monitoring."""

    id = MagicAreasFeatures.HEALTH
    domains = {BINARY_SENSOR_DOMAIN}
    feature_schema = HEALTH_FEATURE_SCHEMA

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
        entity_list: list[Entity] = list(entities)
        return entity_list

__all__ = ["HealthFeatureModule"]
