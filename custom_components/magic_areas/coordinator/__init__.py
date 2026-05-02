"""Coordinator for Magic Areas."""

from __future__ import annotations

from datetime import timedelta
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.coordinator.pipeline import (
    MetaAreaReloadManager,
    MagicAreasData,
    attach_registry_listeners as attach_registry_listeners,
    build_snapshot,
)
from custom_components.magic_areas.coordinator.managed_surfaces import (
    async_reconcile_config_entry_helpers,
    async_reconcile_managed_surfaces,
)
from custom_components.magic_areas.enums import MagicAreasEvents
from custom_components.magic_areas.components import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)
_EXPECTED_UPDATE_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)

__all__ = [
    "MagicAreasCoordinator",
    "MagicAreasData",
    "async_reconcile_config_entry_helpers",
    "async_reconcile_managed_surfaces",
    "attach_registry_listeners",
]


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
        self._lifecycle: MetaAreaReloadManager | None = None
        self._group_registry = GroupRegistry()
        self._last_snapshot_ready_key: tuple[str, str | None, str, str | None] | None = None

        if area_config.is_meta():
            self._lifecycle = MetaAreaReloadManager(
                hass=hass,
                area_config=area_config,
                get_snapshot=lambda: self.data,
                get_entry_id=lambda: self.config_entry.entry_id if self.config_entry else None,
                schedule_reload=hass.config_entries.async_schedule_reload,
            )
            self._lifecycle.start()

    @property
    def lifecycle(self) -> MetaAreaReloadManager | None:
        """Return lifecycle manager for meta areas, if configured."""
        return self._lifecycle

    async def async_shutdown(self) -> None:
        """Shut down the coordinator and clean up subscriptions."""
        if self._lifecycle is not None:
            await self._lifecycle.shutdown()
            self._lifecycle = None
        await super().async_shutdown()

    async def _async_update_data(self) -> MagicAreasData:
        """Fetch area data for the coordinator."""
        assert self.config_entry is not None

        try:
            snapshot = await build_snapshot(
                hass=self.hass,
                area_config=self._area_config,
                config_entry_id=self.config_entry.entry_id,
                group_registry=self._group_registry,
            )
            if not self._area_config.is_meta():
                ready_key = (
                    self._area_config.area_type,
                    self._area_config.floor_id,
                    self._area_config.id,
                    snapshot.entity_references.area_state_sensor,
                )
                if ready_key != self._last_snapshot_ready_key:
                    dispatcher_send(
                        self.hass,
                        MagicAreasEvents.AREA_SNAPSHOT_READY,
                        self._area_config.area_type,
                        self._area_config.floor_id,
                        self._area_config.id,
                        snapshot.updated_at.isoformat(),
                    )
                    self._last_snapshot_ready_key = ready_key
            return snapshot
        except _EXPECTED_UPDATE_ERRORS as err:
            raise UpdateFailed(f"Unable to update area data: {err}") from err
