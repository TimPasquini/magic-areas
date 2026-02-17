"""Config Flow for Magic Area."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.area_registry import async_get as areareg_async_get
from homeassistant.helpers.floor_registry import async_get as floorreg_async_get
from homeassistant.util import slugify

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.config_flows.base import ConfigBase
from custom_components.magic_areas.config_flows.options_flow import OptionsFlowHandler
from custom_components.magic_areas.config_keys import (
    CONF_ID,
    CONF_TYPE,
)
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.area_state import MetaAreaType
from custom_components.magic_areas.enums import MagicConfigEntryVersion
from custom_components.magic_areas.helpers.area import (
    basic_area_from_floor,
    basic_area_from_meta,
    basic_area_from_object,
)
from custom_components.magic_areas.models import MagicAreasConfigEntry
from custom_components.magic_areas.schemas.area import (
    DOMAIN_SCHEMA,
)

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

        reserved_names = []
        non_floor_meta_areas = [
            meta_area_type
            for meta_area_type in MetaAreaType
            if meta_area_type != MetaAreaType.FLOOR
        ]

        # Load registries
        area_registry = areareg_async_get(self.hass)
        floor_registry = floorreg_async_get(self.hass)
        areas = [
            basic_area_from_object(area) for area in area_registry.async_list_areas()
        ]
        area_ids = [area.id for area in areas]

        # Load floors meta-aras
        floors = floor_registry.async_list_floors()

        for floor in floors:
            # Prevent conflicts between meta areas and existing areas
            if floor.floor_id in area_ids:
                _LOGGER.warning(
                    "ConfigFlow: You have an area with a reserved name '%s'. This will prevent from using the %s Meta area.",
                    floor.floor_id,
                    floor.floor_id,
                )
                continue

            _LOGGER.debug(
                "ConfigFlow: Appending Meta Area %s to the list of areas",
                floor.floor_id,
            )
            area = basic_area_from_floor(floor)
            reserved_names.append(area.id)
            areas.append(area)

        # Add standard meta areas to area list
        for meta_area in non_floor_meta_areas:
            # Prevent conflicts between meta areas and existing areas
            if meta_area in area_ids:
                _LOGGER.warning(
                    "ConfigFlow: You have an area with a reserved name '%s'. This will prevent from using the %s Meta area.",
                    meta_area,
                    meta_area,
                )
                continue

            _LOGGER.debug(
                "ConfigFlow: Appending Meta Area %s to the list of areas", meta_area
            )
            area = basic_area_from_meta(meta_area)
            reserved_names.append(area.id)
            areas.append(area)

        if user_input is not None:
            # Look up area object by name
            area_object = None

            for area in areas:
                area_name = user_input[CONF_NAME]

                # Handle meta area name append
                if area_name.startswith("(Meta)"):
                    area_name = " ".join(area_name.split(" ")[1:])

                if area.name == area_name:
                    area_object = area
                    break

            # Fail if area name not found,
            # this should never happen in ideal conditions.
            if not area_object:
                # noinspection PyTypeChecker
                return self.async_abort(reason="invalid_area")

            # Reserve unique name / already configured check
            await self.async_set_unique_id(area_object.id)
            self._abort_if_unique_id_configured()

            # Create area entry with default config
            config_entry = DOMAIN_SCHEMA({f"{area_object.id}": {}})[area_object.id]
            extra_opts = {CONF_NAME: area_object.name, CONF_ID: area_object.id}
            config_entry.update(extra_opts)

            # Handle Meta area
            if slugify(area_object.id) in reserved_names:
                _LOGGER.debug(
                    "ConfigFlow: Meta area %s found, setting correct type.",
                    area_object.id,
                )
                config_entry.update({CONF_TYPE: AreaType.META})

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

        # Slight ordering trick so Meta areas are at the bottom
        available_area_names = sorted(
            [area.name for area in available_areas if area.id not in reserved_names]
        )
        available_area_names.extend(
            sorted(
                [
                    f"(Meta) {area.name}"
                    for area in available_areas
                    if area.id in reserved_names
                ]
            )
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
