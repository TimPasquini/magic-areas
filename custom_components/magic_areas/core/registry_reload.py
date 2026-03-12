"""Registry reload helpers for Magic Areas."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.const import ATTR_NAME, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import (
    EVENT_DEVICE_REGISTRY_UPDATED,
    EventDeviceRegistryUpdatedData,
)
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EventEntityRegistryUpdatedData,
)
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.config_keys.system import (
    CONF_RELOAD_ON_REGISTRY_CHANGE,
)
from custom_components.magic_areas.defaults import (
    DEFAULT_RELOAD_ON_REGISTRY_CHANGE,
)
from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core.registry_filters import (
    make_device_registry_filter,
    make_entity_registry_filter,
)
from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


@callback
async def async_reload_entry(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> None:
    """Trigger a reload by updating the entry data timestamp."""
    if not hass.is_running:
        return

    hass.config_entries.async_update_entry(
        config_entry,
        data={**config_entry.data, "entity_ts": dt_util.utcnow()},
    )


@callback
async def async_registry_updated(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    event: Event[EventEntityRegistryUpdatedData] | Event[EventDeviceRegistryUpdatedData],
) -> None:
    """Handle registry updates that should reload the integration."""
    area_data: dict[str, Any] = dict(config_entry.data)
    if config_entry.options:
        area_data.update(config_entry.options)

    if not area_data.get(
        CONF_RELOAD_ON_REGISTRY_CHANGE, DEFAULT_RELOAD_ON_REGISTRY_CHANGE
    ):
        _LOGGER.debug(
            "%s: Auto-Reloading disabled for this area skipping...",
            config_entry.data[ATTR_NAME],
        )
        return

    _LOGGER.debug(
        "%s: Reloading entry due entity registry change",
        config_entry.data[ATTR_NAME],
    )

    await async_reload_entry(hass, config_entry)


def attach_registry_listeners(
    hass: HomeAssistant,
    config_entry: MagicAreasConfigEntry,
    area_config: AreaConfig,
    tracked_listeners: list[Callable[[], None]],
) -> None:
    """Attach entity/device registry listeners for a non-meta area."""
    @callback
    async def _handle_registry(
        event: Event[EventEntityRegistryUpdatedData]
        | Event[EventDeviceRegistryUpdatedData],
    ) -> None:
        await async_registry_updated(hass, config_entry, event)

    tracked_listeners.append(
        hass.bus.async_listen(
            EVENT_ENTITY_REGISTRY_UPDATED,
            _handle_registry,
            make_entity_registry_filter(hass, area_config.id, config_entry.entry_id),
        )
    )
    tracked_listeners.append(
        hass.bus.async_listen(
            EVENT_DEVICE_REGISTRY_UPDATED,
            _handle_registry,
            make_device_registry_filter(hass, area_config.id, config_entry.entry_id),
        )
    )
    @callback
    async def _handle_start(_event: Event) -> None:
        await async_reload_entry(hass, config_entry)

    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STARTED,
        _handle_start,
    )
