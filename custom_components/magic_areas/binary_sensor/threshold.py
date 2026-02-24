"""Platform file for Magic Areas threshold sensors."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
import homeassistant.components.sensor.const
from homeassistant.components.threshold.binary_sensor import ThresholdSensor
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.const import DOMAIN, EMPTY_STRING
from custom_components.magic_areas.coordinator import MagicAreasData, MagicAreasCoordinator
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.config_keys import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
)
from custom_components.magic_areas.defaults import DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES
from custom_components.magic_areas.feature_info import (
    MagicAreasFeatureInfoThreshold,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.area_config import AreaConfig

_LOGGER = logging.getLogger(__name__)


def create_illuminance_threshold(
    hass: HomeAssistant,
    data: MagicAreasData,
    area_config: "AreaConfig",
    coordinator: MagicAreasCoordinator,
) -> Entity | None:
    """Create threshold light binary sensor based off illuminance aggregate."""

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

    # Resolve illuminance aggregate entity ID from snapshot
    illuminance_aggregate_entity_id = (
        data.entity_references.aggregates_by_device_class.get(
            homeassistant.components.sensor.const.SensorDeviceClass.ILLUMINANCE
        )
    )
    if not illuminance_aggregate_entity_id:
        # Try direct entity registry lookup (aggregate may be registered but not yet in snapshot)
        illuminance_aggregate_entity_id = er.async_get(hass).async_get_entity_id(
            homeassistant.components.sensor.const.DOMAIN,
            DOMAIN,
            f"aggregates_{area_config.id}_aggregate_illuminance",
        )
    if not illuminance_aggregate_entity_id:
        _LOGGER.debug(
            "Area '%s': Illuminance aggregate not available yet, skipping threshold sensor",
            area_config.slug,
        )
        return None

    _LOGGER.debug(
        "Creating illuminance threshold sensor for area '%s': Threshold: %d, Hysteresis: %d (%d%%)",
        area_config.slug,
        illuminance_threshold,
        illuminance_threshold_hysteresis,
        illuminance_threshold_hysteresis_percentage,
    )

    try:
        return AreaThresholdSensor(
            hass=hass,
            area_config=area_config,
            coordinator=coordinator,
            device_class=BinarySensorDeviceClass.LIGHT,
            entity_id=illuminance_aggregate_entity_id,
            upper=illuminance_threshold,
            hysteresis=illuminance_threshold_hysteresis,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.error(
            "%s: Error creating calculated light sensor: %s",
            area_config.slug,
            str(e),
        )
        return None


class AreaThresholdSensor(MagicEntity, ThresholdSensor):
    """Threshold sensor based off aggregates."""

    feature_info = MagicAreasFeatureInfoThreshold()
    _area_name: str

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        area_config: "AreaConfig",
        coordinator: MagicAreasCoordinator,
        device_class: BinarySensorDeviceClass,
        entity_id: str,
        upper: float | None = None,
        lower: float | None = None,
        hysteresis: float = 0.0,
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(
            self, area_config, coordinator, domain=BINARY_SENSOR_DOMAIN, translation_key=device_class
        )
        ThresholdSensor.__init__(
            self,
            hass,
            entity_id=entity_id,
            name=EMPTY_STRING,
            unique_id=self.unique_id,
            lower=lower,
            upper=upper,
            hysteresis=float(hysteresis),
            device_class=device_class,
        )
        self._attr_name = None

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        await super().async_added_to_hass()
        # Explicitly call ThresholdSensor.async_added_to_hass to ensure listeners are registered
        # This handles cases where MRO might not route to it correctly via RestoreEntity
        if hasattr(ThresholdSensor, "async_added_to_hass"):
            await ThresholdSensor.async_added_to_hass(self)
        self.async_write_ha_state()
