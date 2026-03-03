"""Selector builders for Magic Areas config flow.

This module provides reusable selector builders for creating consistent
form inputs across config and options flows.
"""

from typing import Any

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

from custom_components.magic_areas.config_keys import EMPTY_STRING


class NullableEntitySelector(EntitySelector):
    """Entity selector that supports null values.

    This extends the standard EntitySelector to allow None or empty string
    as valid selections, useful for optional entity fields.
    """

    def __call__(self, data: Any) -> Any:
        """Validate the passed selection, if passed."""
        if data in (None, ""):
            return data

        return super().__call__(data)  # type: ignore[misc]


def build_selector_boolean() -> BooleanSelector:
    """Build a boolean toggle selector.

    Returns:
        BooleanSelector configured with default settings

    """
    return BooleanSelector(BooleanSelectorConfig())


def build_selector_select(
    options: list | None = None,
    multiple: bool = False,
    translation_key: str = EMPTY_STRING,
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
    options: list | None = None,
    multiple: bool = False,
) -> NullableEntitySelector:
    """Build an entity selector with predefined entity list.

    Args:
        options: List of entity IDs to include in selector
        multiple: Whether to allow multiple entity selections

    Returns:
        NullableEntitySelector configured with provided entities

    """
    if not options:
        options = []

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
