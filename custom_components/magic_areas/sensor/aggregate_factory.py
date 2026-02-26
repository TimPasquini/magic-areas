"""Aggregate sensor factory for Magic Areas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.core.snapshot_builder import MagicAreasData
from custom_components.magic_areas.core.aggregates import build_sensor_aggregates
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
    aggregates: list[Entity] = []

    aggregate_specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=data.feature_configs,
        enabled_features=data.enabled_features,
    )

    for spec in aggregate_specs:
        _LOGGER.debug(
            "%s: Creating aggregate sensor for device_class '%s' with %d entities",
            area_config.slug,
            spec.device_class,
            len(spec.entity_ids),
        )

        try:
            aggregates.append(
                AreaAggregateSensor(
                    area_config=area_config,
                    coordinator=coordinator,
                    device_class=spec.device_class,
                    entity_ids=spec.entity_ids,
                    unit_of_measurement=spec.unit_of_measurement,
                )
            )
        except (
            Exception
        ) as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error creating '%s' aggregate sensor: %s",
                area_config.slug,
                spec.device_class,
                str(e),
            )

    return aggregates


class AreaAggregateSensor(AreaSensorGroupSensor):
    """Aggregate sensor for the area."""

    feature_id = MagicAreasFeatures.AGGREGATES
