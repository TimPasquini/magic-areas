"""Mutable control-group registry implementation."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from custom_components.magic_areas.core.runtime_model import ControlGroupDefinitionView


@dataclass(frozen=True, slots=True)
class RegisteredControlGroup:
    """Stored control-group entry with scope metadata."""

    definition: ControlGroupDefinitionView
    area_id: str | None = None
    is_custom: bool = False


class GroupRegistry:
    """Track control-group definitions and resolve active groups per area."""

    def __init__(self) -> None:
        """Initialize an empty control-group registry."""
        self._entries: dict[tuple[str | None, str], RegisteredControlGroup] = {}

    def register_default(self, definition: ControlGroupDefinitionView) -> None:
        """Register a default/global group definition."""
        key = (None, definition.group_id)
        self._entries[key] = RegisteredControlGroup(
            definition=definition,
            area_id=None,
            is_custom=False,
        )

    def register_area_default(
        self, area_id: str, definition: ControlGroupDefinitionView
    ) -> None:
        """Register an area-scoped default group definition."""
        key = (area_id, definition.group_id)
        self._entries[key] = RegisteredControlGroup(
            definition=definition,
            area_id=area_id,
            is_custom=False,
        )

    def register_custom(self, area_id: str, definition: ControlGroupDefinitionView) -> None:
        """Register an area-scoped custom group definition."""
        key = (area_id, definition.group_id)
        self._entries[key] = RegisteredControlGroup(
            definition=definition,
            area_id=area_id,
            is_custom=True,
        )

    def register_area_customs(
        self,
        area_id: str,
        definitions: Sequence[ControlGroupDefinitionView],
    ) -> None:
        """Replace area-scoped custom group definitions."""
        keys_to_remove = [
            key
            for key, entry in self._entries.items()
            if key[0] == area_id and entry.is_custom
        ]
        for key in keys_to_remove:
            del self._entries[key]

        for definition in definitions:
            self.register_custom(area_id, definition)

    def register_area_defaults(
        self,
        area_id: str,
        definitions: Sequence[ControlGroupDefinitionView],
        *,
        policy_id: str | None = None,
    ) -> None:
        """Replace area-scoped default definitions for an optional policy scope."""
        keys_to_remove = [
            key
            for key, entry in self._entries.items()
            if key[0] == area_id
            and not entry.is_custom
            and (policy_id is None or entry.definition.policy_id == policy_id)
        ]
        for key in keys_to_remove:
            del self._entries[key]

        for definition in definitions:
            self.register_area_default(area_id, definition)

    def get_for_area(self, area_id: str) -> list[RegisteredControlGroup]:
        """Return active groups for an area, with custom definitions overriding defaults."""
        scoped: dict[str, RegisteredControlGroup] = {}

        for (entry_area_id, group_id), entry in self._entries.items():
            if entry_area_id is None:
                scoped[group_id] = entry

        for (entry_area_id, group_id), entry in self._entries.items():
            if entry_area_id == area_id:
                scoped[group_id] = entry

        return [scoped[group_id] for group_id in sorted(scoped)]

    def get_for_area_policy(
        self, area_id: str, policy_id: str
    ) -> list[RegisteredControlGroup]:
        """Return active groups for an area filtered by policy id."""
        return [
            entry
            for entry in self.get_for_area(area_id)
            if entry.definition.policy_id == policy_id
        ]

    def get_first_for_area_policy(
        self, area_id: str, policy_id: str
    ) -> RegisteredControlGroup | None:
        """Return the first matching group for area+policy, if any."""
        matches = self.get_for_area_policy(area_id, policy_id)
        return matches[0] if matches else None


__all__ = ["GroupRegistry", "RegisteredControlGroup"]
