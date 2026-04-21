"""Selector builders for Magic Areas config flow.

This module provides reusable selector builders for creating consistent
form inputs across config and options flows.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

import voluptuous as vol
from homeassistant.components.climate.const import ATTR_PRESET_MODES
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    ObjectSelector,
    ObjectSelectorConfig,
)

from custom_components.magic_areas.enums import SelectorTranslationKeys

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.selector import SelectSelector


class NullableEntitySelector(EntitySelector):
    """Entity selector that supports null values.

    This extends the standard EntitySelector to allow None or empty string
    as valid selections, useful for optional entity fields.
    """

    def __call__(self, data: object) -> str | list[str] | None:  # type: ignore[override]
        """Validate the passed selection, if passed."""
        if data is None:
            return None
        if data == "":
            return ""

        return super().__call__(data)


def build_selector_boolean() -> BooleanSelector:
    """Build a boolean toggle selector.

    Returns:
        BooleanSelector configured with default settings

    """
    return BooleanSelector(BooleanSelectorConfig())


def build_selector_select(
    options: list[str] | None = None,
    multiple: bool = False,
    translation_key: str = "",
) -> SelectSelector:
    """Build a select dropdown selector.

    Args:
        options: List of options to display in dropdown
        multiple: Whether to allow multiple selections
        translation_key: Translation key for option labels

    Returns:
        SelectSelector configured with provided options

    """
    if not options:
        options = []

    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            multiple=multiple,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key=translation_key,
        )
    )


def build_selector_entity_simple(
    options: list[str] | None = None,
    multiple: bool = False,
) -> NullableEntitySelector:
    """Build an entity selector with predefined entity list.

    Args:
        options: List of entity IDs to include in selector
        multiple: Whether to allow multiple entity selections

    Returns:
        NullableEntitySelector configured with provided entities

    """
    if not isinstance(options, list):
        options = []
    else:
        options = [entity_id for entity_id in options if isinstance(entity_id, str)]

    return NullableEntitySelector(
        EntitySelectorConfig(include_entities=options, multiple=multiple)
    )


def build_selector_number(
    *,
    min_value: float = 0,
    max_value: float = 9999,
    mode: NumberSelectorMode = NumberSelectorMode.BOX,
    step: float = 1,
    unit_of_measurement: str = "seconds",
) -> NumberSelector:
    """Build a number input selector.

    Args:
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        mode: Display mode (BOX or SLIDER)
        step: Increment step size
        unit_of_measurement: Unit suffix to display

    Returns:
        NumberSelector configured with provided constraints

    """
    return NumberSelector(
        NumberSelectorConfig(
            min=min_value,
            max=max_value,
            mode=mode,
            step=step,
            unit_of_measurement=unit_of_measurement,
        )
    )


def build_selector_object() -> ObjectSelector:
    """Build a generic object selector for structured JSON-style payloads."""
    return ObjectSelector(ObjectSelectorConfig())


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


class SelectSelectorBuilder(Protocol):
    """Callable contract for building select selectors."""

    def __call__(
        self,
        options: list[str] | None = None,
        multiple: bool = False,
        translation_key: str = "",
    ) -> SelectSelector:
        """Return a configured select selector."""


def build_climate_preset_selectors_and_validators(
    hass: HomeAssistant,
    climate_entity_id: str | None,
    selector_builder: SelectSelectorBuilder,
    preset_config_keys: Sequence[str],
) -> tuple[dict[str, SelectSelector], dict[str, vol.In]]:
    """Build dynamic selectors and validators for climate preset selection."""
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
    available_preset_modes = [""] + list(preset_modes)

    selectors = {
        key: selector_builder(
            available_preset_modes,
            translation_key=SelectorTranslationKeys.CLIMATE_PRESET_LIST,
        )
        for key in preset_config_keys
    }
    dynamic_validators = {
        key: vol.In(available_preset_modes) for key in preset_config_keys
    }

    return selectors, dynamic_validators
