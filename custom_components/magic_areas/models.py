"""Models for Magic Areas."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator
    from custom_components.magic_areas.base.magic import MagicArea


@dataclass
class MagicAreasRuntimeData:
    """Class to hold magic areas runtime data."""

    area: "MagicArea"
    coordinator: "MagicAreasCoordinator"
    listeners: list[Callable]


type MagicAreasConfigEntry = ConfigEntry[MagicAreasRuntimeData]
