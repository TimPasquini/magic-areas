"""Shared helpers for control-group runtime unit tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from custom_components.magic_areas.core.controls import ControlGroupDefinition
from custom_components.magic_areas.core.controls import GroupRegistry


def patch_entity_registry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    resolver: Callable[[str, str, str], str | None] | None = None,
    fixed_value: str | None = None,
) -> MagicMock:
    """Patch HA entity registry accessor and return fake registry mock."""
    fake_entity_registry = MagicMock()
    if resolver is not None:
        fake_entity_registry.async_get_entity_id.side_effect = resolver
    else:
        fake_entity_registry.async_get_entity_id.return_value = fixed_value
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )
    return fake_entity_registry


def register_group(
    registry: GroupRegistry,
    *,
    area_id: str,
    group_id: str,
    members: tuple[str, ...],
    policy_id: str,
    metadata: dict[str, object] | None = None,
) -> None:
    """Register a default control group definition."""
    registry.register_area_default(
        area_id,
        ControlGroupDefinition(
            group_id=group_id,
            members=members,
            policy_id=policy_id,
            metadata=metadata or {},
        ),
    )
