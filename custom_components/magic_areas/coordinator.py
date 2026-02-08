"""Coordinator for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.base.magic import MagicArea, MagicMetaArea
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.config import normalize_feature_config
from custom_components.magic_areas.core.entity_ids import (
    EntityReferences,
    build_entity_references,
)
from custom_components.magic_areas.core.meta import (
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
    entity_references: EntityReferences
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
        entity_registry = er.async_get(self.hass)

        # Build entity references first (used by presence sensor resolution)
        entity_references = build_entity_references(
            area_id=self.area.id,
            entity_registry=entity_registry,
        )

        presence_sensors = build_presence_sensors(
            entities_by_domain=self.area.entities,
            config=self.area.config,
            slug=self.area.slug,
            enabled_features=enabled_features,
            entity_references=entity_references,
        )
        active_areas: list[str] = []
        if isinstance(self.area, MagicMetaArea):
            # Resolve child area presence sensors from entity registry
            child_presence_sensors: list[str] = []
            state_map: dict[str, str] = {}
            for child_area_id in self.area.child_areas:
                child_entity_id = entity_registry.async_get_entity_id(
                    BINARY_SENSOR_DOMAIN,
                    DOMAIN,
                    f"presence_tracking_{child_area_id}_area_state",
                )
                if child_entity_id:
                    child_presence_sensors.append(child_entity_id)
                    area_state = self.hass.states.get(child_entity_id)
                    if area_state:
                        state_map[child_area_id] = area_state.state
            presence_sensors = child_presence_sensors
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
            entity_references=entity_references,
            updated_at=dt_util.utcnow(),
        )
