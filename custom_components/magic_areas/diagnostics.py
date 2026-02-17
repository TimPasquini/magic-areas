"""Diagnostics support for Magic Areas."""

from enum import Enum
from typing import Any

import homeassistant.components.diagnostics
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get

from custom_components.magic_areas.attrs import ATTR_STATES
from custom_components.magic_areas.config_keys import CONF_ID, CONF_NAME
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.models import MagicAreasConfigEntry

TO_REDACT = {CONF_ID, CONF_NAME}


def _get_area_states(hass: HomeAssistant, area_id: str) -> list[str]:
    """Read current area states from the published presence tracking entity."""
    entity_registry = entityreg_async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        BINARY_SENSOR_DOMAIN,
        DOMAIN,
        f"presence_tracking_{area_id}_area_state",
    )
    if entity_id:
        state = hass.states.get(entity_id)
        if state and ATTR_STATES in state.attributes:
            return [
                str(s.value) if isinstance(s, Enum) else str(s)
                for s in state.attributes[ATTR_STATES]
            ]
    return []


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
    return {
        "entry": homeassistant.components.diagnostics.async_redact_data(
            entry.as_dict(), TO_REDACT
        ),
        "area": {
            "name": data.area_config.name,
            "id": data.area_config.id,
            "type": data.area_config.area_type,
            "states": _get_area_states(hass, data.area_config.id),
            "meta": data.area_config.is_meta(),
            "entities": data.entities,
            "magic_entities": data.magic_entities,
            "config": homeassistant.components.diagnostics.async_redact_data(
                data.config, TO_REDACT
            ),
            "updated_at": data.updated_at.isoformat(),
        },
    }
