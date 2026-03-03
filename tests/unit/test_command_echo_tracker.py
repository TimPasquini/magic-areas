"""Unit tests for core.command_echo."""

from custom_components.magic_areas.core.command_echo import CommandEchoTracker


def test_command_issue_sets_owner_and_pending_echo() -> None:
    """Issuing a command should claim ownership and await echo."""
    tracker = CommandEchoTracker()

    state = tracker.command_issued("light.overhead")

    assert state.owner_id == "light.overhead"
    assert state.controlling is True
    assert state.awaiting_echo is True


def test_echo_received_completes_pending_state() -> None:
    """Matching echo should clear pending flag and keep ownership."""
    tracker = CommandEchoTracker()
    tracker.command_issued("light.overhead")

    state = tracker.echo_received("light.overhead")

    assert state.owner_id == "light.overhead"
    assert state.controlling is True
    assert state.awaiting_echo is False


def test_mismatched_echo_is_ignored() -> None:
    """Non-owner echoes should not mutate the tracker state."""
    tracker = CommandEchoTracker()
    tracker.command_issued("light.overhead")

    state = tracker.echo_received("light.task")

    assert state.owner_id == "light.overhead"
    assert state.controlling is True
    assert state.awaiting_echo is True


def test_external_change_clears_ownership() -> None:
    """External state changes should fully reset ownership."""
    tracker = CommandEchoTracker()
    tracker.command_issued("light.overhead")
    tracker.echo_received("light.overhead")

    state = tracker.external_change()

    assert state.owner_id is None
    assert state.controlling is False
    assert state.awaiting_echo is False
