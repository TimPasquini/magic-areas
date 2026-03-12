"""Config Flow for Magic Area."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from custom_components.magic_areas.config_flows.base import ConfigBase
from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler
from custom_components.magic_areas.config_keys.area import CONF_ID
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.core.discovery import (
    build_area_selector_options,
    create_area_config_entry,
    load_candidate_areas,
    lookup_area_by_display_name,
)
from custom_components.magic_areas.enums import MagicConfigEntryVersion
from custom_components.magic_areas.models import MagicAreasConfigEntry

_LOGGER = logging.getLogger(__name__)

EMPTY_ENTRY = [""]

class ConfigFlow(config_entries.ConfigFlow, ConfigBase, domain=DOMAIN):
    """Handle a config flow for Magic Areas."""

    VERSION = MagicConfigEntryVersion.MAJOR
    MINOR_VERSION = MagicConfigEntryVersion.MINOR

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Load all candidate areas (regular + meta)
        areas, reserved_ids = await load_candidate_areas(self.hass)

        if user_input is not None:
            # Look up area object by display name
            area_object = lookup_area_by_display_name(areas, user_input[CONF_NAME])

            # Fail if area name not found
            if not area_object:
                # noinspection PyTypeChecker
                return self.async_abort(reason="invalid_area")

            # Reserve unique name / already configured check
            await self.async_set_unique_id(area_object.id)
            self._abort_if_unique_id_configured()

            # Create area entry with default config
            config_entry = create_area_config_entry(area_object, reserved_ids)

            # noinspection PyTypeChecker
            return self.async_create_entry(title=area_object.name, data=config_entry)  # type: ignore[arg-type]

        # Filter out already-configured areas
        configured_areas = []
        entries = self._async_current_entries()
        for entry in entries:
            if entry.data.get(CONF_ID):
                configured_areas.append(entry.data.get(CONF_ID))

        available_areas = [area for area in areas if area.id not in configured_areas]

        if not available_areas:
            # noinspection PyTypeChecker
            return self.async_abort(reason="no_more_areas")

        # Build selector options (regular areas first, meta areas last)
        available_area_names = build_area_selector_options(
            available_areas, reserved_ids
        )

        schema = vol.Schema({vol.Required(CONF_NAME): vol.In(available_area_names)})

        # noinspection PyTypeChecker
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: MagicAreasConfigEntry,
    ) -> "OptionsFlowHandler":
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)
