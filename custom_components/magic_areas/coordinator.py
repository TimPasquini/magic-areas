"""Coordinator for Magic Areas."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core.area_runtime import AreaRuntime
from custom_components.magic_areas.core.config import normalize_feature_config
from custom_components.magic_areas.core.entity_ids import (
    EntityReferences,
    build_entity_references,
)
from custom_components.magic_areas.core.entity_loading import (
    load_area_entities,
    load_meta_area_entities,
)
from custom_components.magic_areas.core.meta import (
    collect_child_areas,
    resolve_active_areas,
)
from custom_components.magic_areas.core.meta_reload import (
    evaluate_reload,
    should_reload_on_area_change,
)
from custom_components.magic_areas.core.presence import build_presence_sensors
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MagicAreasData:
    """Snapshot of area data used by platforms.

    Coordinator builds a complete snapshot with:
    - area_config: Immutable configuration
    - area_runtime: Mutable state
    - Platforms read snapshot only; MagicArea is coordinator-internal
    """

    entities: dict[str, list[dict[str, str]]]
    magic_entities: dict[str, list[dict[str, str]]]
    presence_sensors: list[str]
    active_areas: list[str]
    child_areas: list[str]
    config: dict[str, Any]
    enabled_features: set[str]
    feature_configs: dict[str, dict[str, Any]]
    entity_references: EntityReferences
    area_config: AreaConfig
    area_runtime: AreaRuntime
    updated_at: datetime


class MagicAreasCoordinator(DataUpdateCoordinator[MagicAreasData]):
    """Update coordinator for Magic Areas."""

    def __init__(
        self,
        hass: HomeAssistant,
        area_config: AreaConfig,
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
        self._area_config = area_config
        self._last_reload: datetime = datetime.min.replace(tzinfo=dt_util.UTC)
        self._reloading: bool = False
        self._unsubscribe_loaded: Callable[[], None] | None = None

        if area_config.is_meta():
            self._unsubscribe_loaded = async_dispatcher_connect(
                hass, MagicAreasEvents.AREA_LOADED, self._handle_loaded_area
            )

    async def async_shutdown(self) -> None:
        """Shut down the coordinator and clean up subscriptions."""
        if self._unsubscribe_loaded is not None:
            self._unsubscribe_loaded()
            self._unsubscribe_loaded = None
        await super().async_shutdown()

    @callback
    async def _handle_loaded_area(
        self, area_type: str, floor_id: int | None, area_id: str
    ) -> None:
        """Handle area loaded signals for meta-area reload."""
        _LOGGER.debug(
            "%s: Received area loaded signal (type=%s, floor_id=%s, area_id=%s)",
            self._area_config.name,
            area_type,
            floor_id,
            area_id,
        )

        if not self.hass.is_running:
            return

        if self._reloading:
            return

        child_areas = self.data.child_areas if self.data else []

        if not should_reload_on_area_change(
            meta_slug=self._area_config.slug,
            trigger_area_type=area_type,
            trigger_area_id=area_id,
            child_areas=child_areas,
        ):
            return

        await self._do_reload(trigger_area_type=area_type, trigger_area_id=area_id)

    async def _do_reload(
        self, trigger_area_type: str = "", trigger_area_id: str = ""
    ) -> None:
        """Reload the config entry after evaluating throttle and delay."""
        child_areas = self.data.child_areas if self.data else []
        decision = evaluate_reload(
            meta_slug=self._area_config.slug,
            trigger_area_type=trigger_area_type,
            trigger_area_id=trigger_area_id,
            child_areas=child_areas,
            last_reload=self._last_reload,
            now=dt_util.utcnow(),
        )

        if not decision.should_reload:
            _LOGGER.debug(
                "%s: Reload skipped - %s", self._area_config.name, decision.reason
            )
            return

        _LOGGER.info(
            "%s: Reloading entry - %s", self._area_config.name, decision.reason
        )
        self._last_reload = dt_util.utcnow()
        self._reloading = True
        await asyncio.sleep(decision.delay_seconds)
        assert self.config_entry is not None
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

    async def _async_update_data(self) -> MagicAreasData:
        """Fetch area data for the coordinator."""
        assert self.config_entry is not None
        entities: dict[str, list[dict[str, str]]] = {}
        magic_entities: dict[str, list[dict[str, str]]] = {}
        child_areas_list: list[str] = []
        last_update_success = True

        try:
            if self._area_config.is_meta():
                child_areas_list = collect_child_areas(
                    self.hass,
                    self._area_config.id,
                    self._area_config.slug,
                    self._area_config.floor_id,
                )
                entities, magic_entities = await load_meta_area_entities(
                    hass=self.hass,
                    child_area_slugs=child_areas_list,
                    config_entry_id=self.config_entry.entry_id,
                    config=self._area_config.config,
                    logger=_LOGGER,
                )
            else:
                entities, magic_entities = await load_area_entities(
                    hass=self.hass,
                    area_id=self._area_config.id,
                    config_entry_id=self.config_entry.entry_id,
                    config=self._area_config.config,
                    logger=_LOGGER,
                )
        except Exception as err:  # pylint: disable=broad-exception-caught
            last_update_success = False
            raise UpdateFailed(f"Unable to update area data: {err}") from err

        enabled_features, feature_configs = normalize_feature_config(self._area_config.config)
        entity_registry = er.async_get(self.hass)

        entity_references = build_entity_references(
            area_id=self._area_config.id,
            entity_registry=entity_registry,
        )

        presence_sensors = build_presence_sensors(
            entities_by_domain=entities,
            config=self._area_config.config,
            slug=self._area_config.slug,
            enabled_features=enabled_features,
            entity_references=entity_references,
        )

        active_areas: list[str] = []
        if self._area_config.is_meta():
            child_presence_sensors: list[str] = []
            state_map: dict[str, str] = {}
            for child_area_id in child_areas_list:
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
            active_areas = resolve_active_areas(child_areas_list, state_map)

        area_runtime = AreaRuntime(last_update_success=last_update_success)

        return MagicAreasData(
            area_config=self._area_config,
            area_runtime=area_runtime,
            entities=entities,
            magic_entities=magic_entities,
            presence_sensors=presence_sensors,
            active_areas=active_areas,
            child_areas=child_areas_list,
            config=self._area_config.config,
            enabled_features=enabled_features,
            feature_configs=feature_configs,
            entity_references=entity_references,
            updated_at=dt_util.utcnow(),
        )
