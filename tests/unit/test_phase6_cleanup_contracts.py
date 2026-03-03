"""Contracts that guard migration-cleanup boundaries."""

from __future__ import annotations

import inspect

from custom_components.magic_areas.core.control_group_runtime import (
    resolve_group_entity_id,
)
from custom_components.magic_areas.light_groups.entities import AreaLightGroup


def test_resolve_group_entity_id_signature_is_registry_only() -> None:
    """Target resolver should not expose legacy fallback parameters."""
    params = inspect.signature(resolve_group_entity_id).parameters
    assert "fallback_unique_id" not in params
    assert set(params) == {"hass", "area_id", "policy_id", "domain"}


def test_area_light_group_no_longer_exposes_legacy_controlled_property() -> None:
    """Legacy controlled shim should not exist on AreaLightGroup."""
    assert not hasattr(AreaLightGroup, "controlled")


def test_area_light_group_controlling_property_is_read_only() -> None:
    """Controlling should be a read-only runtime view backed by echo state."""
    prop = AreaLightGroup.controlling
    assert isinstance(prop, property)
    assert prop.fset is None
