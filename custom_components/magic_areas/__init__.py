"""Magic Areas component for Home Assistant."""

from collections.abc import Callable
import logging
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

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    CONF_RELOAD_ON_REGISTRY_CHANGE,
    DEFAULT_RELOAD_ON_REGISTRY_CHANGE,
    MagicConfigEntryVersion,
)
from custom_components.magic_areas.helpers.area import get_magic_area_for_config_entry
from custom_components.magic_areas.models import MagicAreasConfigEntry, MagicAreasRuntimeData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: MagicAreasConfigEntry) -> bool:
    """Set up the component."""

    @callback
    async def _async_reload_entry(*args: Any, **kwargs: Any) -> None:
        # Prevent reloads if we're not fully loaded yet
        if not hass.is_running:
            return

        hass.config_entries.async_update_entry(
            config_entry,
            data={**config_entry.data, "entity_ts": dt_util.utcnow()},
        )

    @callback
    async def _async_registry_updated(
        event: (
            Event[EventEntityRegistryUpdatedData]
            | Event[EventDeviceRegistryUpdatedData]
        ),
    ) -> None:
        """Reload integration when entity registry is updated."""

        area_data: dict[str, Any] = dict(config_entry.data)
        if config_entry.options:
            area_data.update(config_entry.options)

        # Check if disabled
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

        await _async_reload_entry()

    async def _async_setup_integration(*args: Any, **kwargs: Any) -> None:
        """Load integration when Hass has finished starting."""
        _LOGGER.debug("Setting up entry for %s", config_entry.data[ATTR_NAME])

        magic_area: MagicArea | None = get_magic_area_for_config_entry(
            hass, config_entry
        )
        assert magic_area is not None
        await magic_area.initialize()

        _LOGGER.debug(
            "%s: Magic Area (%s) created: %s",
            magic_area.name,
            magic_area.id,
            str(magic_area.config),
        )

        # Setup config uptate listener
        tracked_listeners: list[Callable] = []
        tracked_listeners.append(config_entry.add_update_listener(async_update_options))

        # Watch for area changes.
        if not magic_area.is_meta():
            tracked_listeners.append(
                hass.bus.async_listen(
                    EVENT_ENTITY_REGISTRY_UPDATED,
                    _async_registry_updated,
                    magic_area.make_entity_registry_filter(),
                )
            )
            tracked_listeners.append(
                hass.bus.async_listen(
                    EVENT_DEVICE_REGISTRY_UPDATED,
                    _async_registry_updated,
                    magic_area.make_device_registry_filter(),
                )
            )
            # Reload once Home Assistant has finished starting to make sure we have all entities.
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_reload_entry)

        config_entry.runtime_data = MagicAreasRuntimeData(
            area=magic_area,
            listeners=tracked_listeners,
        )

        # Setup platforms
        await hass.config_entries.async_forward_entry_setups(
            config_entry, magic_area.available_platforms()
        )

    await _async_setup_integration()

    return True


async def async_update_options(hass: HomeAssistant, config_entry: MagicAreasConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug(
        "Detected options change for entry %s, reloading", config_entry.entry_id
    )
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: MagicAreasConfigEntry) -> bool:
    """Unload a config entry."""

    area_data = config_entry.runtime_data
    area = area_data.area

    all_unloaded = await hass.config_entries.async_unload_platforms(
        config_entry, area.available_platforms()
    )

    for tracked_listener in area_data.listeners:
        tracked_listener()

    return all_unloaded


# Update config version
async def async_migrate_entry(hass: HomeAssistant, config_entry: MagicAreasConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.info(
        "%s: Migrating configuration from version %s.%s, current config: %s",
        config_entry.data[ATTR_NAME],
        config_entry.version,
        config_entry.minor_version,
        str(config_entry.data),
    )

    if config_entry.version > MagicConfigEntryVersion.MAJOR:
        # This means the user has downgraded from a future version
        _LOGGER.warning(
            "%s: Major version downgrade detection, skipping migration.",
            config_entry.data[ATTR_NAME],
        )

        return False

    hass.config_entries.async_update_entry(
        config_entry,
        minor_version=MagicConfigEntryVersion.MINOR,
        version=MagicConfigEntryVersion.MAJOR,
    )

    _LOGGER.info(
        "Migration to configuration version %s.%s successful: %s",
        config_entry.version,
        config_entry.minor_version,
        str(config_entry.data),
    )

    return True
