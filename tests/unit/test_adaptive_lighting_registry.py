"""Tests for HA registry-backed Adaptive Lighting discovery."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.core.control_intents import (
    ADAPTIVE_LIGHTING_DOMAIN,
    adaptive_lighting_switch_entity_ids,
    managed_adaptive_lighting_config,
    managed_switch_set_from_hass_registry,
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


def test_managed_hass_registry_discovery_resolves_actual_al_switches(
    hass: HomeAssistant,
) -> None:
    """Managed configs should resolve actual AL switch entities by config entry."""
    desired = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling",),
    )
    assert desired is not None
    entry = MockConfigEntry(
        domain=ADAPTIVE_LIGHTING_DOMAIN,
        data=desired.data,
        options={"lights": ["light.ceiling"]},
        title=desired.name,
        unique_id=desired.name,
    )
    entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    actual_refs = {
        "main": "switch.ma_living_room_overhead_adaptive_lighting_ma_living_room_overhead",
        "sleep": (
            "switch.adaptive_lighting_ma_living_room_overhead_"
            "adaptive_lighting_sleep_mode_ma_living_room_overhead"
        ),
        "adapt_brightness": (
            "switch.adaptive_lighting_ma_living_room_overhead_"
            "adaptive_lighting_adapt_brightness_ma_living_room_overhead"
        ),
        "adapt_color": (
            "switch.adaptive_lighting_ma_living_room_overhead_"
            "adaptive_lighting_adapt_color_ma_living_room_overhead"
        ),
    }
    for entity_id in actual_refs.values():
        domain, object_id = entity_id.split(".", 1)
        registry_entry = entity_registry.async_get_or_create(
            domain,
            ADAPTIVE_LIGHTING_DOMAIN,
            object_id,
            config_entry=entry,
            suggested_object_id=object_id,
        )
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            area_id="living_room",
        )

    switch_set = managed_switch_set_from_hass_registry(hass, desired)

    assert switch_set is not None
    assert switch_set.entity_ids == tuple(actual_refs.values())


def test_managed_hass_registry_discovery_handles_ma_adaptive_lighting_names(
    hass: HomeAssistant,
) -> None:
    """Managed discovery should handle AL's verbose IDs for MA Adaptive Lighting rooms."""
    desired = managed_adaptive_lighting_config(
        area_id="adaptive_lighting_room",
        area_name="Adaptive Lighting Room",
        role="all_lights",
        light_entity_ids=("light.overhead", "light.lamp"),
    )
    assert desired is not None
    entry = MockConfigEntry(
        domain=ADAPTIVE_LIGHTING_DOMAIN,
        data=desired.data,
        options={"lights": ["light.overhead", "light.lamp"]},
        title=desired.name,
        unique_id=desired.name,
    )
    entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    actual_refs = {
        "main": (
            "switch.ma_adaptive_lighting_room_all_lights_"
            "adaptive_lighting_ma_adaptive_lighting_room_all_lights"
        ),
        "sleep": (
            "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
            "adaptive_lighting_sleep_mode_ma_adaptive_lighting_room_all_lights"
        ),
        "adapt_brightness": (
            "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
            "adaptive_lighting_adapt_brightness_ma_adaptive_lighting_room_all_lights"
        ),
        "adapt_color": (
            "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
            "adaptive_lighting_adapt_color_ma_adaptive_lighting_room_all_lights"
        ),
    }
    for entity_id in actual_refs.values():
        domain, object_id = entity_id.split(".", 1)
        registry_entry = entity_registry.async_get_or_create(
            domain,
            ADAPTIVE_LIGHTING_DOMAIN,
            object_id,
            config_entry=entry,
            suggested_object_id=object_id,
        )
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            area_id="adaptive_lighting_room",
        )

    switch_set = managed_switch_set_from_hass_registry(hass, desired)

    assert switch_set is not None
    assert switch_set.entity_ids == tuple(actual_refs.values())
