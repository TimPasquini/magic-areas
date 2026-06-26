"""Metadata resolver tests for core.controls.control_group_runtime."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.magic_areas.core.controls import (
    resolve_group_entity_id_by_metadata,
    resolve_group_entity_ids_by_metadata,
    resolve_group_entity_ids_for_metadata_values,
    resolve_group_member_entity_id_by_metadata,
)
from custom_components.magic_areas.core.controls import GroupRegistry
from tests.unit.control_group_runtime_testkit import (
    patch_entity_registry,
    register_group,
)


def test_resolve_group_entity_ids_by_metadata_returns_matching_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata resolver should return mapped entity IDs for groups."""
    patch_entity_registry(
        monkeypatch,
        resolver=lambda domain, platform, unique_id: (
            f"light.magic_areas_{unique_id}"
            if unique_id.startswith("light_groups_kitchen_")
            else None
        ),
    )
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="light_groups_kitchen_overhead_lights",
        members=("light.one",),
        policy_id="light_groups",
        metadata={"category": "overhead_lights"},
    )
    register_group(
        registry,
        area_id="kitchen",
        group_id="light_groups_kitchen_task_lights",
        members=("light.two",),
        policy_id="light_groups",
        metadata={"category": "task_lights"},
    )
    resolved = resolve_group_entity_ids_by_metadata(
        MagicMock(),
        group_registry=registry,
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
    patch_entity_registry(
        monkeypatch,
        fixed_value="light.magic_areas_light_groups_kitchen_overhead_lights",
    )
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="light_groups_kitchen_overhead_lights",
        members=("light.one",),
        policy_id="light_groups",
        metadata={"category": ["overhead_lights"]},
    )
    resolved = resolve_group_entity_ids_by_metadata(
        MagicMock(),
        group_registry=registry,
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
    patch_entity_registry(
        monkeypatch,
        resolver=lambda domain,
        platform,
        unique_id: f"{domain}.magic_areas_{unique_id}",
    )
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="aggregates_kitchen_aggregate_temperature",
        members=("sensor.temp_1",),
        policy_id="aggregate",
        metadata={
            "aggregate_device_class": "temperature",
            "aggregate_domain": "sensor",
        },
    )
    register_group(
        registry,
        area_id="kitchen",
        group_id="aggregates_kitchen_aggregate_motion",
        members=("binary_sensor.motion_1",),
        policy_id="aggregate",
        metadata={
            "aggregate_device_class": "motion",
            "aggregate_domain": "binary_sensor",
        },
    )
    resolved = resolve_group_entity_ids_by_metadata(
        MagicMock(),
        group_registry=registry,
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
    patch_entity_registry(
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
        metadata={"role": "primary"},
    )
    resolved = resolve_group_entity_id_by_metadata(
        MagicMock(),
        group_registry=registry,
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
    fake_entity_registry = patch_entity_registry(monkeypatch, fixed_value=None)
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="fan_groups_kitchen_a",
        members=("fan.kitchen_a",),
        policy_id="fan_groups",
        metadata={"role": "primary"},
    )
    register_group(
        registry,
        area_id="kitchen",
        group_id="fan_groups_kitchen_b",
        members=("fan.kitchen_b",),
        policy_id="fan_groups",
        metadata={"role": "primary"},
    )
    resolved = resolve_group_entity_id_by_metadata(
        MagicMock(),
        group_registry=registry,
        area_id="kitchen",
        policy_id="fan_groups",
        domain="fan",
        metadata_key="role",
        metadata_value="primary",
    )
    assert resolved is None
    fake_entity_registry.async_get_entity_id.assert_not_called()


def test_resolve_group_member_entity_id_by_metadata_returns_exact_member() -> None:
    """Metadata+value member resolver should return selected member."""
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="climate_control_kitchen_climate_control",
        members=("climate.kitchen",),
        policy_id="climate_control",
        metadata={"role": "primary"},
    )
    resolved = resolve_group_member_entity_id_by_metadata(
        group_registry=registry,
        area_id="kitchen",
        policy_id="climate_control",
        metadata_key="role",
        metadata_value="primary",
    )
    assert resolved == "climate.kitchen"


def test_resolve_group_entity_ids_for_metadata_values_preserves_input_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordered metadata resolver should preserve requested metadata order."""
    patch_entity_registry(
        monkeypatch,
        resolver=lambda domain, platform, unique_id: (
            f"light.magic_areas_{unique_id}"
            if unique_id.startswith("light_groups_kitchen_")
            else None
        ),
    )
    registry = GroupRegistry()
    register_group(
        registry,
        area_id="kitchen",
        group_id="light_groups_kitchen_overhead_lights",
        members=("light.one",),
        policy_id="light_groups",
        metadata={"category": "overhead"},
    )
    register_group(
        registry,
        area_id="kitchen",
        group_id="light_groups_kitchen_task_lights",
        members=("light.two",),
        policy_id="light_groups",
        metadata={"category": "task"},
    )
    resolved = resolve_group_entity_ids_for_metadata_values(
        MagicMock(),
        group_registry=registry,
        area_id="kitchen",
        policy_id="light_groups",
        domain="light",
        metadata_key="category",
        metadata_values=["task", "overhead"],
    )
    assert resolved == [
        "light.magic_areas_light_groups_kitchen_task_lights",
        "light.magic_areas_light_groups_kitchen_overhead_lights",
    ]


def test_resolve_group_entity_ids_for_metadata_values_returns_none_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordered metadata resolver should return None when no values resolve."""
    patch_entity_registry(monkeypatch, fixed_value=None)
    resolved = resolve_group_entity_ids_for_metadata_values(
        MagicMock(),
        group_registry=GroupRegistry(),
        area_id="kitchen",
        policy_id="light_groups",
        domain="light",
        metadata_key="category",
        metadata_values=["task", "overhead"],
    )
    assert resolved is None
