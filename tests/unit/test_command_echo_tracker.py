"""Unit tests for light-group command echo state transitions."""

from custom_components.magic_areas.light_groups import CommandEchoState


def test_command_issue_sets_owner_and_pending_echo() -> None:
    """Issuing a command should claim ownership and await echo."""
    initial = CommandEchoState(owner_id="light.overhead", controlling=True)

    state = initial.command_issued("light.overhead")

    assert state.owner_id == "light.overhead"
    assert state.controlling is True
    assert state.awaiting_echo is True


def test_command_completed_clears_pending_state() -> None:
    """Receiving expected echo should clear pending flag and keep ownership."""
    issued = CommandEchoState(
        owner_id="light.overhead",
        controlling=True,
        awaiting_echo=True,
    )

    state = issued.command_completed()

    assert state.owner_id == "light.overhead"
    assert state.controlling is True
    assert state.awaiting_echo is False


def test_external_change_clears_ownership() -> None:
    """External state changes should fully reset ownership."""
    issued = CommandEchoState(
        owner_id="light.overhead",
        controlling=True,
        awaiting_echo=True,
    )

    state = issued.external_change()

    assert state.owner_id is None
    assert state.controlling is False
    assert state.awaiting_echo is False


def test_set_controlling_updates_control_flag_only() -> None:
    """set_controlling should preserve ownership and awaiting echo fields."""
    state = CommandEchoState(
        owner_id="light.overhead",
        controlling=True,
        awaiting_echo=True,
    )

    updated = state.set_controlling(False)

    assert updated.owner_id == "light.overhead"
    assert updated.controlling is False
    assert updated.awaiting_echo is True
