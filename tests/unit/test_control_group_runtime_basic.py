"""Basic resolver tests for core.controls.control_group_runtime."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.magic_areas.core.controls import (
    resolve_group_entity_id,
    resolve_group_member_entity_id,
)
from custom_components.magic_areas.core.controls import GroupRegistry
from tests.unit.control_group_runtime_testkit import patch_entity_registry, register_group


def test_resolve_group_entity_id_prefers_group_registry_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry definition should resolve to its entity-registry entity_id."""
    patch_entity_registry(
        monkeypatch,
        resolver=lambda domain, platform, unique_id: (
            "fan.magic_areas_fan_groups_kitchen_fan_group"
            if unique_id == "fan_groups_kitchen_fan_group"
            else None
        ),
    )
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="fan_groups_kitchen_fan_group",
        members=("fan.kitchen",),
        policy_id="fan_groups",
    )
    resolved = resolve_group_entity_id(
        MagicMock(),
        group_registry=registry,
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
    )
    assert resolved == "fan.magic_areas_fan_groups_kitchen_fan_group"


def test_resolve_group_entity_id_returns_none_when_no_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry-only resolver should return None when no group definition exists."""
    patch_entity_registry(monkeypatch, fixed_value=None)
    resolved = resolve_group_entity_id(
        MagicMock(),
        group_registry=GroupRegistry(),
        area_id="kitchen",
        policy_id="media_player_groups",
        domain="media_player",
    )
    assert resolved is None


def test_resolve_group_entity_id_does_not_attempt_legacy_fallback_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolver should only perform a single group_id entity-registry lookup."""
    fake_entity_registry = patch_entity_registry(
        monkeypatch,
        fixed_value="fan.magic_areas_fan_groups_kitchen_fan_group",
    )
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="fan_groups_kitchen_fan_group",
        members=("fan.kitchen",),
        policy_id="fan_groups",
    )
    resolved = resolve_group_entity_id(
        MagicMock(),
        group_registry=registry,
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
    )
    assert resolved == "fan.magic_areas_fan_groups_kitchen_fan_group"
    fake_entity_registry.async_get_entity_id.assert_called_once_with(
        "fan", "magic_areas", "fan_groups_kitchen_fan_group"
    )


def test_resolve_group_member_entity_id_returns_first_member() -> None:
    """Member resolver should return the indexed member from registry definition."""
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="climate_control_kitchen_climate_control",
        members=("climate.kitchen",),
        policy_id="climate_control",
    )
    resolved = resolve_group_member_entity_id(
        group_registry=registry,
        area_id="kitchen",
        policy_id="climate_control",
    )
    assert resolved == "climate.kitchen"


def test_resolve_group_member_entity_id_returns_none_when_missing() -> None:
    """Member resolver should return None for missing groups/index."""
    assert (
        resolve_group_member_entity_id(
            group_registry=GroupRegistry(),
            area_id="kitchen",
            policy_id="climate_control",
        )
        is None
    )


def test_resolve_group_member_entity_id_returns_none_for_out_of_bounds_index() -> None:
    """Member resolver should return None when requested index is out of range."""
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="climate_control_kitchen_climate_control",
        members=("climate.kitchen",),
        policy_id="climate_control",
    )
    resolved = resolve_group_member_entity_id(
        group_registry=registry,
        area_id="kitchen",
        policy_id="climate_control",
        member_index=2,
    )
    assert resolved is None
