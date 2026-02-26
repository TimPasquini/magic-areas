"""Sensor controls for magic areas."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry
    from custom_components.magic_areas.features.registry import FeatureRegistry

from custom_components.magic_areas.helpers.cleanup import cleanup_removed_entries
from custom_components.magic_areas.features.dispatch import collect_feature_entities

_LOGGER = logging.getLogger(__name__)
FEATURE_REGISTRY: "FeatureRegistry | None" = None


def _get_feature_registry() -> "FeatureRegistry":
    if FEATURE_REGISTRY is not None:
        return FEATURE_REGISTRY
    from custom_components.magic_areas.features.registry import FEATURE_REGISTRY as registry

    return registry


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
    magic_entities = data.magic_entities

    registry = _get_feature_registry()
    entities_to_add = collect_feature_entities(
        domain=SENSOR_DOMAIN,
        registry=registry,
        data=data,
        area_config=area_config,
        coordinator=coordinator,
        logger=_LOGGER,
    )

    if entities_to_add:
        async_add_entities(entities_to_add)

    if SENSOR_DOMAIN in magic_entities:
        cleanup_removed_entries(
            hass, entities_to_add, magic_entities[SENSOR_DOMAIN]
        )
