"""Magic Areas component for Home Assistant."""

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_NAME
from homeassistant.core import HomeAssistant
from custom_components.magic_areas.coordinator import (
    MagicAreasCoordinator,
    attach_registry_listeners,
)
from custom_components.magic_areas.enums import MagicConfigEntryVersion
from custom_components.magic_areas.helpers import build_area_config_for_config_entry
from custom_components.magic_areas.migrations import apply_applicable_migrations
from custom_components.magic_areas.components import (
    MagicAreasConfigEntry,
    MagicAreasRuntimeData,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: MagicAreasConfigEntry
) -> bool:
    """Set up the component."""

    async def _async_setup_integration() -> bool:
        """Load integration when Hass has finished starting."""
        _LOGGER.debug("Setting up entry for %s", config_entry.data[ATTR_NAME])

        # Build AreaConfig directly from registry (coordinator's primary config source)
        area_config = build_area_config_for_config_entry(hass, config_entry)
        if area_config is None:
            _LOGGER.error(
                "Failed to build area config for entry %s",
                config_entry.entry_id,
            )
            return False

        _LOGGER.debug(
            "%s: Magic Area (%s) created: %s",
            area_config.name,
            area_config.id,
            str(area_config.config),
        )

        # Setup config update listener
        tracked_listeners: list[Callable[[], None]] = [
            config_entry.add_update_listener(async_update_options)
        ]

        # Watch for area changes.
        if not area_config.is_meta():
            attach_registry_listeners(
                hass, config_entry, area_config, tracked_listeners
            )

        coordinator = MagicAreasCoordinator(hass, area_config, config_entry)
        if config_entry.state is ConfigEntryState.SETUP_IN_PROGRESS:
            await coordinator.async_config_entry_first_refresh()
        else:
            await coordinator.async_refresh()

        config_entry.runtime_data = MagicAreasRuntimeData(
            coordinator=coordinator,
            listeners=tracked_listeners,
        )

        from custom_components.magic_areas.coordinator import (
            async_reconcile_managed_adaptive_lighting,
            async_reconcile_managed_surfaces,
        )
        from custom_components.magic_areas.features.dispatch import (
            collect_feature_managed_adaptive_lighting_configs,
            collect_feature_managed_surfaces,
        )
        from custom_components.magic_areas.features.registry import FEATURE_REGISTRY

        if coordinator.data:
            await async_reconcile_managed_surfaces(
                hass=hass,
                owner_entry_id=config_entry.entry_id,
                desired_surfaces=collect_feature_managed_surfaces(
                    registry=FEATURE_REGISTRY,
                    data=coordinator.data,
                    area_config=area_config,
                    logger=_LOGGER,
                ),
            )
            await async_reconcile_managed_adaptive_lighting(
                hass=hass,
                area_id=area_config.id,
                desired_configs=collect_feature_managed_adaptive_lighting_configs(
                    registry=FEATURE_REGISTRY,
                    data=coordinator.data,
                    area_config=area_config,
                    logger=_LOGGER,
                ),
            )

        # Setup platforms (get from coordinator data after refresh)
        platforms = (
            coordinator.data.area_config.available_platforms()
            if coordinator.data
            else []
        )
        await hass.config_entries.async_forward_entry_setups(config_entry, platforms)
        return True

    return await _async_setup_integration()


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

    from_version = (config_entry.version, config_entry.minor_version)
    to_version = (
        int(MagicConfigEntryVersion.MAJOR),
        int(MagicConfigEntryVersion.MINOR),
    )

    migrated_count = await apply_applicable_migrations(
        hass,
        config_entry,
        from_version=from_version,
        to_version=to_version,
    )
    _LOGGER.debug(
        "%s: Applied %s migration(s) from %s to %s",
        config_entry.data[ATTR_NAME],
        migrated_count,
        from_version,
        to_version,
    )

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
