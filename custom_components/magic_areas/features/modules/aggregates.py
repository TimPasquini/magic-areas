"""Aggregates feature module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.binary_sensor import (
    AreaAggregateBinarySensor,
    create_aggregate_sensors_from_definitions as create_binary_aggregates,
)
from custom_components.magic_areas.binary_sensor.threshold import (
    create_illuminance_threshold,
)
from custom_components.magic_areas.core.aggregate_policy import (
    AggregatePolicyContext,
    build_default_aggregate_selection_policy,
)
from custom_components.magic_areas.core.aggregate_runtime import (
    register_aggregate_definitions,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import (
    BaseFeatureModule,
    FeatureConfigStep,
)
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    DEFAULT_AGGREGATES_MIN_ENTITIES,
    DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
)
from custom_components.magic_areas.sensor.aggregate_factory import (
    AreaAggregateSensor,
    create_aggregate_sensors_from_definitions as create_sensor_aggregates,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


AGGREGATE_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_AGGREGATES_MIN_ENTITIES, default=DEFAULT_AGGREGATES_MIN_ENTITIES
        ): cv.positive_int,
        vol.Optional(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
        vol.Optional(
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
        vol.Optional(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
            default=DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
        ): cv.positive_int,
        vol.Optional(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
            default=DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
        ): cv.positive_int,
    },
    extra=vol.REMOVE_EXTRA,
)


class AggregatesFeatureModule(BaseFeatureModule):
    """Feature module for aggregates."""

    id = MagicAreasFeatures.AGGREGATES
    domains = {"sensor", "binary_sensor"}

    def config_schema(self) -> vol.Schema | None:
        """Return the config schema for this feature."""
        return AGGREGATE_FEATURE_SCHEMA

    def is_enabled(self, data: MagicAreasData) -> bool:
        """Return whether this feature is enabled for the area."""
        return MagicAreasFeatures.AGGREGATES in data.enabled_features

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
        register_aggregate_definitions(area_id=area_config.id, definitions=definitions)
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

    def config_flow_steps(self) -> list[FeatureConfigStep]:
        """Return config flow steps for this feature."""
        return [
            FeatureConfigStep(
                feature=MagicAreasFeatures.AGGREGATES,
                step_id="feature_conf_aggregates",
                schema=AGGREGATE_FEATURE_SCHEMA,
            )
        ]


__all__ = [
    "AggregatesFeatureModule",
    "AreaAggregateBinarySensor",
    "AreaAggregateSensor",
]
