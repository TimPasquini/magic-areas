"""Sensor controls for magic areas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.components import MagicAreasConfigEntry

from custom_components.magic_areas.platform_dispatch import (
    async_setup_platform_via_features,
)

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


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
