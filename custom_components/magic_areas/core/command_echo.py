"""Generic command-echo ownership tracking for control groups."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandEchoState:
    """Immutable snapshot of command ownership state."""

    owner_id: str | None = None
    controlling: bool = False
    awaiting_echo: bool = False

    @property
    def controlled(self) -> bool:
        """Compatibility alias for legacy control-state naming."""
        return self.awaiting_echo

    def command_issued(self, owner_id: str | None = None) -> CommandEchoState:
        """Return state after issuing a command."""
        return CommandEchoState(
            owner_id=owner_id if owner_id is not None else self.owner_id,
            controlling=True,
            awaiting_echo=True,
        )

    def command_completed(self) -> CommandEchoState:
        """Return state after receiving an expected echo."""
        return CommandEchoState(
            owner_id=self.owner_id,
            controlling=self.controlling,
            awaiting_echo=False,
        )

    def external_change(self) -> CommandEchoState:
        """Return neutral state after non-owned change."""
        return CommandEchoState()

    def set_controlled(self, controlled: bool) -> CommandEchoState:
        """Return state with updated awaiting-echo flag."""
        return CommandEchoState(
            owner_id=self.owner_id,
            controlling=self.controlling,
            awaiting_echo=controlled,
        )

    def set_controlling(self, controlling: bool) -> CommandEchoState:
        """Return state with updated controlling flag."""
        return CommandEchoState(
            owner_id=self.owner_id,
            controlling=controlling,
            awaiting_echo=self.awaiting_echo,
        )


class CommandEchoTracker:
    """Track ownership for command/echo loops across control groups."""

    def __init__(self) -> None:
        """Initialize a neutral command-ownership state."""
        self._state = CommandEchoState()

    @property
    def state(self) -> CommandEchoState:
        """Return current ownership state."""
        return self._state

    def set_state(self, state: CommandEchoState) -> CommandEchoState:
        """Set tracker state from a policy decision."""
        self._state = state
        return self._state

    def command_issued(self, owner_id: str) -> CommandEchoState:
        """Mark that an owner issued a command and now expects an echo."""
        self._state = CommandEchoState(
            owner_id=owner_id,
            controlling=True,
            awaiting_echo=True,
        )
        return self._state

    def echo_received(self, owner_id: str | None = None) -> CommandEchoState:
        """Mark command echo completion if owner matches or is unspecified."""
        if self._state.owner_id is None:
            return self._state

        if owner_id is not None and owner_id != self._state.owner_id:
            return self._state

        self._state = CommandEchoState(
            owner_id=self._state.owner_id,
            controlling=True,
            awaiting_echo=False,
        )
        return self._state

    def external_change(self) -> CommandEchoState:
        """Clear ownership when a non-owned state change is detected."""
        self._state = CommandEchoState()
        return self._state

    def reset(self) -> CommandEchoState:
        """Reset to neutral state."""
        self._state = CommandEchoState()
        return self._state
