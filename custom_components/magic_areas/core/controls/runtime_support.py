"""Shared runtime support primitives for control paths."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass, field


@dataclass(slots=True)
class MonotonicDeadlineMap[KeyT: Hashable]:
    """Track monotonic deadlines keyed by domain-owned identifiers."""

    _deadlines: dict[KeyT, float] = field(default_factory=dict)

    def set_deadline(self, key: KeyT, deadline: float) -> float:
        """Set or replace a deadline for a key."""
        self._deadlines[key] = deadline
        return deadline

    def setdefault_deadline(self, key: KeyT, deadline: float) -> float:
        """Set a deadline for a key only when one is not already present."""
        return self._deadlines.setdefault(key, deadline)

    def discard(self, key: KeyT) -> None:
        """Discard one deadline if present."""
        self._deadlines.pop(key, None)

    def drop_expired(self, now: float) -> tuple[KeyT, ...]:
        """Remove expired deadlines and return the removed keys."""
        expired = [
            key for key, deadline in tuple(self._deadlines.items()) if now >= deadline
        ]
        for key in expired:
            self._deadlines.pop(key, None)
        return _sorted_keys(expired)

    def active_keys(self, now: float) -> tuple[KeyT, ...]:
        """Return active keys after pruning expired deadlines."""
        self.drop_expired(now)
        return _sorted_keys(self._deadlines)

    def contains(self, key: KeyT, now: float) -> bool:
        """Return whether one key is active after pruning expired deadlines."""
        self.drop_expired(now)
        return key in self._deadlines

    def next_delay(self, now: float) -> float | None:
        """Return delay until the next active deadline, or None when empty."""
        self.drop_expired(now)
        if not self._deadlines:
            return None
        return max(min(self._deadlines.values()) - now, 0.0)

    def __bool__(self) -> bool:
        """Return whether any unpruned deadlines are stored."""
        return bool(self._deadlines)


def _sorted_keys[KeyT: Hashable](keys: Iterable[KeyT]) -> tuple[KeyT, ...]:
    """Return keys in deterministic order without constraining key type."""
    return tuple(sorted(keys, key=str))


def merged_extra_state_attributes(
    current: Mapping[str, object] | None,
    updates: Mapping[str, object],
) -> dict[str, object]:
    """Return extra state attributes with updates applied."""
    attrs = dict(current or {})
    attrs.update(updates)
    return attrs


__all__ = ["MonotonicDeadlineMap", "merged_extra_state_attributes"]
