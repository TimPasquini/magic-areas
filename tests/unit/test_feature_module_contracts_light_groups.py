"""Contract tests for light groups feature module."""

from __future__ import annotations

from custom_components.magic_areas.core.controls import GroupRegistry
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    MAIN_SWITCH,
    SLEEP_SWITCH,
)
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    LabelSurface,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

from .feature_module_contracts_testkit import (
    get_module,
    make_area_config,
    make_coordinator,
    make_snapshot,
)


def test_light_groups_module_builds_expected_entities() -> None:
    """Light groups module should build overhead + all groups."""
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
        "light.magic_areas_light_groups_kitchen_all_lights",
        "light.magic_areas_light_groups_kitchen_overhead_lights",
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
    module = get_module("light_groups")

    entities = module.build_entities(area_config, make_coordinator(snapshot), snapshot)
    groups = {
        entity.entity_id: entity
        for entity in entities
        if entity.entity_id.startswith("light.")
    }

    all_group = groups["light.magic_areas_light_groups_kitchen_all_lights"]
    overhead_group = groups["light.magic_areas_light_groups_kitchen_overhead_lights"]

    assert getattr(all_group, "_adaptive_lighting_switch_set") is None
    switch_set = getattr(overhead_group, "_adaptive_lighting_switch_set")
    assert switch_set is not None
    assert switch_set.role == "overhead_lights"


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
        "magic_areas:entry-1:area-1:light_groups:config_entry_helper:light_group_overhead_lights"
    ].options["entities"] == ["light.overhead_1"]


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
