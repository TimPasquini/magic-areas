"""Tests for shared control runtime support primitives."""

from custom_components.magic_areas.core.controls.runtime_support import (
    MonotonicDeadlineMap,
)


def test_deadline_map_adds_and_reports_active_key() -> None:
    """A deadline remains active until its monotonic deadline expires."""
    deadlines = MonotonicDeadlineMap[str]()

    deadlines.set_deadline("humidity", 15.0)

    assert deadlines.active_keys(10.0) == ("humidity",)


def test_deadline_map_replaces_existing_deadline() -> None:
    """Replacement updates the stored deadline for an existing key."""
    deadlines = MonotonicDeadlineMap[str]()

    deadlines.set_deadline("humidity", 15.0)
    deadlines.set_deadline("humidity", 30.0)

    assert deadlines.active_keys(20.0) == ("humidity",)


def test_deadline_map_setdefault_preserves_existing_deadline() -> None:
    """Setdefault preserves the first deadline for an existing key."""
    deadlines = MonotonicDeadlineMap[str]()

    assert deadlines.setdefault_deadline("humidity", 15.0) == 15.0
    assert deadlines.setdefault_deadline("humidity", 30.0) == 15.0

    assert deadlines.active_keys(20.0) == ()


def test_deadline_map_drops_expired_keys() -> None:
    """Expired deadlines are removed and reported in deterministic order."""
    deadlines = MonotonicDeadlineMap[str]()
    deadlines.set_deadline("odor", 20.0)
    deadlines.set_deadline("cooling", 10.0)
    deadlines.set_deadline("humidity", 10.0)

    assert deadlines.drop_expired(10.0) == ("cooling", "humidity")
    assert deadlines.active_keys(10.0) == ("odor",)


def test_deadline_map_active_keys_are_sorted_tuple() -> None:
    """Active keys are returned as a sorted tuple."""
    deadlines = MonotonicDeadlineMap[str]()
    deadlines.set_deadline("humidity", 20.0)
    deadlines.set_deadline("cooling", 20.0)
    deadlines.set_deadline("odor", 20.0)

    assert deadlines.active_keys(10.0) == ("cooling", "humidity", "odor")


def test_deadline_map_next_delay() -> None:
    """Next delay reports empty and positive delay states."""
    deadlines = MonotonicDeadlineMap[str]()

    assert deadlines.next_delay(10.0) is None

    deadlines.set_deadline("humidity", 10.0)
    assert deadlines.next_delay(9.5) == 0.5

    deadlines.set_deadline("odor", 8.0)
    assert deadlines.next_delay(8.0) == 2.0


def test_deadline_map_contains_prunes_expired_deadlines() -> None:
    """Contains checks one key after pruning expired deadlines."""
    deadlines = MonotonicDeadlineMap[str]()
    deadlines.set_deadline("humidity", 10.0)
    deadlines.set_deadline("odor", 20.0)

    assert not deadlines.contains("humidity", 10.0)
    assert deadlines.contains("odor", 10.0)


def test_deadline_map_handles_empty_map() -> None:
    """Empty maps report no active keys, expired keys, or next delay."""
    deadlines = MonotonicDeadlineMap[str]()

    assert not deadlines
    assert deadlines.drop_expired(10.0) == ()
    assert deadlines.active_keys(10.0) == ()
    assert deadlines.next_delay(10.0) is None
