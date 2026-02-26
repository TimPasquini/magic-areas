"""State machine for light group control tracking.

Encapsulates the controlling/controlled boolean pair as an explicit state machine
with clear transitions to prevent race conditions.
"""

from __future__ import annotations


class ControlState:
    """State machine for light group control.

    controlling: We sent the last command (we think we're in control)
    controlled: We sent a command and are waiting for the echo/feedback
    """

    def __init__(self, controlling: bool = False, controlled: bool = False) -> None:
        """Initialize control state."""
        self.controlling = controlling
        self.controlled = controlled

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ControlState(controlling={self.controlling}, controlled={self.controlled})"

    def command_issued(self) -> ControlState:
        """We sent a command; mark that we are controlling and expect an echo."""
        return ControlState(controlling=True, controlled=True)

    def command_completed(self) -> ControlState:
        """Echo received; clear the controlled flag.

        We stay in controlling state until someone else changes the light.
        """
        return ControlState(controlling=self.controlling, controlled=False)

    def external_change(self) -> ControlState:
        """Someone else changed the light; stop controlling."""
        return ControlState(controlling=False, controlled=False)

    def area_cleared(self) -> ControlState:
        """Area cleared; reset to neutral state."""
        return ControlState(controlling=False, controlled=False)

    def set_controlled(self, controlled: bool) -> ControlState:
        """Return new state with updated controlled flag."""
        return ControlState(controlling=self.controlling, controlled=controlled)

    def set_controlling(self, controlling: bool) -> ControlState:
        """Return new state with updated controlling flag."""
        return ControlState(controlling=controlling, controlled=self.controlled)
