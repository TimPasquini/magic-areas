"""Sensor controls for magic areas."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.aggregates import build_sensor_aggregates
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoAggregates,
)
from custom_components.magic_areas.features import CONF_FEATURE_AGGREGATION
from custom_components.magic_areas.sensor.base import AreaSensorGroupSensor
from custom_components.magic_areas.util import cleanup_removed_entries

if TYPE_CHECKING:
    from custom_components.magic_areas.models import MagicAreasConfigEntry

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
    area: MagicArea = data.area
    entities_by_domain = data.entities
    magic_entities = data.magic_entities

    entities_to_add: list[Entity] = []

    if CONF_FEATURE_AGGREGATION in data.enabled_features:
        entities_to_add.extend(create_aggregate_sensors(data, entities_by_domain))

    if entities_to_add:
        async_add_entities(entities_to_add)

    if SENSOR_DOMAIN in magic_entities:
        cleanup_removed_entries(
            area.hass, entities_to_add, magic_entities[SENSOR_DOMAIN]
        )


def create_aggregate_sensors(
    data: MagicAreasData, entities_by_domain: dict[str, list[dict[str, str]]]
) -> list[Entity]:
    """Create the aggregate sensors for the area."""
    area = data.area

    aggregates: list[Entity] = []

    aggregate_specs = build_sensor_aggregates(
        entities_by_domain=entities_by_domain,
        feature_configs=data.feature_configs,
        enabled_features=data.enabled_features,
    )

    for spec in aggregate_specs:
        _LOGGER.debug(
            "%s: Creating aggregate sensor for device_class '%s' with %d entities",
            area.slug,
            spec.device_class,
            len(spec.entity_ids),
        )

        try:
            aggregates.append(
                AreaAggregateSensor(
                    area=area,
                    device_class=spec.device_class,
                    entity_ids=spec.entity_ids,
                    unit_of_measurement=spec.unit_of_measurement,
                )
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "%s: Error creating '%s' aggregate sensor: %s",
                area.slug,
                spec.device_class,
                str(e),
            )

    return aggregates


class AreaAggregateSensor(AreaSensorGroupSensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoAggregates()
