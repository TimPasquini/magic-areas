"""Platform setup for Magic Areas light entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.platform_dispatch import (
    async_setup_platform_via_features,
)

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.components import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area light config entry."""
    await async_setup_platform_via_features(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain=LIGHT_DOMAIN,
        logger=_LOGGER,
    )
