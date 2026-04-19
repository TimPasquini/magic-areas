"""Aggregates feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    create_aggregate_sensors_from_definitions as create_binary_aggregates,
    create_illuminance_threshold,
)
from custom_components.magic_areas.core.aggregates import (
    AggregatePolicyContext,
    build_default_aggregate_selection_policy,
    register_aggregate_definitions,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    schema_from_default_options,
)
from custom_components.magic_areas.features.config.readers import AGGREGATES_OPTION_KEYS
from custom_components.magic_areas.sensor import (
    AreaAggregateSensor,
    create_aggregate_sensors_from_definitions as create_sensor_aggregates,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


AGGREGATE_FEATURE_SCHEMA = schema_from_default_options(
    feature=MagicAreasFeatures.AGGREGATES,
    keys_and_validators=(
        (AGGREGATES_OPTION_KEYS[0], cv.positive_int),
        (AGGREGATES_OPTION_KEYS[1], cv.positive_int),
        (AGGREGATES_OPTION_KEYS[2], cv.positive_int),
        (AGGREGATES_OPTION_KEYS[3], [str]),
        (AGGREGATES_OPTION_KEYS[4], [str]),
    ),
)


class AggregatesFeatureModule(BaseFeatureModule):
    """Feature module for aggregates."""

    id = MagicAreasFeatures.AGGREGATES
    domains = {"sensor", "binary_sensor"}
    feature_schema = AGGREGATE_FEATURE_SCHEMA

    def build_entities(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        data: MagicAreasData,
    ) -> list[Entity]:
        """Build entities for the aggregates feature."""
        policy = build_default_aggregate_selection_policy()
        definitions = policy.aggregate_definitions(
            AggregatePolicyContext(
                entities_by_domain=data.entities,
                feature_configs=data.feature_configs,
                enabled_features=data.enabled_features,
            )
        )
        register_aggregate_definitions(
            group_registry=data.group_registry,
            area_id=area_config.id,
            definitions=definitions,
        )
        entities: list[Entity] = []

        entities.extend(
            create_sensor_aggregates(
                definitions=definitions,
                area_config=area_config,
                coordinator=coordinator,
            )
        )

        entities.extend(
            create_binary_aggregates(
                definitions=definitions,
                area_config=area_config,
                coordinator=coordinator,
            )
        )

        threshold_entity = create_illuminance_threshold(
            coordinator.hass, data, area_config, coordinator
        )
        if threshold_entity:
            entities.append(threshold_entity)

        return entities

__all__ = [
    "AggregatesFeatureModule",
    "AreaAggregateSensor",
]
