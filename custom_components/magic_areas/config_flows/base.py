"""Base class for config flow."""

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from custom_components.magic_areas.config_flows.helpers import errors_from_validation
from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)


class ConfigBase:
    """Base class for config flow."""

    config_entry: MagicAreasConfigEntry | None = None

    def _build_options_schema(
        self,
        options: list,
        *,
        saved_options: Mapping[str, Any] | None = None,
        dynamic_validators: dict | None = None,
        selectors: dict | None = None,
    ) -> vol.Schema:
        """Build schema for configuration options."""
        _LOGGER.debug(
            "ConfigFlow: Building schema from options: %s - dynamic_validators: %s",
            str(options),
            str(dynamic_validators),
        )

        if not dynamic_validators:
            dynamic_validators = {}

        if not selectors:
            selectors = {}

        if saved_options is None and self.config_entry:
            saved_options = self.config_entry.options

        _LOGGER.debug(
            "ConfigFlow: Data for pre-populating fields: %s", str(saved_options)
        )

        schema = {
            vol.Optional(
                name,
                description={
                    "suggested_value": (
                        saved_options.get(name)
                        if saved_options and saved_options.get(name) is not None
                        else default
                    )
                },
                default=default,
            ): (
                selectors[name]
                if name in selectors
                else dynamic_validators.get(name, validation)
            )
            for name, default, validation in options
        }

        _LOGGER.debug("ConfigFlow: Built schema: %s", str(schema))

        return vol.Schema(schema)

    @staticmethod
    def _errors_from_validation(
        validation: vol.MultipleInvalid,
    ) -> dict[str, str]:
        """Return errors mapping from voluptuous validation."""
        return errors_from_validation(validation)
