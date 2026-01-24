"""Coordinator for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.base.magic import MagicArea, MagicMetaArea
from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.core.config import normalize_feature_config
from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MagicAreasData:
    """Snapshot of area data used by platforms."""

    area: MagicArea
    entities: dict[str, list[dict[str, str]]]
    magic_entities: dict[str, list[dict[str, str]]]
    presence_sensors: list[str]
    active_areas: list[str]
    config: dict[str, Any]
    enabled_features: set[str]
    feature_configs: dict[str, dict[str, Any]]
    updated_at: datetime


class MagicAreasCoordinator(DataUpdateCoordinator[MagicAreasData]):
    """Update coordinator for Magic Areas."""

    def __init__(
        self,
        hass: HomeAssistant,
        area: MagicArea,
        config_entry: MagicAreasConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
            config_entry=config_entry,
        )
        self.area = area

    async def _async_update_data(self) -> MagicAreasData:
        """Fetch area data for the coordinator."""
        try:
            if isinstance(self.area, MagicMetaArea):
                self.area.child_areas = self.area.get_child_areas()
            await self.area.load_entities()
        except Exception as err:  # pylint: disable=broad-exception-caught
            raise UpdateFailed(f"Unable to update area data: {err}") from err

        enabled_features, feature_configs = normalize_feature_config(self.area.config)
        active_areas: list[str] = []
        if isinstance(self.area, MagicMetaArea):
            active_areas = self.area.get_active_areas()

        return MagicAreasData(
            area=self.area,
            entities=self.area.entities,
            magic_entities=self.area.magic_entities,
            presence_sensors=self.area.get_presence_sensors(),
            active_areas=active_areas,
            config=self.area.config,
            enabled_features=enabled_features,
            feature_configs=feature_configs,
            updated_at=dt_util.utcnow(),
        )
