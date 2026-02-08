"""Dynamic schema builders for feature configuration.

This module provides helper functions to build feature-specific schemas
dynamically based on entity capabilities, registry data, or other runtime state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get

from custom_components.magic_areas.config_keys import EMPTY_STRING
from custom_components.magic_areas.enums import SelectorTranslationKeys

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.selector import SelectSelector


class ClimatePresetBuilderError(Exception):
    """Base exception for climate preset builder errors."""

    pass


class NoEntitySelectedError(ClimatePresetBuilderError):
    """Raised when no climate entity is provided."""

    pass


class InvalidEntityError(ClimatePresetBuilderError):
    """Raised when climate entity is not found in registry."""

    pass


class NoPresetSupportError(ClimatePresetBuilderError):
    """Raised when climate entity does not support presets."""

    pass


def build_climate_preset_selectors_and_validators(
    hass: HomeAssistant,
    climate_entity_id: str | None,
    selector_builder: Any,  # ConfigBase._build_selector_select method
    preset_config_keys: tuple[str, str, str, str],
) -> tuple[dict[str, SelectSelector], dict[str, vol.In]]:
    """Build dynamic selectors and validators for climate preset selection.

    Queries the climate entity's capabilities to extract available preset modes,
    then builds selectors and validators for each state preset configuration field.

    Args:
        hass: Home Assistant instance
        climate_entity_id: Entity ID of the climate device to query
        selector_builder: Function to build select selectors (from ConfigBase)
        preset_config_keys: Tuple of (CLEAR, OCCUPIED, SLEEP, EXTENDED) config keys

    Returns:
        Tuple of (selectors dict, validators dict)

    Raises:
        NoEntitySelectedError: If climate_entity_id is None or empty
        InvalidEntityError: If entity not found in registry
        NoPresetSupportError: If entity does not support preset modes

    Example:
        >>> selectors, validators = build_climate_preset_selectors_and_validators(
        ...     hass,
        ...     "climate.living_room",
        ...     config_base._build_selector_select,
        ...     (CONF_CLIMATE_CONTROL_PRESET_CLEAR, ...),
        ... )
    """
    if not climate_entity_id:
        raise NoEntitySelectedError("No climate entity selected")

    entity_registry = entityreg_async_get(hass)
    entity_object = entity_registry.async_get(climate_entity_id)

    if not entity_object:
        raise InvalidEntityError(f"Climate entity not found: {climate_entity_id}")

    caps = entity_object.capabilities or {}
    preset_modes = caps.get(ATTR_PRESET_MODES)

    if not preset_modes:
        raise NoPresetSupportError(
            f"Climate entity does not support presets: {climate_entity_id}"
        )

    # Build list of available preset modes (with empty option for "no preset")
    available_preset_modes = [EMPTY_STRING] + list(preset_modes)

    # Unpack config keys
    (
        conf_preset_clear,
        conf_preset_occupied,
        conf_preset_sleep,
        conf_preset_extended,
    ) = preset_config_keys

    # Build selectors for each preset type
    selectors = {
        conf_preset_clear: selector_builder(
            available_preset_modes,
            translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
        ),
        conf_preset_occupied: selector_builder(
            available_preset_modes,
            translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
        ),
        conf_preset_sleep: selector_builder(
            available_preset_modes,
            translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
        ),
        conf_preset_extended: selector_builder(
            available_preset_modes,
            translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
        ),
    }

    # Build validators for each preset type
    dynamic_validators = {
        conf_preset_clear: vol.In(available_preset_modes),
        conf_preset_occupied: vol.In(available_preset_modes),
        conf_preset_sleep: vol.In(available_preset_modes),
        conf_preset_extended: vol.In(available_preset_modes),
    }

    return selectors, dynamic_validators
