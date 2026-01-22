"""Diagnostics support for Magic Areas."""

from typing import Any

import homeassistant.components.diagnostics
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.config_keys import CONF_ID, CONF_NAME
from custom_components.magic_areas.models import MagicAreasConfigEntry

TO_REDACT = {CONF_ID, CONF_NAME}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MagicAreasConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = entry.runtime_data
    if runtime_data.coordinator.data is None:
        await runtime_data.coordinator.async_refresh()
    data = runtime_data.coordinator.data
    if data is None:
        return {
            "entry": homeassistant.components.diagnostics.async_redact_data(
                entry.as_dict(), TO_REDACT
            ),
            "area": {"error": "Coordinator data unavailable"},
        }
    area = data.area

    return {
        "entry": homeassistant.components.diagnostics.async_redact_data(
            entry.as_dict(), TO_REDACT
        ),
        "area": {
            "name": area.name,
            "id": area.id,
            "type": area.area_type,
            "states": area.states,
            "meta": area.is_meta(),
            "entities": data.entities,
            "magic_entities": data.magic_entities,
            "config": homeassistant.components.diagnostics.async_redact_data(
                data.config, TO_REDACT
            ),
            "updated_at": data.updated_at.isoformat(),
        },
    }
