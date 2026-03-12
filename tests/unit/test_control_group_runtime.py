"""Unit tests for core.control_group_runtime."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.magic_areas.core.control_group import ControlGroupDefinition
from custom_components.magic_areas.core.control_group_runtime import (
    resolve_group_entity_id_by_metadata,
    resolve_group_entity_ids_by_metadata,
    resolve_group_entity_id,
    resolve_group_member_entity_id_by_metadata,
    resolve_group_member_entity_id,
)
from custom_components.magic_areas.core.group_registry import GroupRegistry


def test_resolve_group_entity_id_prefers_group_registry_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry definition should resolve to its entity-registry entity_id."""
    fake_entity_registry = MagicMock()
    fake_entity_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: (
            "fan.magic_areas_fan_groups_kitchen_fan_group"
            if unique_id == "fan_groups_kitchen_fan_group"
            else None
        )
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )
    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="fan_groups_kitchen_fan_group",
            members=("fan.kitchen",),
            policy_id="fan_groups",
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_entity_id(
        MagicMock(),
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
    )

    assert resolved == "fan.magic_areas_fan_groups_kitchen_fan_group"


def test_resolve_group_entity_id_returns_none_when_no_definition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry-only resolver should return None when no group definition exists."""
    fake_entity_registry = MagicMock()
    fake_entity_registry.async_get_entity_id.return_value = None
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        GroupRegistry(),
    )

    resolved = resolve_group_entity_id(
        MagicMock(),
        area_id="kitchen",
        policy_id="media_player_groups",
        domain="media_player",
    )

    assert resolved is None


def test_resolve_group_entity_id_does_not_attempt_legacy_fallback_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolver should only perform a single group_id entity-registry lookup."""
    fake_entity_registry = MagicMock()
    fake_entity_registry.async_get_entity_id.return_value = (
        "fan.magic_areas_fan_groups_kitchen_fan_group"
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )
    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="fan_groups_kitchen_fan_group",
            members=("fan.kitchen",),
            policy_id="fan_groups",
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_entity_id(
        MagicMock(),
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
    )

    assert resolved == "fan.magic_areas_fan_groups_kitchen_fan_group"
    fake_entity_registry.async_get_entity_id.assert_called_once_with(
        "fan",
        "magic_areas",
        "fan_groups_kitchen_fan_group",
    )


def test_resolve_group_member_entity_id_returns_first_member(monkeypatch: pytest.MonkeyPatch) -> None:
    """Member resolver should return the indexed member from registry definition."""
    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="climate_control_kitchen_climate_control",
            members=("climate.kitchen",),
            policy_id="climate_control",
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_member_entity_id(
        area_id="kitchen",
        policy_id="climate_control",
    )

    assert resolved == "climate.kitchen"


def test_resolve_group_member_entity_id_returns_none_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Member resolver should return None for missing groups/index."""
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        GroupRegistry(),
    )

    assert (
        resolve_group_member_entity_id(
            area_id="kitchen",
            policy_id="climate_control",
        )
        is None
    )


def test_resolve_group_member_entity_id_returns_none_for_out_of_bounds_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Member resolver should return None when requested index is out of range."""
    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="climate_control_kitchen_climate_control",
            members=("climate.kitchen",),
            policy_id="climate_control",
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_member_entity_id(
        area_id="kitchen",
        policy_id="climate_control",
        member_index=2,
    )

    assert resolved is None


def test_resolve_group_entity_ids_by_metadata_returns_matching_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata resolver should return mapped entity IDs for groups."""
    fake_entity_registry = MagicMock()
    fake_entity_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: (
            f"light.magic_areas_{unique_id}"
            if unique_id.startswith("light_groups_kitchen_")
            else None
        )
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )

    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="light_groups_kitchen_overhead_lights",
            members=("light.one",),
            policy_id="light_groups",
            metadata={"category": "overhead_lights"},
        ),
    )
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="light_groups_kitchen_task_lights",
            members=("light.two",),
            policy_id="light_groups",
            metadata={"category": "task_lights"},
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_entity_ids_by_metadata(
        MagicMock(),
        area_id="kitchen",
        policy_id="light_groups",
        domain="light",
        metadata_key="category",
    )

    assert resolved == {
        "overhead_lights": "light.magic_areas_light_groups_kitchen_overhead_lights",
        "task_lights": "light.magic_areas_light_groups_kitchen_task_lights",
    }


def test_resolve_group_entity_ids_by_metadata_skips_non_string_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata resolver should ignore groups whose metadata value is not a string."""
    fake_entity_registry = MagicMock()
    fake_entity_registry.async_get_entity_id.return_value = (
        "light.magic_areas_light_groups_kitchen_overhead_lights"
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )

    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="light_groups_kitchen_overhead_lights",
            members=("light.one",),
            policy_id="light_groups",
            metadata={"category": ["overhead_lights"]},
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_entity_ids_by_metadata(
        MagicMock(),
        area_id="kitchen",
        policy_id="light_groups",
        domain="light",
        metadata_key="category",
    )

    assert resolved == {}


def test_resolve_group_entity_ids_by_metadata_applies_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata resolver should apply additional metadata filters."""
    fake_entity_registry = MagicMock()
    fake_entity_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: f"{domain}.magic_areas_{unique_id}"
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )

    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="aggregates_kitchen_aggregate_temperature",
            members=("sensor.temp_1",),
            policy_id="aggregate",
            metadata={
                "aggregate_device_class": "temperature",
                "aggregate_domain": "sensor",
            },
        ),
    )
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="aggregates_kitchen_aggregate_motion",
            members=("binary_sensor.motion_1",),
            policy_id="aggregate",
            metadata={
                "aggregate_device_class": "motion",
                "aggregate_domain": "binary_sensor",
            },
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_entity_ids_by_metadata(
        MagicMock(),
        area_id="kitchen",
        policy_id="aggregate",
        domain="sensor",
        metadata_key="aggregate_device_class",
        metadata_filters={"aggregate_domain": "sensor"},
    )

    assert resolved == {
        "temperature": "sensor.magic_areas_aggregates_kitchen_aggregate_temperature"
    }


def test_resolve_group_entity_id_by_metadata_returns_exact_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata+value resolver should return entity_id for a single match."""
    fake_entity_registry = MagicMock()
    fake_entity_registry.async_get_entity_id.return_value = (
        "fan.magic_areas_fan_groups_kitchen_fan_group"
    )
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )

    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="fan_groups_kitchen_fan_group",
            members=("fan.kitchen",),
            policy_id="fan_groups",
            metadata={"role": "primary"},
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_entity_id_by_metadata(
        MagicMock(),
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
        metadata_key="role",
        metadata_value="primary",
    )
    assert resolved == "fan.magic_areas_fan_groups_kitchen_fan_group"


def test_resolve_group_entity_id_by_metadata_returns_none_when_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata+value resolver should return None when multiple groups match."""
    fake_entity_registry = MagicMock()
    monkeypatch.setattr(
        "homeassistant.helpers.entity_registry.async_get",
        lambda hass: fake_entity_registry,
    )

    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="fan_groups_kitchen_a",
            members=("fan.kitchen_a",),
            policy_id="fan_groups",
            metadata={"role": "primary"},
        ),
    )
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="fan_groups_kitchen_b",
            members=("fan.kitchen_b",),
            policy_id="fan_groups",
            metadata={"role": "primary"},
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_entity_id_by_metadata(
        MagicMock(),
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
        metadata_key="role",
        metadata_value="primary",
    )
    assert resolved is None
    fake_entity_registry.async_get_entity_id.assert_not_called()


def test_resolve_group_member_entity_id_by_metadata_returns_exact_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata+value member resolver should return selected member."""
    registry = GroupRegistry()
    registry.register_area_default(
        "kitchen",
        ControlGroupDefinition(
            group_id="climate_control_kitchen_climate_control",
            members=("climate.kitchen",),
            policy_id="climate_control",
            metadata={"role": "primary"},
        ),
    )
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_group_runtime.GROUP_REGISTRY",
        registry,
    )

    resolved = resolve_group_member_entity_id_by_metadata(
        area_id="kitchen",
        policy_id="climate_control",
        metadata_key="role",
        metadata_value="primary",
    )
    assert resolved == "climate.kitchen"
