"""Local platform dispatch facade.

Keeps top-level platform modules decoupled from feature internals by exposing
a stable local setup helper.
"""

from __future__ import annotations

from collections.abc import Callable
from logging import Logger
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.coordinator import MagicAreasData
    from custom_components.magic_areas.components import MagicAreasConfigEntry
    from custom_components.magic_areas.core.runtime_model import AreaConfig
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


async def async_setup_platform_via_features(
    *,
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    async_add_entities: AddEntitiesCallback,
    domain: str,
    logger: Logger,
    base_entities_builder: Callable[
        [AreaConfig, MagicAreasCoordinator, MagicAreasData], list[Entity]
    ]
    | None = None,
) -> None:
    """Set up one platform via feature dispatch."""
    from custom_components.magic_areas.features.dispatch import (
        async_setup_feature_platform,
    )

    await async_setup_feature_platform(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        domain=domain,
        logger=logger,
        base_entities_builder=base_entities_builder,
    )

