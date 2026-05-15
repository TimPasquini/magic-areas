"""Contract tests for group/control oriented feature modules."""

from __future__ import annotations

from typing import cast

from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN

from custom_components.magic_areas.config_keys.area import CONF_CLIMATE_CONTROL_ENTITY_ID
from custom_components.magic_areas.core.runtime_model import (
    ConfigEntryHelperSurface,
    ManagedSurface,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

from .feature_module_contracts_testkit import get_module, make_area_config, make_coordinator, make_snapshot


def _helper_surfaces(surfaces: list[ManagedSurface]) -> list[ConfigEntryHelperSurface]:
    """Return config-entry helper surfaces with runtime assertions for tests."""
    assert all(isinstance(surface, ConfigEntryHelperSurface) for surface in surfaces)
    return cast(list[ConfigEntryHelperSurface], surfaces)


def test_fan_groups_module_builds_group_and_control_switch() -> None:
    """Fan groups module should build control switch and native helper surface."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={},
        entities={FAN_DOMAIN: [{"entity_id": "fan.ceiling_1"}]},
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("fan_groups")
    entities = module.build_entities(area_config, coordinator, snapshot)
    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    entity_ids = sorted(entity.entity_id for entity in entities)
    assert entity_ids == ["switch.magic_areas_fan_groups_kitchen_fan_control"]
    assert len(surfaces) == 1
    helper_surfaces = _helper_surfaces(surfaces)
    assert helper_surfaces[0].unique_id == (
        "magic_areas:entry-1:area-1:fan_groups:config_entry_helper:fan_group"
    )
    assert helper_surfaces[0].domain == "group"
    assert helper_surfaces[0].options["group_type"] == FAN_DOMAIN
    assert helper_surfaces[0].options["entities"] == ["fan.ceiling_1"]


def test_fan_groups_module_registers_default_control_group() -> None:
    """Fan module should register area-scoped default control-group definitions."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={MagicAreasFeatures.FAN_GROUPS: {"required_state": "occupied"}},
        entities={FAN_DOMAIN: [{"entity_id": "fan.ceiling_1"}]},
    )
    coordinator = make_coordinator(snapshot)
    module = get_module("fan_groups")
    module.build_entities(area_config, coordinator, snapshot)

    groups = snapshot.group_registry.get_for_area(area_config.id)
    assert any(
        group.definition.group_id
        == "magic_areas:entry-1:area-1:fan_groups:config_entry_helper:fan_group"
        for group in groups
    )


def test_fan_groups_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Fan module should clear stale fan_groups entries when no fan entities remain."""
    area_config = make_area_config()
    module = get_module("fan_groups")

    initial_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={MagicAreasFeatures.FAN_GROUPS: {"required_state": "occupied"}},
        entities={FAN_DOMAIN: [{"entity_id": "fan.ceiling_1"}]},
    )
    updated_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.FAN_GROUPS},
        feature_configs={MagicAreasFeatures.FAN_GROUPS: {"required_state": "occupied"}},
        entities={},
    )
    updated_snapshot.group_registry = initial_snapshot.group_registry

    module.build_entities(area_config, make_coordinator(initial_snapshot), initial_snapshot)
    module.build_entities(area_config, make_coordinator(updated_snapshot), updated_snapshot)

    group_ids = {
        group.definition.group_id
        for group in initial_snapshot.group_registry.get_for_area(area_config.id)
    }
    assert (
        "magic_areas:entry-1:area-1:fan_groups:config_entry_helper:fan_group"
        not in group_ids
    )


def test_media_player_groups_module_builds_group_and_control_switch() -> None:
    """Media player groups module should build control switch and helper surface."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities={MEDIA_PLAYER_DOMAIN: [{"entity_id": "media_player.tv"}]},
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("media_player_groups")
    entities = module.build_entities(area_config, coordinator, snapshot)
    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    entity_ids = sorted(entity.entity_id for entity in entities)
    assert entity_ids == ["switch.magic_areas_media_player_groups_kitchen_media_player_control"]
    assert len(surfaces) == 1
    helper_surfaces = _helper_surfaces(surfaces)
    assert helper_surfaces[0].unique_id == (
        "magic_areas:entry-1:area-1:media_player_groups:config_entry_helper:"
        "media_player_group"
    )
    assert helper_surfaces[0].domain == "group"
    assert helper_surfaces[0].options["group_type"] == MEDIA_PLAYER_DOMAIN
    assert helper_surfaces[0].options["entities"] == ["media_player.tv"]


def test_media_player_groups_module_registers_default_control_group() -> None:
    """Media-player module should register area-scoped default control-group definitions."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities={MEDIA_PLAYER_DOMAIN: [{"entity_id": "media_player.tv"}]},
    )
    coordinator = make_coordinator(snapshot)
    module = get_module("media_player_groups")
    module.build_entities(area_config, coordinator, snapshot)

    groups = snapshot.group_registry.get_for_area(area_config.id)
    assert any(
        group.definition.group_id
        == "magic_areas:entry-1:area-1:media_player_groups:config_entry_helper:"
        "media_player_group"
        for group in groups
    )


def test_media_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Media module should clear stale media_player_groups entries on rebuild."""
    area_config = make_area_config()
    module = get_module("media_player_groups")

    initial_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities={MEDIA_PLAYER_DOMAIN: [{"entity_id": "media_player.tv"}]},
    )
    updated_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.MEDIA_PLAYER_GROUPS},
        feature_configs={},
        entities={},
    )
    updated_snapshot.group_registry = initial_snapshot.group_registry

    module.build_entities(area_config, make_coordinator(initial_snapshot), initial_snapshot)
    module.build_entities(area_config, make_coordinator(updated_snapshot), updated_snapshot)

    group_ids = {
        group.definition.group_id
        for group in initial_snapshot.group_registry.get_for_area(area_config.id)
    }
    assert (
        "magic_areas:entry-1:area-1:media_player_groups:config_entry_helper:"
        "media_player_group"
        not in group_ids
    )


def test_cover_groups_module_builds_device_class_groups() -> None:
    """Cover groups module should declare native helper surfaces per device class."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.COVER_GROUPS},
        feature_configs={},
        entities={
            COVER_DOMAIN: [
                {"entity_id": "cover.blind_1", "device_class": "blind"},
                {"entity_id": "cover.other_1", "device_class": None},
            ]
        },
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("cover_groups")
    entities = module.build_entities(area_config, coordinator, snapshot)
    surfaces = module.desired_managed_surfaces(area_config, snapshot)

    assert entities == []
    helper_surfaces = _helper_surfaces(surfaces)
    assert sorted(surface.title for surface in helper_surfaces) == [
        "Magic Areas Cover Groups Kitchen Cover Group",
        "Magic Areas Cover Groups Kitchen Cover Group Blind",
    ]


def test_presence_hold_module_builds_switch() -> None:
    """Presence hold module should build the presence hold switch."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.PRESENCE_HOLD},
        feature_configs={},
        entities={},
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("presence_hold")
    entities = module.build_entities(area_config, coordinator, snapshot)

    assert [entity.entity_id for entity in entities] == ["switch.magic_areas_presence_hold_kitchen"]


def test_climate_control_module_builds_switch() -> None:
    """Climate control module should build the climate control switch."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={
            MagicAreasFeatures.CLIMATE_CONTROL: {CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.kitchen"}
        },
        entities={},
    )
    coordinator = make_coordinator(snapshot)

    module = get_module("climate_control")
    entities = module.build_entities(area_config, coordinator, snapshot)

    assert [entity.entity_id for entity in entities] == ["switch.magic_areas_climate_control_kitchen"]


def test_climate_control_module_registers_default_control_group() -> None:
    """Climate module should register default control-group definition."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={
            MagicAreasFeatures.CLIMATE_CONTROL: {CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.kitchen"}
        },
        entities={},
    )
    coordinator = make_coordinator(snapshot)
    module = get_module("climate_control")
    module.build_entities(area_config, coordinator, snapshot)

    groups = snapshot.group_registry.get_for_area(area_config.id)
    assert any(group.definition.group_id == "climate_control_area-1_climate_control" for group in groups)


def test_climate_module_replaces_stale_policy_groups_on_rebuild() -> None:
    """Climate module should clear stale climate_control entries when unset."""
    area_config = make_area_config()
    module = get_module("climate_control")

    initial_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={
            MagicAreasFeatures.CLIMATE_CONTROL: {CONF_CLIMATE_CONTROL_ENTITY_ID: "climate.kitchen"}
        },
        entities={},
    )
    updated_snapshot = make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={MagicAreasFeatures.CLIMATE_CONTROL: {}},
        entities={},
    )
    updated_snapshot.group_registry = initial_snapshot.group_registry

    module.build_entities(area_config, make_coordinator(initial_snapshot), initial_snapshot)
    module.build_entities(area_config, make_coordinator(updated_snapshot), updated_snapshot)

    group_ids = {
        group.definition.group_id
        for group in initial_snapshot.group_registry.get_for_area(area_config.id)
    }
    assert "climate_control_area-1_climate_control" not in group_ids


def test_climate_control_module_skips_switch_without_entity() -> None:
    """Climate module should not build switch when climate entity is unset."""
    area_config = make_area_config()
    snapshot = make_snapshot(
        enabled={MagicAreasFeatures.CLIMATE_CONTROL},
        feature_configs={MagicAreasFeatures.CLIMATE_CONTROL: {}},
        entities={},
    )
    coordinator = make_coordinator(snapshot)
    module = get_module("climate_control")

    entities = module.build_entities(area_config, coordinator, snapshot)
    assert entities == []
