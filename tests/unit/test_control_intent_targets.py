"""Tests for pure control intent target contracts."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr

from custom_components.magic_areas.core.control_intents import (
    ControlTargetKind,
    ControlTargetPrecision,
    ControlTargetSource,
    RoleTarget,
    custom_control_label_name,
    resolve_custom_control_target,
    resolve_role_target,
)


def test_label_role_target_models_broad_ha_label_execution() -> None:
    """A broad role target can represent an HA label service target."""
    target = RoleTarget(
        role="sleep",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.LABEL,
        precision=ControlTargetPrecision.BROAD,
        source=ControlTargetSource.RECONCILED_LABEL,
        label_name="ma:sleep",
        label_id="ma_sleep",
        resolution_path=("label",),
    )

    assert target.is_executable
    assert target.uses_broad_label_target
    assert target.target_entity_ids == ()


def test_helper_role_target_models_exact_native_helper_execution() -> None:
    """An exact role target can execute through a native helper entity."""
    target = RoleTarget(
        role="sleep",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.HELPER_ENTITY,
        precision=ControlTargetPrecision.EXACT,
        source=ControlTargetSource.MANAGED_HELPER,
        helper_unique_id="magic_areas:entry:living_room:light_groups:config_entry_helper:light_group_sleep_lights",
        helper_entity_id="light.magic_areas_native_light_groups_living_room_sleep_lights",
        resolution_path=("managed_helper",),
    )

    assert target.is_executable
    assert not target.uses_broad_label_target
    assert target.target_entity_ids == (
        "light.magic_areas_native_light_groups_living_room_sleep_lights",
    )


def test_entity_subset_role_target_models_filtered_intersection_execution() -> None:
    """Filtered/intersection targets execute through explicit entity IDs."""
    target = RoleTarget(
        role="sleep+accent",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.ENTITY_SUBSET,
        precision=ControlTargetPrecision.FILTERED,
        source=ControlTargetSource.ENTITY_SUBSET,
        entity_ids=("light.tv_backlight",),
        resolution_path=("label:ma:sleep", "label:ma:accent", "intersection"),
        fallback_reason="label_intersection_not_supported_by_ha",
    )

    assert target.is_executable
    assert target.target_entity_ids == ("light.tv_backlight",)
    assert target.fallback_reason == "label_intersection_not_supported_by_ha"


def test_compatibility_role_target_models_hidden_policy_entity() -> None:
    """Compatibility targets preserve current hidden policy-entity fallback."""
    target = RoleTarget(
        role="all_lights",
        domain="light",
        area_id="living_room",
        kind=ControlTargetKind.COMPATIBILITY_ENTITY,
        precision=ControlTargetPrecision.COMPATIBILITY,
        source=ControlTargetSource.POLICY_ENTITY,
        compatibility_entity_id="light.magic_areas_light_groups_living_room_all_lights",
        resolution_path=("managed_helper_missing", "policy_entity"),
        fallback_reason="managed_helper_unavailable",
    )

    assert target.is_executable
    assert target.target_entity_ids == (
        "light.magic_areas_light_groups_living_room_all_lights",
    )


def test_resolve_role_target_prefers_exact_managed_helper(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime resolver should use exact helper surfaces ahead of labels."""
    monkeypatch.setattr(
        "custom_components.magic_areas.core.control_intents.targets.resolve_managed_surface_entity_id",
        lambda *_args, **_kwargs: "light.native_sleep_group",
    )

    target = resolve_role_target(
        hass,
        area_id="living_room",
        domain="light",
        role="sleep",
        area_entity_ids=("light.sleep_lamp",),
        label_name="ma:sleep",
        helper_unique_id="magic_areas:entry:living_room:light_groups:config_entry_helper:light_group_sleep_lights",
        helper_config_entry_domain="group",
    )

    assert target.kind is ControlTargetKind.HELPER_ENTITY
    assert target.precision is ControlTargetPrecision.EXACT
    assert target.source is ControlTargetSource.MANAGED_HELPER
    assert target.target_entity_ids == ("light.native_sleep_group",)


def test_resolve_role_target_filters_label_members_to_area_domain_boundary(
    hass: HomeAssistant,
) -> None:
    """Label resolution should not leak outside the supplied area/domain universe."""
    entity_registry = er.async_get(hass)
    sleep_lamp = entity_registry.async_get_or_create(
        "light",
        "test",
        "sleep_lamp",
    )
    overhead_lamp = entity_registry.async_get_or_create(
        "light",
        "test",
        "overhead_lamp",
    )
    other_room_sleep_lamp = entity_registry.async_get_or_create(
        "light",
        "test",
        "other_room_sleep_lamp",
    )
    sleep_switch = entity_registry.async_get_or_create(
        "switch",
        "test",
        "sleep_switch",
    )
    label = lr.async_get(hass).async_create("ma:sleep")
    for entry in (sleep_lamp, other_room_sleep_lamp, sleep_switch):
        entity_registry.async_update_entity(entry.entity_id, labels={label.label_id})

    target = resolve_role_target(
        hass,
        area_id="living_room",
        domain="light",
        role="sleep",
        area_entity_ids=(sleep_lamp.entity_id, overhead_lamp.entity_id),
        label_name="ma:sleep",
    )

    assert target.kind is ControlTargetKind.ENTITY_SUBSET
    assert target.precision is ControlTargetPrecision.FILTERED
    assert target.source is ControlTargetSource.RECONCILED_LABEL
    assert target.entity_ids == (sleep_lamp.entity_id,)
    assert target.fallback_reason == "ha_label_intersection_not_supported"


def test_resolve_role_target_can_emit_broad_label_when_explicitly_allowed(
    hass: HomeAssistant,
) -> None:
    """Broad label targets should be opt-in because HA labels are union targets."""
    label = lr.async_get(hass).async_create("ma:sleep")

    target = resolve_role_target(
        hass,
        area_id="global",
        domain="light",
        role="sleep",
        area_entity_ids=(),
        label_name="ma:sleep",
        allow_broad_label_target=True,
    )

    assert target.kind is ControlTargetKind.LABEL
    assert target.precision is ControlTargetPrecision.BROAD
    assert target.label_id == label.label_id
    assert target.is_executable


def test_resolve_role_target_falls_back_to_filtered_compatibility_members(
    hass: HomeAssistant,
) -> None:
    """Compatibility member fallback should still stay inside area/domain scope."""
    target = resolve_role_target(
        hass,
        area_id="living_room",
        domain="light",
        role="accent",
        area_entity_ids=("light.accent_lamp", "light.other_area_member"),
        fallback_entity_ids=(
            "light.accent_lamp",
            "switch.not_a_light",
            "light.not_in_area",
        ),
        fallback_source=ControlTargetSource.GROUP_REGISTRY,
    )

    assert target.kind is ControlTargetKind.ENTITY_SUBSET
    assert target.source is ControlTargetSource.GROUP_REGISTRY
    assert target.entity_ids == ("light.accent_lamp",)


def test_resolve_role_target_uses_policy_entity_as_last_compatibility_target(
    hass: HomeAssistant,
) -> None:
    """Hidden policy entities remain modelable as the final compatibility fallback."""
    target = resolve_role_target(
        hass,
        area_id="living_room",
        domain="light",
        role="all_lights",
        area_entity_ids=(),
        compatibility_entity_id="light.magic_areas_policy_living_room_all_lights",
    )

    assert target.kind is ControlTargetKind.COMPATIBILITY_ENTITY
    assert target.precision is ControlTargetPrecision.COMPATIBILITY
    assert target.source is ControlTargetSource.POLICY_ENTITY
    assert target.target_entity_ids == ("light.magic_areas_policy_living_room_all_lights",)


def test_custom_control_label_name_uses_existing_label_convention() -> None:
    """Custom control labels should have one canonical naming function."""
    assert custom_control_label_name("control.task") == "ma:control:task"
    assert custom_control_label_name("TV Viewing Mode") == "ma:control:tv-viewing-mode"
    assert custom_control_label_name("") == "ma:control:custom"


def test_resolve_custom_control_target_prefers_reconciled_label_members(
    hass: HomeAssistant,
) -> None:
    """Custom controls should resolve through labels before config member fallback."""
    entity_registry = er.async_get(hass)
    labelled_lamp = entity_registry.async_get_or_create(
        "light",
        "test",
        "labelled_lamp",
    )
    fallback_lamp = entity_registry.async_get_or_create(
        "light",
        "test",
        "fallback_lamp",
    )
    label = lr.async_get(hass).async_create("ma:control:task")
    entity_registry.async_update_entity(labelled_lamp.entity_id, labels={label.label_id})

    target = resolve_custom_control_target(
        hass,
        area_id="living_room",
        domain="light",
        group_id="control.task",
        area_entity_ids=(labelled_lamp.entity_id, fallback_lamp.entity_id),
        fallback_entity_ids=(fallback_lamp.entity_id,),
    )

    assert target.kind is ControlTargetKind.ENTITY_SUBSET
    assert target.source is ControlTargetSource.RECONCILED_LABEL
    assert target.label_name == "ma:control:task"
    assert target.entity_ids == (labelled_lamp.entity_id,)


def test_resolve_custom_control_target_falls_back_to_config_members(
    hass: HomeAssistant,
) -> None:
    """Config member lists remain a compatibility fallback during migration."""
    target = resolve_custom_control_target(
        hass,
        area_id="living_room",
        domain="switch",
        group_id="control.vent",
        area_entity_ids=("switch.vent", "switch.other"),
        fallback_entity_ids=("switch.vent", "light.not_switch", "switch.not_in_area"),
    )

    assert target.kind is ControlTargetKind.ENTITY_SUBSET
    assert target.source is ControlTargetSource.CONFIG_RECONCILIATION
    assert target.entity_ids == ("switch.vent",)
