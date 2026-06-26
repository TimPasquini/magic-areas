"""Helpers package public API."""

from collections.abc import Sequence
from collections.abc import Awaitable, Callable
from datetime import datetime
import logging

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get
from homeassistant.helpers.event import async_call_later

from custom_components.magic_areas.helpers.area import (
    BasicArea,
    basic_area_from_floor,
    basic_area_from_meta,
    basic_area_from_object,
    build_area_config_for_config_entry,
)

_LOGGER = logging.getLogger(__name__)


class ReusableTimer:
    """Single active reusable timer with fixed delay and callback."""

    def __init__(
        self,
        hass: HomeAssistant,
        delay: float,
        callback: Callable[[datetime], Awaitable[None]],
    ) -> None:
        """Initialize the timer with a fixed delay and async callback."""
        self.hass = hass
        self._delay = delay
        self._callback = callback
        self._handle: CALLBACK_TYPE | None = None
        self._token: int = 0  # protects against race conditions

        _LOGGER.debug(
            "Initialized logger with delay=%d and callback=%s",
            self._delay,
            str(self._callback),
        )

    def start(self) -> None:
        """(Re)start the timer using the configured delay + callback."""
        self.cancel()
        self._token += 1
        token = self._token

        async def _scheduled(now: datetime) -> None:
            # Ignore if a newer start() happened after scheduling
            if token != self._token:
                _LOGGER.debug("Token mismatch. Skipping (%d/%d)", self._token, token)
                return
            self._handle = None
            await self._callback(now)
            _LOGGER.debug("Timer fired.")

        self._handle = async_call_later(self.hass, self._delay, _scheduled)
        _LOGGER.debug("Timer started.")

    def cancel(self) -> None:
        """Cancel the timer if running."""
        if self._handle:
            self._handle()  # async_call_later returns a cancel function
            self._handle = None
            _LOGGER.debug("Timer cancelled.")

    async def async_remove(self) -> None:
        """Cleanup when entity/integration is removed."""
        self.cancel()


def cleanup_removed_entries(
    hass: HomeAssistant, entity_list: Sequence[Entity], old_ids: list[dict[str, str]]
) -> None:
    """Clean up old magic entities."""
    new_ids = [entity.entity_id for entity in entity_list]
    _LOGGER.debug(
        "Checking for cleanup. Old entity list: %s, New entity list: %s",
        old_ids,
        new_ids,
    )
    entity_registry = entityreg_async_get(hass)
    for entity_dict in old_ids:
        entity_id = entity_dict[ATTR_ENTITY_ID]
        if entity_id in new_ids:
            continue
        _LOGGER.debug("Cleaning up old entity %s", entity_id)
        entity_registry.async_remove(entity_id)


__all__ = [
    "ReusableTimer",
    "BasicArea",
    "basic_area_from_floor",
    "basic_area_from_meta",
    "basic_area_from_object",
    "build_area_config_for_config_entry",
    "cleanup_removed_entries",
]
