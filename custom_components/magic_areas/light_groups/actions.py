"""Action helpers for Magic Areas light groups."""

from __future__ import annotations

from typing import Any

from homeassistant.components.group.light import FORWARDED_ATTRIBUTES
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant


def get_active_lights(hass: HomeAssistant, entity_ids: list[str]) -> list[str]:
    """Return list of lights that are on."""
    active_lights: list[str] = []
    for entity_id in entity_ids:
        light_state = hass.states.get(entity_id)
        if not light_state:
            continue
        if light_state.state == "on":
            active_lights.append(entity_id)
    return active_lights


async def forward_turn_on(
    hass: HomeAssistant, area_name: str, entity_ids: list[str], **kwargs: Any
) -> None:
    """Forward the turn_on command to active lights in the group."""
    data = {key: value for key, value in kwargs.items() if key in FORWARDED_ATTRIBUTES}

    active_lights = get_active_lights(hass, entity_ids) or entity_ids
    data[ATTR_ENTITY_ID] = active_lights

    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        data,
        blocking=True,
        context=kwargs.get("context"),
    )
