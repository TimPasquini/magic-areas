"""Wasp In A Box state machine for Magic Areas.

Encapsulates the temporal state logic for detecting motion (wasp) while a door
is open (box). The machine receives pre-built sensor state dicts and returns
WaspStateUpdate results — consistent with the existing policy pattern
(LightGroupPolicy, FanControlPolicy, ClimatePresetPolicy).

No Home Assistant entity classes are imported.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import STATE_OFF, STATE_ON


@dataclass(slots=True)
class WaspStateUpdate:
    """Result of a wasp-in-a-box state update cycle."""

    is_present: bool
    wasp_active: bool
    box_open: bool
    request_timer: float | None = None  # seconds, or None
    cancel_timer: bool = False


class WaspStateMachine:
    """State machine for door+motion presence coordination.

    Receives pre-built sensor state dicts (wasp sensors + box sensors),
    returns WaspStateUpdate results. Entity handles HA wiring (scheduling
    timers, writing HA state).

    The "wasp in a box" algorithm tracks whether motion was detected while
    a door was open. State persists through timeout windows to prevent false
    negatives from rapid open/close cycles.

    State owned by this machine:
    - wasp: bool — whether motion was recently detected
    - is_present: bool — derived presence result (presence when wasp detected or box open)
    """

    def __init__(self, wasp_timeout: int) -> None:
        """Initialize the wasp state machine.

        Args:
            wasp_timeout: Timeout in seconds for wasp to clear after box closes.

        """
        self._wasp_timeout = wasp_timeout
        self.wasp: bool = False
        self._timeout_requested: bool = False

    @property
    def is_present(self) -> bool:
        """Return whether the space is occupied (wasp or box active)."""
        # Present if wasp is active (motion detected) or if timeout is pending
        return self.wasp or self._timeout_requested

    @property
    def wasp_active(self) -> bool:
        """Return whether wasp is currently active."""
        return self.wasp

    def update_wasp(self, wasp_states: dict[str, str]) -> WaspStateUpdate:
        """Update machine state from wasp sensor states.

        Args:
            wasp_states: Dict mapping sensor names to STATE_ON/STATE_OFF.

        Returns:
            WaspStateUpdate with new presence and timer decisions.

        """
        wasp_state = self._aggregate_states(wasp_states)
        box_state = STATE_OFF  # We don't know box state, keep it OFF

        return self._compute_update(wasp_state, box_state)

    def update_box(self, box_states: dict[str, str]) -> WaspStateUpdate:
        """Update machine state from box sensor states.

        Args:
            box_states: Dict mapping sensor names to STATE_ON/STATE_OFF.

        Returns:
            WaspStateUpdate with new presence and timer decisions.

        """
        wasp_state = STATE_OFF  # We don't know wasp state, keep it OFF
        box_state = self._aggregate_states(box_states)

        return self._compute_update(wasp_state, box_state)

    def update_all(
        self, wasp_states: dict[str, str], box_states: dict[str, str]
    ) -> WaspStateUpdate:
        """Update machine state from both sensor groups.

        This is the most common call path when handling sensor state changes.

        Args:
            wasp_states: Dict mapping wasp sensor names to STATE_ON/STATE_OFF.
            box_states: Dict mapping box sensor names to STATE_ON/STATE_OFF.

        Returns:
            WaspStateUpdate with new presence and timer decisions.

        """
        wasp_state = self._aggregate_states(wasp_states)
        box_state = self._aggregate_states(box_states)

        return self._compute_update(wasp_state, box_state)

    def on_wasp_timeout(self) -> WaspStateUpdate:
        """Handle wasp timeout expiration.

        Called when the timeout timer fires after the box closes.
        Clears the wasp state and returns the update.

        Returns:
            WaspStateUpdate reflecting the timeout event.

        """
        self.wasp = False
        self._timeout_requested = False

        return WaspStateUpdate(
            is_present=self.is_present,
            wasp_active=self.wasp,
            box_open=False,
            request_timer=None,
            cancel_timer=True,
        )

    def on_delay_complete(
        self, wasp_states: dict[str, str], box_states: dict[str, str]
    ) -> WaspStateUpdate:
        """Handle completion of the box-close delay.

        After a box closes, there's a delay before running the full logic.
        This method is called when that delay expires.

        Args:
            wasp_states: Dict mapping wasp sensor names to STATE_ON/STATE_OFF.
            box_states: Dict mapping box sensor names to STATE_ON/STATE_OFF.

        Returns:
            WaspStateUpdate with new presence and timer decisions.

        """
        wasp_state = self._aggregate_states(wasp_states)
        box_state = self._aggregate_states(box_states)

        return self._compute_update(wasp_state, box_state)

    def _aggregate_states(self, states: dict[str, str]) -> str:
        """Aggregate sensor states to ON if any sensor is ON.

        Args:
            states: Dict mapping sensor names to STATE_ON/STATE_OFF.

        Returns:
            STATE_ON if any sensor is ON, STATE_OFF otherwise.

        """
        for state in states.values():
            if state == STATE_ON:
                return STATE_ON
        return STATE_OFF

    def _compute_update(self, wasp_state: str, box_state: str) -> WaspStateUpdate:
        """Compute the next state and any timer requests.

        Core logic (translated from entity's wasp_in_a_box method):
        - If wasp ON: set wasp=True, cancel timer
        - Elif box ON: set wasp=False, cancel timer
        - Else: start timer if wasp is active and timeout is configured

        Args:
            wasp_state: Aggregated wasp sensor state (STATE_ON/STATE_OFF).
            box_state: Aggregated box sensor state (STATE_ON/STATE_OFF).

        Returns:
            WaspStateUpdate with new presence, timer decisions, and state.

        """
        request_timer = None
        cancel_timer = False
        box_open = box_state == STATE_ON

        if wasp_state == STATE_ON:
            # Motion detected → set wasp, cancel any pending timer
            self.wasp = True
            self._timeout_requested = False
            cancel_timer = True
        elif box_open:
            # Door is open → clear wasp, cancel timer
            self.wasp = False
            self._timeout_requested = False
            cancel_timer = True
        else:
            # Both wasp and box are OFF
            # If wasp was active, start timer to eventually clear it
            if self.wasp and self._wasp_timeout > 0:
                request_timer = float(self._wasp_timeout)
                self._timeout_requested = True
            else:
                self._timeout_requested = False

        return WaspStateUpdate(
            is_present=self.is_present,
            wasp_active=self.wasp,
            box_open=box_open,
            request_timer=request_timer,
            cancel_timer=cancel_timer,
        )
