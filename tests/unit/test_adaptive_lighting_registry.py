"""Tests for HA registry-backed Adaptive Lighting discovery."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr

from custom_components.magic_areas.core.control_intents import (
    adaptive_lighting_switch_entity_ids,
    switch_set_from_hass_registry,
    switch_sets_from_hass_registry,
)


def _register_switch_set(
    hass: HomeAssistant,
    name: str,
    *,
    area_id: str | None = None,
    labels: set[str] | None = None,
) -> dict[str, str]:
    """Register one conventional Adaptive Lighting switch set."""
    entity_registry = er.async_get(hass)
    refs = adaptive_lighting_switch_entity_ids(name)
    for entity_id in refs.values():
        domain, object_id = entity_id.split(".", 1)
        entry = entity_registry.async_get_or_create(
            domain,
            "test",
            object_id,
            suggested_object_id=object_id,
        )
        entity_registry.async_update_entity(
            entry.entity_id,
            area_id=area_id,
            labels=labels or set(),
        )
    return refs


def test_hass_registry_discovery_resolves_one_area_switch_set(
    hass: HomeAssistant,
) -> None:
    """Registry binding should resolve a complete switch set assigned to the area."""
    refs = _register_switch_set(hass, "Kitchen", area_id="kitchen")
    _register_switch_set(hass, "Bedroom", area_id="bedroom")

    switch_set = switch_set_from_hass_registry(
        hass,
        area_id="kitchen",
        role="overhead_lights",
    )

    assert switch_set is not None
    assert switch_set.area_id == "kitchen"
    assert switch_set.role == "overhead_lights"
    assert switch_set.entity_ids == tuple(refs.values())


def test_hass_registry_discovery_rejects_ambiguous_area_matches(
    hass: HomeAssistant,
) -> None:
    """Registry binding should not pick between multiple complete area matches."""
    _register_switch_set(hass, "Kitchen", area_id="kitchen")
    _register_switch_set(hass, "Dining", area_id="kitchen")

    assert switch_set_from_hass_registry(hass, area_id="kitchen") is None


def test_hass_registry_discovery_can_scope_by_required_label_name(
    hass: HomeAssistant,
) -> None:
    """Required labels should narrow discovery to the intended AL switch set."""
    label = lr.async_get(hass).async_create("ma:overhead")
    refs = _register_switch_set(
        hass,
        "Kitchen Overhead",
        labels={label.label_id},
    )
    _register_switch_set(hass, "Kitchen Sleep")

    switch_set = switch_set_from_hass_registry(
        hass,
        area_id="kitchen",
        role="overhead_lights",
        required_label_names=("ma:overhead",),
    )

    assert switch_set is not None
    assert switch_set.entity_ids == tuple(refs.values())


def test_hass_registry_discovery_rejects_missing_label_name(
    hass: HomeAssistant,
) -> None:
    """Missing required labels should fail closed instead of falling back to area."""
    _register_switch_set(hass, "Kitchen", area_id="kitchen")

    assert (
        switch_set_from_hass_registry(
            hass,
            area_id="kitchen",
            required_label_names=("ma:missing",),
        )
        is None
    )


def test_hass_registry_discovery_lists_complete_area_switch_sets(
    hass: HomeAssistant,
) -> None:
    """Registry binding should list all complete same-area switch sets for config UI."""
    kitchen_refs = _register_switch_set(hass, "Kitchen", area_id="kitchen")
    dining_refs = _register_switch_set(hass, "Dining", area_id="kitchen")
    _register_switch_set(hass, "Bedroom", area_id="bedroom")

    switch_sets = switch_sets_from_hass_registry(hass, area_id="kitchen")

    assert tuple(switch_set.entity_ids for switch_set in switch_sets) == (
        tuple(dining_refs.values()),
        tuple(kitchen_refs.values()),
    )
