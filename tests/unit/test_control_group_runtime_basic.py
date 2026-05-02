"""Basic resolver tests for core.controls.control_group_runtime."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call

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


def test_resolve_group_entity_id_uses_single_lookup_when_magic_areas_entity_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolver should not query native helpers when Magic Areas entity exists."""
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


def test_resolve_group_entity_id_falls_back_to_native_group_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolver should support HA group-helper entities owned by Magic Areas."""
    fake_entity_registry = patch_entity_registry(
        monkeypatch,
        resolver=lambda domain, platform, unique_id: (
            "fan.magic_areas_fan_groups_kitchen_fan_group"
            if platform == "group"
            and unique_id == "magic_areas:entry-1:kitchen:fan_groups:config_entry_helper:fan_group"
            else None
        ),
    )
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="magic_areas:entry-1:kitchen:fan_groups:config_entry_helper:fan_group",
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
    assert fake_entity_registry.async_get_entity_id.call_args_list == [
        call(
            "fan",
            "magic_areas",
            "magic_areas:entry-1:kitchen:fan_groups:config_entry_helper:fan_group",
        ),
        call(
            "fan",
            "group",
            "magic_areas:entry-1:kitchen:fan_groups:config_entry_helper:fan_group",
        ),
    ]


def test_resolve_group_entity_id_falls_back_through_helper_config_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Managed helper config-entry ownership should resolve its registered entity."""
    group_id = "magic_areas:entry-1:kitchen:fan_groups:config_entry_helper:fan_group"
    patch_entity_registry(monkeypatch, fixed_value=None)
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_entries_for_config_entry",
        lambda registry, entry_id: [
            SimpleNamespace(domain="fan", entity_id="fan.native_helper")
        ]
        if entry_id == "helper-entry"
        else [],
    )
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [
        SimpleNamespace(entry_id="helper-entry", unique_id=group_id)
    ]
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id=group_id,
        members=("fan.kitchen",),
        policy_id="fan_groups",
    )

    resolved = resolve_group_entity_id(
        hass,
        group_registry=registry,
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
    )

    assert resolved == "fan.native_helper"


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
