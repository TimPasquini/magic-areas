"""Contract tests for light groups feature module."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast
from unittest.mock import Mock

import pytest

from custom_components.magic_areas.coordinator import MagicAreasData
from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    ManagedAdaptiveLightingConfig,
    SLEEP_SWITCH,
)
from custom_components.magic_areas.core.runtime_model import (
    AreaConfig,
    ConfigEntryHelperSurface,
    LabelSurface,
    SignalHelperSurface,
)
from custom_components.magic_areas.enums import MagicAreasFeatures
from custom_components.magic_areas.light_groups import LightGroupRuntimeController

from .feature_module_contracts_testkit import (
    get_module,
    make_area_config,
    make_coordinator,
    make_snapshot,
)


class _ManagedAdaptiveLightingModule(Protocol):
    """Feature-module subset used by managed Adaptive Lighting tests."""

    def desired_managed_adaptive_lighting_configs(
        self,
        area_config: AreaConfig,
        data: MagicAreasData,
    ) -> list[ManagedAdaptiveLightingConfig]:
        """Return desired managed Adaptive Lighting configs."""
        ...


class _LightGroupRuntimeModule(_ManagedAdaptiveLightingModule, Protocol):
    """Feature-module subset used by runtime-controller tests."""

    def build_runtime_controllers(
        self,
        area_config: AreaConfig,
        coordinator: object,
        data: MagicAreasData,
    ) -> list[LightGroupRuntimeController]:
        """Return non-entity light-group runtime controllers."""
        ...


def _managed_adaptive_lighting_module() -> _ManagedAdaptiveLightingModule:
    """Return light-groups module narrowed to the managed AL contract."""
    return cast(_ManagedAdaptiveLightingModule, get_module("light_groups"))


def _light_group_runtime_module() -> _LightGroupRuntimeModule:
    """Return light-groups module narrowed to the runtime-controller contract."""
    return cast(_LightGroupRuntimeModule, get_module("light_groups"))


def _attrs(entity: object) -> Mapping[str, object]:
    """Return non-optional extra attributes for entity assertions."""
    attributes = getattr(
        entity,
        "extra_state_attributes",
        getattr(entity, "_attr_extra_state_attributes", None),
    )
    assert isinstance(attributes, Mapping)
    return attributes


def test_light_groups_module_builds_expected_entities() -> None:
    """Light groups module should expose only its control switch as a MA entity."""
    area_config = make_area_config()
    entities_by_domain = {"light": [{"entity_id": "light.overhead_1"}]}
    feature_configs = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            "overhead_lights": ["light.overhead_1"],
            "overhead_lights_states": ["occupied", "bright"],
            "overhead_lights_act_on": ["occupancy", "state"],
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("light_groups")
    entities = module.build_entities(area_config, coordinator, snapshot)

    entity_ids = sorted(entity.entity_id for entity in entities)
    assert entity_ids == [
        "switch.magic_areas_light_groups_kitchen_light_control",
    ]


def test_light_groups_module_adopts_adaptive_lighting_for_configured_role() -> None:
    """Adaptive Lighting switch sets should attach only to their configured role."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "adaptive_lighting_mode": "adopt_existing",
                "adaptive_lighting_switch_sets": {
                    "overhead_lights": {
                        MAIN_SWITCH: "switch.adaptive_lighting_kitchen_overhead",
                        SLEEP_SWITCH: (
                            "switch.adaptive_lighting_sleep_mode_kitchen_overhead"
                        ),
                        ADAPT_BRIGHTNESS_SWITCH: (
                            "switch.adaptive_lighting_adapt_brightness_kitchen_overhead"
                        ),
                        ADAPT_COLOR_SWITCH: (
                            "switch.adaptive_lighting_adapt_color_kitchen_overhead"
                        ),
                    }
                },
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    module = _light_group_runtime_module()

    controllers = {
        getattr(controller, "category"): controller
        for controller in module.build_runtime_controllers(
            area_config, make_coordinator(snapshot), snapshot
        )
    }

    all_group = controllers["all_lights"]
    overhead_group = controllers["overhead_lights"]

    assert getattr(all_group, "_adaptive_lighting_switch_set") is None
    switch_set = getattr(overhead_group, "_adaptive_lighting_switch_set")
    assert switch_set is not None
    assert switch_set.role == "overhead_lights"


def test_light_groups_module_defers_managed_adaptive_lighting_role_until_registry() -> None:
    """Manage mode should defer runtime switch binding until AL creates registry entries."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "adaptive_lighting_mode": "manage",
                "adaptive_lighting_managed_roles": ["overhead_lights"],
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    module = _light_group_runtime_module()

    controllers = {
        getattr(controller, "category"): controller
        for controller in module.build_runtime_controllers(
            area_config, make_coordinator(snapshot), snapshot
        )
    }

    all_group = controllers["all_lights"]
    overhead_group = controllers["overhead_lights"]

    assert getattr(all_group, "_adaptive_lighting_switch_set") is None
    switch_set = getattr(overhead_group, "_adaptive_lighting_switch_set")
    assert switch_set is None
    assert _attrs(overhead_group)["adaptive_lighting"] == {
        "mode": "manage",
        "role": "overhead_lights",
        "active": True,
        "reason": "associated",
        "main_switch_entity_id": "switch.adaptive_lighting_ma_kitchen_overhead",
    }


def test_light_groups_module_defers_managed_adaptive_lighting_all_lights_until_registry() -> None:
    """Manage mode should defer room-level switch binding until AL creates entries."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "adaptive_lighting_mode": "manage",
                "adaptive_lighting_manage_all_lights": True,
                "adaptive_lighting_managed_roles": [],
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    module = _light_group_runtime_module()

    controllers = {
        getattr(controller, "category"): controller
        for controller in module.build_runtime_controllers(
            area_config, make_coordinator(snapshot), snapshot
        )
    }

    all_group = controllers["all_lights"]
    overhead_group = controllers["overhead_lights"]

    switch_set = getattr(all_group, "_adaptive_lighting_switch_set")
    assert switch_set is None
    assert _attrs(all_group)["adaptive_lighting"] == {
        "mode": "manage",
        "role": "all_lights",
        "active": True,
        "reason": "associated",
        "main_switch_entity_id": "switch.adaptive_lighting_ma_kitchen_all_lights",
    }
    assert getattr(overhead_group, "_adaptive_lighting_switch_set") is None


def test_light_groups_module_exposes_adaptive_lighting_diagnostics_attribute() -> None:
    """Light group attributes should explain AL association state for debugging."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "adaptive_lighting_mode": "manage",
                "adaptive_lighting_manage_all_lights": True,
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    module = _light_group_runtime_module()

    controllers = module.build_runtime_controllers(
        area_config, make_coordinator(snapshot), snapshot
    )
    all_group = next(
        controller
        for controller in controllers
        if getattr(controller, "category") == "all_lights"
    )

    assert _attrs(all_group)["adaptive_lighting"] == {
        "mode": "manage",
        "role": "all_lights",
        "active": True,
        "reason": "associated",
        "main_switch_entity_id": "switch.adaptive_lighting_ma_kitchen_all_lights",
    }


@pytest.mark.asyncio
async def test_light_group_runtime_controller_exposes_host_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concrete runtime controllers should satisfy the shared host protocol."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    coordinator = make_coordinator(snapshot)
    coordinator.hass.states.get.return_value.state = "on"
    controller = next(
        candidate
        for candidate in _light_group_runtime_module().build_runtime_controllers(
            area_config, coordinator, snapshot
        )
        if candidate.category == "overhead_lights"
    )
    native_helper = "light.magic_areas_native_kitchen_overhead"
    monkeypatch.setattr(
        controller,
        "_control_target_entity_id",
        Mock(return_value=native_helper),
    )

    assert controller.name == "Kitchen overhead_lights light runtime"
    assert controller.unique_id == controller._native_control_target_unique_id
    assert controller.entity_id == native_helper
    assert controller.is_on is True
    assert controller.controlling is True
    assert controller._echo_state.owner_id == controller.unique_id
    assert await controller.async_get_last_state() is None

    remove_listener = Mock()
    controller.track_group_listener(remove_listener, "contract_test")
    assert controller._listener_registry.count == 1
    controller.cleanup()
    remove_listener.assert_called_once_with()
    controller.async_write_ha_state()


def test_light_groups_module_builds_managed_adaptive_lighting_configs() -> None:
    """Selected manage-mode roles should compile into desired AL configs."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "task_lights": ["light.task_1"],
                "adaptive_lighting_mode": "manage",
                "adaptive_lighting_managed_roles": ["overhead_lights"],
            }
        },
        entities={
            "light": [
                {"entity_id": "light.overhead_1"},
                {"entity_id": "light.task_1"},
            ]
        },
    )
    module = _managed_adaptive_lighting_module()

    configs = module.desired_managed_adaptive_lighting_configs(area_config, snapshot)

    assert len(configs) == 1
    assert configs[0].name == "MA Kitchen overhead"
    assert configs[0].role == "overhead_lights"
    assert configs[0].light_entity_ids == ("light.overhead_1",)


def test_light_groups_module_builds_managed_adaptive_lighting_all_lights_config() -> None:
    """Opted-in all-lights management should compile a room-level AL config."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "task_lights": ["light.task_1"],
                "adaptive_lighting_mode": "manage",
                "adaptive_lighting_manage_all_lights": True,
                "adaptive_lighting_managed_roles": [],
            }
        },
        entities={
            "light": [
                {"entity_id": "light.overhead_1"},
                {"entity_id": "light.task_1"},
                {"entity_id": "light.unassigned_1"},
            ]
        },
    )
    module = _managed_adaptive_lighting_module()

    configs = module.desired_managed_adaptive_lighting_configs(area_config, snapshot)

    assert len(configs) == 1
    assert configs[0].name == "MA Kitchen all lights"
    assert configs[0].role == "all_lights"
    assert configs[0].light_entity_ids == (
        "light.overhead_1",
        "light.task_1",
        "light.unassigned_1",
    )


def test_light_groups_module_does_not_build_all_lights_adaptive_lighting_by_default() -> None:
    """Manage mode should not create a room-level AL config without the gate."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "task_lights": ["light.task_1"],
                "adaptive_lighting_mode": "manage",
                "adaptive_lighting_managed_roles": ["task_lights"],
            }
        },
        entities={
            "light": [
                {"entity_id": "light.overhead_1"},
                {"entity_id": "light.task_1"},
                {"entity_id": "light.unassigned_1"},
            ]
        },
    )
    module = _managed_adaptive_lighting_module()

    configs = module.desired_managed_adaptive_lighting_configs(area_config, snapshot)

    assert [config.role for config in configs] == ["task_lights"]


def test_light_groups_module_registers_default_control_groups() -> None:
    """Light module should register area-scoped default control-group definitions."""
    area_config = make_area_config()
    entities_by_domain = {
        "light": [
            {"entity_id": "light.overhead_1"},
            {"entity_id": "light.task_1"},
        ]
    }
    feature_configs = {
        MagicAreasFeatures.LIGHT_GROUPS: {
            "overhead_lights": ["light.overhead_1"],
            "overhead_lights_states": ["occupied", "bright"],
            "overhead_lights_act_on": ["occupancy", "state"],
            "task_lights": ["light.task_1"],
            "task_lights_states": ["occupied"],
            "task_lights_act_on": ["occupancy"],
        }
    }
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs=feature_configs,
        entities=entities_by_domain,
    )
    registry = GroupRegistry()
    snapshot.group_registry = registry
    coordinator = make_coordinator(snapshot)
    module = get_module("light_groups")
    module.build_entities(area_config, coordinator, snapshot)

    registered = registry.get_for_area(area_config.id)
    registered_ids = sorted(group.definition.group_id for group in registered)
    assert registered_ids == [
        "light_groups_area-1_all_lights",
        "light_groups_area-1_overhead_lights",
        "light_groups_area-1_task_lights",
    ]


def test_light_groups_all_definition_includes_unassigned_lights() -> None:
    """ALL light-group definition should include every area light."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
            }
        },
        entities={
            "light": [
                {"entity_id": "light.overhead_1"},
                {"entity_id": "light.unassigned_1"},
            ]
        },
    )
    module = get_module("light_groups")
    registry = GroupRegistry()
    snapshot.group_registry = registry
    module.build_entities(area_config, make_coordinator(snapshot), snapshot)

    groups_by_id = {
        group.definition.group_id: group.definition
        for group in registry.get_for_area(area_config.id)
    }
    assert set(groups_by_id["light_groups_area-1_all_lights"].members) == {
        "light.overhead_1",
        "light.unassigned_1",
    }
    assert set(groups_by_id["light_groups_area-1_overhead_lights"].members) == {
        "light.overhead_1"
    }


def test_light_groups_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Light module should replace prior light_groups policy entries on rebuild."""
    area_config = make_area_config()
    module = get_module("light_groups")
    registry = GroupRegistry()

    initial_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
                "task_lights": ["light.task_1"],
                "task_lights_states": ["occupied"],
            }
        },
        entities={
            "light": [{"entity_id": "light.overhead_1"}, {"entity_id": "light.task_1"}]
        },
    )
    updated_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    initial_snapshot.group_registry = registry
    updated_snapshot.group_registry = registry
    module.build_entities(
        area_config, make_coordinator(initial_snapshot), initial_snapshot
    )
    module.build_entities(
        area_config, make_coordinator(updated_snapshot), updated_snapshot
    )

    group_ids = {
        group.definition.group_id for group in registry.get_for_area(area_config.id)
    }
    assert "light_groups_area-1_overhead_lights" in group_ids
    assert "light_groups_area-1_task_lights" not in group_ids


def test_light_groups_module_clears_stale_groups_when_no_lights_remain() -> None:
    """Light module should clear stale light_groups entries when no lights remain."""
    area_config = make_area_config()
    module = get_module("light_groups")
    registry = GroupRegistry()

    initial_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    updated_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
            }
        },
        entities={},
    )
    initial_snapshot.group_registry = registry
    updated_snapshot.group_registry = registry
    module.build_entities(
        area_config, make_coordinator(initial_snapshot), initial_snapshot
    )
    module.build_entities(
        area_config, make_coordinator(updated_snapshot), updated_snapshot
    )

    group_ids = {
        group.definition.group_id for group in registry.get_for_area(area_config.id)
    }
    assert "light_groups_area-1_all_lights" not in group_ids
    assert "light_groups_area-1_overhead_lights" not in group_ids


def test_light_groups_module_declares_native_light_helper_surfaces() -> None:
    """Light groups should declare exact native HA helper surfaces by role."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
                "task_lights": ["light.task_1"],
                "task_lights_states": ["occupied"],
            }
        },
        entities={
            "light": [
                {"entity_id": "light.overhead_1"},
                {"entity_id": "light.task_1"},
                {"entity_id": "light.unassigned_1"},
            ]
        },
    )
    module = get_module("light_groups")

    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    helper_surfaces = [
        surface for surface in surfaces if isinstance(surface, ConfigEntryHelperSurface)
    ]
    label_surfaces = [
        surface for surface in surfaces if isinstance(surface, LabelSurface)
    ]
    surfaces_by_id = {surface.unique_id: surface for surface in helper_surfaces}
    assert sorted(surfaces_by_id) == [
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_all_lights",
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_overhead_lights",
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_task_lights",
    ]
    labels_by_name = {surface.name: surface for surface in label_surfaces}
    assert sorted(labels_by_name) == [
        "ma:accent",
        "ma:overhead",
        "ma:sleep",
        "ma:task",
    ]
    assert labels_by_name["ma:overhead"].entity_ids == ("light.overhead_1",)
    assert labels_by_name["ma:task"].entity_ids == ("light.task_1",)
    assert labels_by_name["ma:sleep"].entity_ids == ()
    assert labels_by_name["ma:accent"].entity_ids == ()
    assert labels_by_name["ma:accent"].prune_entity_ids == (
        "light.overhead_1",
        "light.task_1",
        "light.unassigned_1",
    )
    assert surfaces_by_id[
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_all_lights"
    ].options["entities"] == [
        "light.overhead_1",
        "light.task_1",
        "light.unassigned_1",
    ]
    assert surfaces_by_id[
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_all_lights"
    ].entity_name == "All Lights"
    assert surfaces_by_id[
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_overhead_lights"
    ].options["entities"] == ["light.overhead_1"]
    assert surfaces_by_id[
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_overhead_lights"
    ].entity_name == "Overhead Lights"


def test_light_groups_module_declares_adaptive_ambient_rise_signal_surface() -> None:
    """Adaptive ambient-rise opt-in should compile to a managed Trend helper."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "brightness_mode": "adaptive",
                "adaptive_require_ambient_rise": True,
                "ambient_rise_window_seconds": 120,
                "ambient_rise_min_delta": 30,
                "outside_lux_inside_entity": "sensor.kitchen_lux",
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    module = get_module("light_groups")

    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    signal_surfaces = [
        surface for surface in surfaces if isinstance(surface, SignalHelperSurface)
    ]
    assert len(signal_surfaces) == 1
    surface = signal_surfaces[0]
    assert surface.unique_id == (
        "magic_areas:entry-1:area-1:signals:signal_helper:trend_ambient_rise"
    )
    assert surface.domain == "trend"
    assert surface.title == "Magic Areas Signals Kitchen Trend Ambient Rise"
    assert surface.source_entity_id == "sensor.kitchen_lux"
    assert surface.options == {
        "name": "Magic Areas Signals Kitchen Trend Ambient Rise",
        "entity_id": "sensor.kitchen_lux",
        "invert": False,
        "max_samples": 10,
        "min_samples": 2,
        "min_gradient": 0.25,
        "sample_duration": 120,
    }
    assert surface.area_id == "area-1"
    assert surface.device_identifier == ("magic_areas", "magic_area_device_area-1")
    assert surface.device_name == "Kitchen"


def test_light_groups_module_skips_ambient_rise_signal_without_complete_opt_in() -> None:
    """Signal helpers should not appear unless adaptive ambient-rise has a source."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "brightness_mode": "advisory",
                "adaptive_require_ambient_rise": True,
                "ambient_rise_window_seconds": 120,
                "ambient_rise_min_delta": 30,
                "outside_lux_inside_entity": "sensor.kitchen_lux",
            }
        },
        entities={"light": [{"entity_id": "light.overhead_1"}]},
    )
    module = get_module("light_groups")

    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    assert not any(isinstance(surface, SignalHelperSurface) for surface in surfaces)


def test_light_groups_module_removes_native_surfaces_when_no_lights_remain() -> None:
    """Light managed helper surfaces should be absent without source lights."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.LIGHT_GROUPS},
        feature_configs={
            MagicAreasFeatures.LIGHT_GROUPS: {
                "overhead_lights": ["light.overhead_1"],
                "overhead_lights_states": ["occupied"],
            }
        },
        entities={},
    )
    module = get_module("light_groups")

    assert module.desired_managed_surfaces(area_config, snapshot) == []
