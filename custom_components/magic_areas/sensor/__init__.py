"""Sensor controls for magic areas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.group.sensor import ATTR_MEAN, ATTR_SUM, SensorGroup
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor.const import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.core.aggregates import AggregateDefinition
from custom_components.magic_areas.entity import MagicGroupEntity
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.policy import (
    AGGREGATE_MODE_SUM,
    AGGREGATE_MODE_TOTAL_INCREASING_SENSOR,
    AGGREGATE_MODE_TOTAL_SENSOR,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.components import MagicAreasConfigEntry

from custom_components.magic_areas.platform_dispatch import (
    async_setup_platform_via_features,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0
DEFAULT_SENSOR_DISPLAY_PRECISION = 2

type ExpectedEntityBuildErrors = tuple[
    type[KeyError],
    type[TypeError],
    type[ValueError],
    type[AttributeError],
    type[RuntimeError],
]

EXPECTED_ENTITY_BUILD_ERRORS: ExpectedEntityBuildErrors = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


class AreaSensorGroupSensor(MagicGroupEntity, SensorGroup):
    """Sensor for the magic area, group sensor with all the stuff in it."""

    def __init__(
        self,
        area_config: AreaConfig,
        coordinator: MagicAreasCoordinator,
        device_class: str,
        entity_ids: list[str],
        unit_of_measurement: str | None,
    ) -> None:
        """Initialize an area sensor group sensor."""

        MagicGroupEntity.__init__(
            self,
            area_config,
            coordinator,
            domain=SENSOR_DOMAIN,
            member_entity_ids=entity_ids,
            translation_key=device_class,
        )

        # Resolve unit of measurement (use hass from coordinator)
        unit_attr_name = f"{device_class}_unit"
        hass = coordinator.hass
        if hasattr(hass.config.units, unit_attr_name):
            final_unit_of_measurement = getattr(hass.config.units, unit_attr_name)
        else:
            final_unit_of_measurement = unit_of_measurement

        self._attr_suggested_display_precision = DEFAULT_SENSOR_DISPLAY_PRECISION

        sensor_device_class: SensorDeviceClass | None = (
            SensorDeviceClass(device_class) if device_class else None
        )
        self.device_class = sensor_device_class

        state_class = SensorStateClass.MEASUREMENT

        if device_class in AGGREGATE_MODE_TOTAL_INCREASING_SENSOR:
            state_class = SensorStateClass.TOTAL_INCREASING
        elif device_class in AGGREGATE_MODE_TOTAL_SENSOR:
            state_class = SensorStateClass.TOTAL

        SensorGroup.__init__(
            self,
            hass,
            name="",
            unique_id=self._attr_unique_id,
            entity_ids=self.member_entity_ids,
            unit_of_measurement=final_unit_of_measurement,
            device_class=sensor_device_class,
            state_class=state_class,
            sensor_type=ATTR_SUM if device_class in AGGREGATE_MODE_SUM else ATTR_MEAN,
            ignore_non_numeric=True,
        )
        delattr(self, "_attr_name")


class AreaAggregateSensor(AreaSensorGroupSensor):
    """Aggregate sensor for the area."""

    feature_id = MagicAreasFeatures.AGGREGATES


def _log_creation_error(*, area_slug: str, label: str, exc: Exception) -> None:
    """Log a standardized entity creation failure."""
    _LOGGER.error("%s: Error creating %s: %s", area_slug, label, str(exc))


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
        except EXPECTED_ENTITY_BUILD_ERRORS as exc:  # pragma: no cover
            _log_creation_error(
                area_slug=area_config.slug,
                label=f"'{definition.device_class}' aggregate sensor",
                exc=exc,
            )

    return aggregates


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area sensor config entry."""
    await async_setup_platform_via_features(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain=SENSOR_DOMAIN,
        logger=_LOGGER,
    )


__all__ = [
    "AreaAggregateSensor",
    "create_aggregate_sensors_from_definitions",
]
