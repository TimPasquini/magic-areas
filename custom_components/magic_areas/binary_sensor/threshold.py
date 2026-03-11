"""Platform file for Magic Areas threshold sensors."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.threshold.binary_sensor import ThresholdSensor
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from custom_components.magic_areas.entity import MagicEntity
from custom_components.magic_areas.const import EMPTY_STRING
from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
from custom_components.magic_areas.core.thresholds import (
    get_illuminance_threshold_spec,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

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

    spec = get_illuminance_threshold_spec(hass, data, area_config)
    if not spec:
        return None
    (
        illuminance_aggregate_entity_id,
        illuminance_threshold,
        illuminance_threshold_hysteresis,
        illuminance_threshold_hysteresis_percentage,
    ) = spec

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

    feature_id = MagicAreasFeatures.THRESHOLD
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
