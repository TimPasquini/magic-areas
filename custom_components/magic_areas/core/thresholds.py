"""Threshold calculation helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import homeassistant.components.sensor.const
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.aggregate_runtime import (
    resolve_aggregate_entity_id,
)
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
)
from custom_components.magic_areas.defaults import DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES
from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig
    from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData

_LOGGER = logging.getLogger(__name__)


def get_illuminance_threshold_spec(
    hass: HomeAssistant,
    data: MagicAreasData,
    area_config: AreaConfig,
) -> tuple[str, float, float, float] | None:
    """Return illuminance threshold config or None if unavailable."""
    if MagicAreasFeatures.AGGREGATES not in data.enabled_features:  # pragma: no cover
        return None

    aggregation_config = data.feature_configs.get(MagicAreasFeatures.AGGREGATES, {})
    illuminance_threshold = aggregation_config.get(
        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
        DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
    )

    if illuminance_threshold == 0:
        return None

    if (  # pragma: no cover
        homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
        not in aggregation_config.get(
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
            DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
        )
    ):
        return None

    if homeassistant.components.sensor.const.DOMAIN not in data.entities:
        return None

    illuminance_sensors = [
        sensor
        for sensor in data.entities[homeassistant.components.sensor.const.DOMAIN]
        if ATTR_DEVICE_CLASS in sensor
        and sensor[ATTR_DEVICE_CLASS]
        == homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
    ]

    if not illuminance_sensors:  # pragma: no cover
        return None

    illuminance_threshold_hysteresis_percentage = aggregation_config.get(
        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
        DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    )
    illuminance_threshold_hysteresis = 0.0

    if illuminance_threshold_hysteresis_percentage > 0:
        illuminance_threshold_hysteresis = illuminance_threshold * (
            illuminance_threshold_hysteresis_percentage / 100
        )

    illuminance_aggregate_entity_id = resolve_aggregate_entity_id(
        hass,
        area_id=area_config.id,
        domain=homeassistant.components.sensor.const.DOMAIN,
        device_class=str(
            homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
        ),
    )
    if not illuminance_aggregate_entity_id:
        illuminance_aggregate_entity_id = data.entity_references.aggregates_by_device_class.get(
            homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
        )
    if not illuminance_aggregate_entity_id:
        _LOGGER.debug(
            "Area '%s': Illuminance aggregate not available yet, skipping threshold sensor",
            area_config.slug,
        )
        return None

    return (
        illuminance_aggregate_entity_id,
        float(illuminance_threshold),
        float(illuminance_threshold_hysteresis),
        float(illuminance_threshold_hysteresis_percentage),
    )
