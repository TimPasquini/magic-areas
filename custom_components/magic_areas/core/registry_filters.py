"""Registry filter factory functions for area reload detection."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.device_registry import EventDeviceRegistryUpdatedData
from homeassistant.helpers.device_registry import async_get as devicereg_async_get
from homeassistant.helpers.entity_registry import EventEntityRegistryUpdatedData
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get

from custom_components.magic_areas.components import (
    MAGIC_DEVICE_ID_PREFIX,
    MAGICAREAS_UNIQUEID_PREFIX,
)

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant


def make_entity_registry_filter(
    hass: "HomeAssistant", area_id: str, config_entry_id: str
) -> Callable[[EventEntityRegistryUpdatedData], bool]:
    """Create entity register filter for an area.

    Args:
        hass: Home Assistant instance
        area_id: Area ID to filter for
        config_entry_id: Config entry ID to ignore

    Returns:
        Filter function that identifies relevant entity registry updates.

    """

    @callback
    def _entity_registry_filter(event_data: EventEntityRegistryUpdatedData) -> bool:
        """Filter entity registry events relevant to this area."""
        entity_id = event_data["entity_id"]

        # Ignore our own stuff
        _, entity_part = entity_id.split(".")
        if entity_part.startswith(MAGICAREAS_UNIQUEID_PREFIX):
            return False

        # Note: Throttling based on timestamp was removed as it prevented necessary reloads
        # during testing and the reload() method on MagicArea has its own throttle check

        entity_registry = entityreg_async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)

        if event_data["action"] == "update" and "area_id" in event_data["changes"]:
            # Removed from our area
            if event_data["changes"].get("area_id") == area_id:
                return True

            # Is from our area
            if entity_entry and entity_entry.area_id == area_id:
                return True

            return False

        if event_data["action"] in ("create", "remove"):
            # Is from our area
            if entity_entry and entity_entry.area_id == area_id:
                return True

        return False

    return _entity_registry_filter


def make_device_registry_filter(
    hass: "HomeAssistant", area_id: str, config_entry_id: str
) -> Callable[[EventDeviceRegistryUpdatedData], bool]:
    """Create device register filter for an area.

    Args:
        hass: Home Assistant instance
        area_id: Area ID to filter for
        config_entry_id: Config entry ID to ignore

    Returns:
        Filter function that identifies relevant device registry updates.

    """

    @callback
    def _device_registry_filter(event_data: EventDeviceRegistryUpdatedData) -> bool:
        """Filter device registry events relevant to this area."""
        # Ignore our own stuff
        if event_data["device_id"].startswith(MAGIC_DEVICE_ID_PREFIX):
            return False

        # Note: Throttling based on timestamp was removed as it prevented necessary reloads
        # during testing and the reload() method on MagicArea has its own throttle check

        if event_data["action"] == "update" and "area_id" in event_data["changes"]:
            # Removed from our area
            if event_data["changes"].get("area_id") == area_id:
                return True

        # Check if device is currently in our area
        device_registry = devicereg_async_get(hass)
        device_entry = device_registry.async_get(event_data["device_id"])

        # Is from our area
        if device_entry and device_entry.area_id == area_id:
            return True

        return False

    return _device_registry_filter
