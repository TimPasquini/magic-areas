"""Coordinator for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.base.magic import MagicArea, MagicMetaArea
from custom_components.magic_areas.core_constants import DOMAIN
from custom_components.magic_areas.core.config import normalize_feature_config
from custom_components.magic_areas.core.meta import (
    build_meta_presence_sensors,
    resolve_active_areas,
)
from custom_components.magic_areas.core.presence import build_presence_sensors
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
            self.area.last_update_success = False
            raise UpdateFailed(f"Unable to update area data: {err}") from err
        else:
            self.area.last_update_success = True

        enabled_features, feature_configs = normalize_feature_config(self.area.config)
        presence_sensors = build_presence_sensors(
            entities_by_domain=self.area.entities,
            config=self.area.config,
            slug=self.area.slug,
            enabled_features=enabled_features,
        )
        active_areas: list[str] = []
        if isinstance(self.area, MagicMetaArea):
            presence_sensors = build_meta_presence_sensors(self.area.child_areas)
            state_map: dict[str, str] = {}
            for area_id in self.area.child_areas:
                entity_id = (
                    f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{area_id}_area_state"
                )
                area_state = self.hass.states.get(entity_id)
                if area_state:
                    state_map[area_id] = area_state.state
            active_areas = resolve_active_areas(self.area.child_areas, state_map)

        return MagicAreasData(
            area=self.area,
            entities=self.area.entities,
            magic_entities=self.area.magic_entities,
            presence_sensors=presence_sensors,
            active_areas=active_areas,
            config=self.area.config,
            enabled_features=enabled_features,
            feature_configs=feature_configs,
            updated_at=dt_util.utcnow(),
        )
