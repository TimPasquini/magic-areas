"""Presence tracking state machine helpers for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.magic_areas.policy import INVALID_STATES
from custom_components.magic_areas.core.occupancy import AreaOccupancyTracker

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PresenceUpdate:
    """Result of a presence tracker update."""

    new_states: set[str]
    lost_states: set[str]
    current_states: set[str]
    cancel_timeout: bool
    request_timeout: float | None


class PresenceTracker:
    """Pure-ish presence tracker with HA state input/output injected."""

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        area_name: str,
        config: dict[str, Any],
        is_meta: bool,
    ) -> None:
        """Initialize tracker with HA access and area context."""
        self._hass = hass
        self._area_name = area_name
        self._tracker = AreaOccupancyTracker(config=config, is_meta=is_meta)

    @property
    def tracker(self) -> AreaOccupancyTracker:
        """Return the underlying occupancy tracker."""
        return self._tracker

    def handle_sensor_state_change(
        self,
        *,
        entity_id: str,
        to_state: str | None,
        ignore_non_state_change: bool,
        old_state: str | None,
    ) -> bool:
        """Return True when caller should update state.

        Handles invalid states and non-state changes.
        """
        if to_state is None:
            return False

        if ignore_non_state_change and old_state is not None and to_state == old_state:
            return False

        _LOGGER.debug(
            "%s: sensor '%s' changed to {%s}",
            self._area_name,
            entity_id,
            to_state,
        )

        if to_state in INVALID_STATES:
            _LOGGER.debug(
                "%s: sensor '%s' has invalid state %s",
                self._area_name,
                entity_id,
                to_state,
            )
            return False

        if to_state and to_state not in self._tracker.valid_on_states():
            _LOGGER.debug("Setting last non-normal time %s", entity_id)
            self._tracker.record_sensor_off(dt_util.utcnow())
            return True

        return True

    def handle_secondary_state_change(
        self,
        *,
        entity_id: str,
        to_state: str | None,
    ) -> bool:
        """Return True when caller should update state."""
        if to_state is None:
            return False

        _LOGGER.debug(
            "%s: Secondary state change: entity '%s' changed to %s",
            self._area_name,
            entity_id,
            to_state,
        )

        if to_state in INVALID_STATES:
            _LOGGER.debug(
                "%s: sensor '%s' has invalid state %s",
                self._area_name,
                entity_id,
                to_state,
            )
            return False

        return True

    def update(
        self,
        *,
        sensor_ids: list[str],
        secondary_states: list[str],
        keep_only: list[str],
        now: datetime | None = None,
    ) -> PresenceUpdate:
        """Run tracker update using live HA state for given sensors."""
        moment = now if isinstance(now, datetime) else dt_util.utcnow()

        sensor_states: dict[str, str | None] = {}
        for sensor_id in sensor_ids:
            try:
                entity = self._hass.states.get(sensor_id)
                sensor_states[sensor_id] = entity.state if entity else None
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOGGER.error(
                    "%s: Error getting entity state for '%s': %s",
                    self._area_name,
                    sensor_id,
                    err,
                )
                sensor_states[sensor_id] = None

        update = self._tracker.update(sensor_states, secondary_states, keep_only, moment)

        return PresenceUpdate(
            new_states=update.new_states,
            lost_states=update.lost_states,
            current_states=set(update.current_states),
            cancel_timeout=update.cancel_timeout,
            request_timeout=update.request_timeout,
        )

    def record_timeout_set(self) -> None:
        """Record that a timeout has been scheduled."""
        self._tracker.on_timeout_set()

    def record_timeout_cleared(self) -> None:
        """Record that a timeout has been cleared."""
        self._tracker.on_timeout_cleared()
