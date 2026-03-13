"""Binary sensor platform setup and public factory exports."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.binary_sensor.aggregate_factory import (
    create_aggregate_sensors_from_definitions,
    create_ble_tracker_sensor,
    create_health_sensors,
    create_wasp_in_a_box_sensor,
)
from custom_components.magic_areas.binary_sensor.presence import (
    AreaStateBinarySensor,
    MetaAreaStateBinarySensor,
)
from custom_components.magic_areas.binary_sensor.threshold import (
    create_illuminance_threshold,
)
from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.platform_dispatch import (
    async_setup_platform_via_features,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.components import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area binary sensor config entry."""
    await async_setup_platform_via_features(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain=BINARY_SENSOR_DOMAIN,
        logger=_LOGGER,
        base_entities_builder=_build_platform_base_entities,
    )


def _build_platform_base_entities(
    area_config: AreaConfig,
    coordinator: MagicAreasCoordinator,
    _data: MagicAreasData,
) -> list[Entity]:
    """Build binary-sensor entities not dispatched through feature modules."""
    if area_config.is_meta():
        return [MetaAreaStateBinarySensor(area_config, coordinator)]
    return [AreaStateBinarySensor(area_config, coordinator)]


__all__ = [
    "create_aggregate_sensors_from_definitions",
    "create_ble_tracker_sensor",
    "create_health_sensors",
    "create_illuminance_threshold",
    "create_wasp_in_a_box_sensor",
]
