"""Helper functions for config and options flows.

This module provides reusable utility functions for configuration flows,
including error handling and validation helpers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

import voluptuous as vol

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


def errors_from_validation(validation: vol.MultipleInvalid) -> dict[str, str]:
    """Convert voluptuous validation errors to Home Assistant error dict format.

    Args:
        validation: The voluptuous MultipleInvalid exception containing errors

    Returns:
        Dict mapping field names to error strings, suitable for use with
        Home Assistant's async_show_form errors parameter

    Example:
        >>> try:
        ...     schema(user_input)
        ... except vol.MultipleInvalid as e:
        ...     errors = errors_from_validation(e)
        ...     return self.async_show_form(..., errors=errors)
    """
    return {
        str(error.path[0]): str(error.msg)
        for error in validation.errors
        if isinstance(error, vol.Invalid) and error.path
    }


async def handle_step_validation(
    *,
    user_input: dict[str, Any] | None,
    schema: vol.Schema,
    area_name: str,
    step_name: str,
    area_options: dict[str, Any],
    config_key: str | None = None,
    on_success: Callable[[], Any],
) -> tuple[dict[str, str], bool]:
    """Handle validation for a config flow step.

    This extracts the common validation/save pattern used across all flow steps.

    Args:
        user_input: User input from form submission (or None if initial display)
        schema: Voluptuous schema to validate against
        area_name: Name of area being configured (for logging)
        step_name: Name of step (for logging)
        area_options: Dict to update with validated input
        config_key: Optional key to update within area_options (if None, updates root)
        on_success: Callback to execute after successful validation

    Returns:
        Tuple of (errors dict, should_continue)
        - If should_continue is False, caller should continue to form display
        - If should_continue is True, validation succeeded and on_success was called

    Example:
        >>> errors, handled = await handle_step_validation(
        ...     user_input=user_input,
        ...     schema=MY_SCHEMA,
        ...     area_name=self.area.name,
        ...     step_name="my_step",
        ...     area_options=self.area_options,
        ...     on_success=lambda: self.async_step_show_menu(),
        ... )
        >>> if handled:
        ...     return await on_success()  # Validation succeeded, return to menu
    """
    errors: dict[str, str] = {}

    if user_input is None:
        return errors, False

    _LOGGER.debug(
        "OptionsFlow: Validating area %s %s config: %s",
        area_name,
        step_name,
        str(user_input),
    )

    try:
        validated = schema(user_input)

        # Update area_options (either root or specific key)
        if config_key:
            if config_key not in area_options:
                area_options[config_key] = {}
            area_options[config_key].update(validated)
        else:
            area_options.update(validated)

        _LOGGER.debug(
            "OptionsFlow: Saving area %s %s config: %s",
            area_name,
            step_name,
            str(area_options),
        )

        return errors, True

    except vol.MultipleInvalid as validation:
        errors = errors_from_validation(validation)
        _LOGGER.debug(
            "OptionsFlow: Found the following errors for area %s: %s",
            area_name,
            str(errors),
        )
        return errors, False

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        _LOGGER.warning(
            "OptionsFlow: Unexpected error caught on area %s: %s",
            area_name,
            str(e),
        )
        return errors, False
