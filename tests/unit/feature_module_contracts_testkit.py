"""Shared helpers for feature module contract tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeGuard
from unittest.mock import MagicMock

import pytest

from custom_components.magic_areas.area_state import AreaType
from custom_components.magic_areas.core.runtime_model import AreaConfig
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.features.base import FeatureModule

FEATURE_MODULE_SPECS: dict[str, tuple[str, str]] = {
    "aggregates": ("AggregatesFeatureModule", "aggregates"),
    "wasp_in_a_box": ("WaspInABoxFeatureModule", "wasp_in_a_box"),
    "light_groups": ("LightGroupsFeatureModule", "light_groups"),
    "fan_groups": ("FanGroupsFeatureModule", "fan_groups"),
    "media_player_groups": ("MediaPlayerGroupsFeatureModule", "media_player_groups"),
    "cover_groups": ("CoverGroupsFeatureModule", "cover_groups"),
    "presence_hold": ("PresenceHoldFeatureModule", "presence_hold"),
    "climate_control": ("ClimateControlFeatureModule", "climate_control"),
    "health": ("HealthFeatureModule", "health"),
    "ble_trackers": ("BLETrackersFeatureModule", "ble_trackers"),
}


def _is_feature_module(value: object) -> TypeGuard[FeatureModule]:
    """Return whether object satisfies the FeatureModule runtime contract."""
    return all(
        hasattr(value, attr)
        for attr in (
            "id",
            "domains",
            "supports_regular_area",
            "supports_meta_area",
            "supports_global_meta_area",
            "configurable_on_meta",
            "configurable_on_global_meta",
            "config_schema",
            "option_steps",
            "validate_config",
            "is_enabled",
            "depends_on",
            "build_entities",
            "desired_managed_surfaces",
            "attach_listeners",
            "config_flow_steps",
        )
    )


def make_area_config() -> AreaConfig:
    """Build standard area config for feature contract tests."""
    hass_config = MagicMock()
    hass_config.entry_id = "entry-1"
    return AreaConfig(
        id="area-1",
        name="Kitchen",
        slug="kitchen",
        area_type=AreaType.INTERIOR,
        config={},
        hass_config=hass_config,
    )


def make_coordinator(snapshot: MagicMock, hass: object | None = None) -> MagicMock:
    """Build coordinator mock bound to provided snapshot."""
    coordinator = MagicMock()
    coordinator.data = snapshot
    coordinator.last_update_success = True
    coordinator.hass = hass if hass is not None else MagicMock()
    return coordinator


def make_snapshot(
    *,
    enabled: set[MagicAreasFeatures],
    feature_configs: Mapping[MagicAreasFeatures, object],
    entities: Mapping[str, Sequence[Mapping[str, object]]],
) -> MagicMock:
    """Build snapshot mock for contract tests."""
    snapshot = MagicMock()
    snapshot.enabled_features = enabled
    snapshot.feature_configs = dict(feature_configs)
    snapshot.entities = {domain: [dict(entity) for entity in domain_entities] for domain, domain_entities in entities.items()}
    snapshot.magic_entities = {}
    snapshot.entity_references = MagicMock()
    snapshot.group_registry = GroupRegistry()
    return snapshot


def get_module(feature_name: str) -> FeatureModule:
    """Return module instance by feature key from modules package."""
    class_name, module_name = FEATURE_MODULE_SPECS[feature_name]
    try:
        modules_pkg = __import__(
            "custom_components.magic_areas.features.modules",
            fromlist=[class_name],
        )
    except ModuleNotFoundError:  # pragma: no cover
        pytest.fail(
            f"{class_name} not implemented yet (expected in "
            f"custom_components.magic_areas.features.modules.{module_name})"
        )

    module_cls = getattr(modules_pkg, class_name, None)
    if module_cls is None:  # pragma: no cover
        pytest.fail(
            f"{class_name} not implemented yet (expected in "
            f"custom_components.magic_areas.features.modules.{module_name})"
        )
    module = module_cls()
    if not _is_feature_module(module):  # pragma: no cover
        pytest.fail(f"{class_name} does not implement FeatureModule contract")
    return module


def group_ids_for_area(snapshot: MagicMock, area_id: str) -> set[str]:
    """Collect policy group ids for a specific area from snapshot registry."""
    return {
        group.definition.group_id
        for group in snapshot.group_registry.get_for_area(area_id)
    }
