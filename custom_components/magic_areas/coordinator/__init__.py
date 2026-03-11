"""Coordinator for Magic Areas."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.coordinator.snapshot_builder import build_snapshot
from custom_components.magic_areas.coordinator.snapshot_models import MagicAreasData
from custom_components.magic_areas.core.meta_reload import (
    evaluate_reload,
    should_reload_on_area_change,
)
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


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

        try:
            return await build_snapshot(
                hass=self.hass,
                area_config=self._area_config,
                config_entry_id=self.config_entry.entry_id,
            )
        except Exception as err:  # pylint: disable=broad-exception-caught
            raise UpdateFailed(f"Unable to update area data: {err}") from err
