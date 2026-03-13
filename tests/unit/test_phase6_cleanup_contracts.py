"""Contracts that guard migration-cleanup boundaries."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from custom_components.magic_areas.core.controls import resolve_group_entity_id
from custom_components.magic_areas.core.runtime_model import GroupRegistryView
import custom_components.magic_areas.light_groups as light_groups
from custom_components.magic_areas.light_groups import AreaLightGroup


def test_resolve_group_entity_id_signature_is_registry_only() -> None:
    """Target resolver should not expose legacy fallback parameters."""
    params = inspect.signature(resolve_group_entity_id).parameters
    assert "fallback_unique_id" not in params
    assert set(params) == {"hass", "group_registry", "area_id", "policy_id", "domain"}


def test_area_light_group_no_longer_exposes_legacy_controlled_property() -> None:
    """Legacy controlled shim should not exist on AreaLightGroup."""
    assert not hasattr(AreaLightGroup, "controlled")


def test_resolve_group_entity_id_uses_group_registry_protocol_annotation() -> None:
    """Resolver contract should accept the explicit group-registry protocol."""
    hints = get_type_hints(resolve_group_entity_id)
    assert hints["group_registry"] is GroupRegistryView


def test_area_light_group_controlling_property_is_read_only() -> None:
    """Controlling should be a read-only runtime view backed by echo state."""
    prop = AreaLightGroup.controlling
    assert isinstance(prop, property)
    assert prop.fset is None


def test_light_groups_package_no_longer_exports_removed_runtime_helpers() -> None:
    """Removed runtime helpers should stay out of the package surface."""
    removed_names = {
        "resolve_light_category_config",
        "reset_control_state",
        "update_primary_control_state",
        "update_secondary_control_state",
    }
    exported = set(getattr(light_groups, "__all__", []))
    assert removed_names.isdisjoint(exported)
