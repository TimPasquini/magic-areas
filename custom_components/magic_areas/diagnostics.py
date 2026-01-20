"""Diagnostics support for Magic Areas."""

from typing import Any

import homeassistant.components.diagnostics
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import CONF_ID, CONF_NAME
from custom_components.magic_areas.models import MagicAreasConfigEntry

TO_REDACT = {CONF_ID, CONF_NAME}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MagicAreasConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    area = entry.runtime_data.area

    return {
        "entry": homeassistant.components.diagnostics.async_redact_data(entry.as_dict(), TO_REDACT),
        "area": {
            "name": area.name,
            "id": area.id,
            "type": area.area_type,
            "states": area.states,
            "meta": area.is_meta(),
            "entities": area.entities,
            "magic_entities": area.magic_entities,
            "config": homeassistant.components.diagnostics.async_redact_data(area.config, TO_REDACT),
        },
    }