"""Magic Areas component for Home Assistant."""

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_NAME, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import dispatcher_send
from custom_components.magic_areas.coordinator import MagicAreasCoordinator
from custom_components.magic_areas.core.identity_migration import (
    async_migrate_unique_ids,
)
from custom_components.magic_areas.core.registry_reload import (
    attach_registry_listeners,
)
from custom_components.magic_areas.enums import MagicAreasEvents, MagicConfigEntryVersion
from custom_components.magic_areas.helpers.area import (
    build_area_config_for_config_entry,
)
from custom_components.magic_areas.models import (
    MagicAreasConfigEntry,
    MagicAreasRuntimeData,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> bool:
    """Set up the component."""

    async def _async_setup_integration(*args: Any, **kwargs: Any) -> None:
        """Load integration when Hass has finished starting."""
        _LOGGER.debug("Setting up entry for %s", config_entry.data[ATTR_NAME])

        # Build AreaConfig directly from registry (coordinator's primary config source)
        area_config = build_area_config_for_config_entry(hass, config_entry)
        assert area_config is not None

        _LOGGER.debug(
            "%s: Magic Area (%s) created: %s",
            area_config.name,
            area_config.id,
            str(area_config.config),
        )

        # For regular areas, dispatch AREA_LOADED so meta-area coordinators
        # know to refresh. Meta areas handle their own reload subscription.
        if not area_config.is_meta():
            _area_type = area_config.area_type
            _floor_id = area_config.floor_id
            _area_id = area_config.id

            @callback
            async def _async_notify_loaded(*args: Any, **kwargs: Any) -> None:
                dispatcher_send(
                    hass,
                    MagicAreasEvents.AREA_LOADED,
                    _area_type,
                    _floor_id,
                    _area_id,
                )

            if hass.is_running:
                hass.create_task(_async_notify_loaded())
            else:
                hass.bus.async_listen_once(
                    EVENT_HOMEASSISTANT_STARTED, _async_notify_loaded
                )

        # Setup config update listener
        tracked_listeners: list[Callable] = [
            config_entry.add_update_listener(async_update_options)
        ]

        # Watch for area changes.
        if not area_config.is_meta():
            attach_registry_listeners(hass, config_entry, area_config, tracked_listeners)

        coordinator = MagicAreasCoordinator(hass, area_config, config_entry)
        if config_entry.state is ConfigEntryState.SETUP_IN_PROGRESS:
            await coordinator.async_config_entry_first_refresh()
        else:
            await coordinator.async_refresh()

        config_entry.runtime_data = MagicAreasRuntimeData(
            coordinator=coordinator,
            listeners=tracked_listeners,
        )

        # Setup platforms (get from coordinator data after refresh)
        platforms = (
            coordinator.data.area_config.available_platforms()
            if coordinator.data
            else []
        )
        await hass.config_entries.async_forward_entry_setups(config_entry, platforms)

    await _async_setup_integration()

    return True


async def async_update_options(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> None:
    """Update options."""
    _LOGGER.debug(
        "Detected options change for entry %s, reloading", config_entry.entry_id
    )
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> bool:
    """Unload a config entry."""

    area_data = config_entry.runtime_data

    # Get platforms from coordinator data if available, otherwise build from config
    platforms = []
    if area_data.coordinator.data:
        platforms = area_data.coordinator.data.area_config.available_platforms()

    all_unloaded = await hass.config_entries.async_unload_platforms(
        config_entry, platforms
    )

    await area_data.coordinator.async_shutdown()

    for tracked_listener in area_data.listeners:
        tracked_listener()

    return all_unloaded


# Update config version
async def async_migrate_entry(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> bool:
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

    if config_entry.minor_version < MagicConfigEntryVersion.MINOR:
        await async_migrate_unique_ids(hass, config_entry)

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
