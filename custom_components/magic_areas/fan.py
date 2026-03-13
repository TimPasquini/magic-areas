"""Fan groups & control for Magic Areas."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
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
    """Set up the area fan config entry."""
    await async_setup_platform_via_features(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain=FAN_DOMAIN,
        logger=_LOGGER,
    )
