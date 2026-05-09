"""HA executor for Adaptive Lighting coordination service intents."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.control_intents.adaptive_lighting import (
    AdaptiveLightingServiceIntent,
)


async def async_execute_adaptive_lighting_intents(
    hass: HomeAssistant,
    intents: Iterable[AdaptiveLightingServiceIntent],
) -> None:
    """Execute Adaptive Lighting coordination intents through HA services."""
    for intent in intents:
        if not hass.services.has_service(intent.domain, intent.service):
            continue
        await hass.services.async_call(
            intent.domain,
            intent.service,
            intent.data,
            blocking=True,
        )


__all__ = ["async_execute_adaptive_lighting_intents"]
