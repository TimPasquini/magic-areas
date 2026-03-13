"""Listener registry for Home Assistant entity lifecycle management.

Provides safe listener lifecycle management: named registration,
debug logging, and error-tolerant cleanup. Any entity that registers
HA listeners (state change events, dispatcher signals, timers) can
use this instead of bare async_on_remove() calls.

No Home Assistant entity classes are imported — this is pure lifecycle
management.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)
_EXPECTED_LISTENER_CLEANUP_ERRORS = (
    KeyError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
)


class ListenerRegistry:
    """Track and clean up event listeners with named debugging.

    Provides safe listener lifecycle management: named registration,
    debug logging, and error-tolerant cleanup. Any entity that registers
    HA listeners (state change events, dispatcher signals, timers) can
    use this instead of bare async_on_remove() calls.

    Usage:
        registry = ListenerRegistry(logger_name="custom_component.my_entity")
        remove_fn = async_track_state_change(hass, entity_id, callback)
        registry.track("state_change_tracking", remove_fn)
        # ... later in cleanup ...
        registry.cleanup()
    """

    def __init__(self, logger_name: str | None = None) -> None:
        """Initialize the listener registry.

        Args:
            logger_name: Optional logger name for debug output.
                If not provided, uses module-level logger.

        """
        self._listeners: list[tuple[str, Callable[[], None]]] = []
        self._logger = logging.getLogger(logger_name) if logger_name else _LOGGER

    @property
    def count(self) -> int:
        """Return number of tracked listeners."""
        return len(self._listeners)

    def track(self, name: str, remove_fn: Callable[[], None]) -> None:
        """Register a listener for later cleanup.

        Args:
            name: Descriptive name for debugging (e.g., "member_state_tracking").
            remove_fn: Function to call to remove the listener.

        """
        self._listeners.append((name, remove_fn))
        self._logger.debug(
            "Tracked listener: %s (total: %d)", name, len(self._listeners)
        )

    def cleanup(self) -> None:
        """Remove all tracked listeners with error handling.

        Iterates all registered listeners, calls each remove callback,
        logs errors without raising, then clears the list.
        """
        if not self._listeners:
            self._logger.debug("No listeners to clean up")
            return

        self._logger.debug("Cleaning up %d listeners", len(self._listeners))

        for name, remove_fn in self._listeners:
            try:
                remove_fn()
                self._logger.debug("Cleaned up listener: %s", name)
            except _EXPECTED_LISTENER_CLEANUP_ERRORS as err:
                self._logger.exception("Error cleaning up listener '%s': %s", name, err)

        self._listeners.clear()
