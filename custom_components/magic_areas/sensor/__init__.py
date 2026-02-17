"""Sensor controls for magic areas."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.aggregates import build_sensor_aggregates
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoAggregates,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.sensor.base import AreaSensorGroupSensor

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.models import MagicAreasConfigEntry

from custom_components.magic_areas.helpers.cleanup import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "MagicAreasConfigEntry",
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area sensor config entry."""

    runtime_data = config_entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        _LOGGER.debug("Skipping sensor setup; coordinator data unavailable")
        return
    area_config = data.area_config
    coordinator = runtime_data.coordinator
    entities_by_domain = data.entities
    magic_entities = data.magic_entities

    entities_to_add: list[Entity] = []

    if MagicAreasFeatures.AGGREGATES in data.enabled_features:
        entities_to_add.extend(
            create_aggregate_sensors(data, entities_by_domain, area_config, coordinator)
        )

    if entities_to_add:
        async_add_entities(entities_to_add)

    if SENSOR_DOMAIN in magic_entities:
        cleanup_removed_entries(
            hass, entities_to_add, magic_entities[SENSOR_DOMAIN]
        )


def create_aggregate_sensors(
    data: MagicAreasData,
    entities_by_domain: dict[str, list[dict[str, str]]],
    area_config: "AreaConfig",
    coordinator: "MagicAreasCoordinator",
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

    feature_info = MagicAreasFeatureInfoAggregates()
