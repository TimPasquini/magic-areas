"""Aggregate sensor factory for Magic Areas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.core.aggregate_policy import (
    AggregatePolicyContext,
    AggregateDefinition,
    build_default_aggregate_selection_policy,
)
from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.sensor.base import AreaSensorGroupSensor

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator

_LOGGER = logging.getLogger(__name__)


def create_aggregate_sensors(
    data: MagicAreasData,
    entities_by_domain: dict[str, list[dict[str, str]]],
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
) -> list[Entity]:
    """Create the aggregate sensors for the area."""
    policy = build_default_aggregate_selection_policy()
    definitions = policy.aggregate_definitions(
        AggregatePolicyContext(
            entities_by_domain=entities_by_domain,
            feature_configs=data.feature_configs,
            enabled_features=data.enabled_features,
        )
    )
    return create_aggregate_sensors_from_definitions(
        definitions=definitions,
        area_config=area_config,
        coordinator=coordinator,
    )


def create_aggregate_sensors_from_definitions(
    *,
    definitions: list[AggregateDefinition],
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
) -> list[Entity]:
    """Create sensor aggregates from canonical aggregate definitions."""
    aggregates: list[Entity] = []

    for definition in definitions:
        if definition.domain != SENSOR_DOMAIN:
            continue
        if definition.unit_of_measurement is None:
            continue
        _LOGGER.debug(
            "%s: Creating aggregate sensor for device_class '%s' with %d entities",
            area_config.slug,
            definition.device_class,
            len(definition.entity_ids),
        )

        try:
            aggregates.append(
                AreaAggregateSensor(
                    area_config=area_config,
                    coordinator=coordinator,
                    device_class=definition.device_class,
                    entity_ids=list(definition.entity_ids),
                    unit_of_measurement=definition.unit_of_measurement,
                )
            )
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error creating '%s' aggregate sensor: %s",
                area_config.slug,
                definition.device_class,
                str(e),
            )

    return aggregates


class AreaAggregateSensor(AreaSensorGroupSensor):
    """Aggregate sensor for the area."""

    feature_id = MagicAreasFeatures.AGGREGATES
