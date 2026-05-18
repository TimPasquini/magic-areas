"""Tests for HA-bound managed Adaptive Lighting reconciliation."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.core.control_intents import (
    ADAPTIVE_LIGHTING_DOMAIN,
    ATTR_LIGHTS,
    MANAGED_ADAPTIVE_LIGHTING_AREA_ID,
    MANAGED_ADAPTIVE_LIGHTING_ROLE,
    managed_adaptive_lighting_config,
)
from custom_components.magic_areas.coordinator import (
    async_reconcile_managed_adaptive_lighting,
)
from tests.unit.adaptive_lighting_testkit import (
    setup_adaptive_lighting_config_entry_harness,
)


async def test_reconciler_creates_missing_managed_adaptive_lighting_entry(
    hass: HomeAssistant,
) -> None:
    """Manage mode should create a durable MA-owned AL config entry."""
    desired = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling", "light.lamp"),
    )
    assert desired is not None

    await async_reconcile_managed_adaptive_lighting(
        hass=hass,
        desired_configs=(desired,),
    )

    entries = hass.config_entries.async_entries(ADAPTIVE_LIGHTING_DOMAIN)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.title == "MA Living Room overhead"
    assert entry.unique_id == "MA Living Room overhead"
    assert entry.source == SOURCE_USER
    assert entry.data == {
        CONF_NAME: "MA Living Room overhead",
        MANAGED_ADAPTIVE_LIGHTING_AREA_ID: "living_room",
        MANAGED_ADAPTIVE_LIGHTING_ROLE: "overhead_lights",
    }
    assert entry.options == {ATTR_LIGHTS: ["light.ceiling", "light.lamp"]}


async def test_reconciler_updates_membership_without_clobbering_al_options(
    hass: HomeAssistant,
) -> None:
    """Membership updates should preserve Adaptive Lighting-owned tuning options."""
    harness = setup_adaptive_lighting_config_entry_harness(hass)
    entry = await harness.async_create_entry(
        name="MA Living Room overhead",
        options={
            ATTR_LIGHTS: ["light.old_member"],
            "min_brightness": 20,
            "sleep_rgb_or_color_temp": "color_temp",
        },
    )
    desired = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling", "light.lamp"),
    )
    assert desired is not None

    await async_reconcile_managed_adaptive_lighting(
        hass=hass,
        desired_configs=(desired,),
    )

    assert entry.options == {
        ATTR_LIGHTS: ["light.ceiling", "light.lamp"],
        "min_brightness": 20,
        "sleep_rgb_or_color_temp": "color_temp",
    }


async def test_reconciler_deletes_stale_owned_entry_but_ignores_user_entry(
    hass: HomeAssistant,
) -> None:
    """Stale MA-owned AL entries should be removed without touching user entries."""
    harness = setup_adaptive_lighting_config_entry_harness(hass)
    stale = await harness.async_create_entry(
        name="MA Living Room overhead",
        options={ATTR_LIGHTS: ["light.old_member"]},
    )
    user_entry = MockConfigEntry(
        domain=ADAPTIVE_LIGHTING_DOMAIN,
        title="MA Living Room task",
        unique_id="user-owned-id",
        data={CONF_NAME: "MA Living Room task"},
        options={ATTR_LIGHTS: ["light.user"]},
    )
    user_entry.add_to_hass(hass)

    await async_reconcile_managed_adaptive_lighting(
        hass=hass,
        desired_configs=(),
    )

    assert hass.config_entries.async_get_entry(stale.entry_id) is None
    assert hass.config_entries.async_get_entry(user_entry.entry_id) is user_entry


async def test_reconciler_scopes_stale_cleanup_by_area(hass: HomeAssistant) -> None:
    """Per-area reconciliation should not remove another area's managed AL entry."""
    harness = setup_adaptive_lighting_config_entry_harness(hass)
    other_area = await harness.async_create_entry(
        name="MA Bedroom overhead",
        area_id="bedroom",
        role="overhead_lights",
        options={ATTR_LIGHTS: ["light.bedroom"]},
    )

    await async_reconcile_managed_adaptive_lighting(
        hass=hass,
        area_id="living_room",
        desired_configs=(),
    )

    assert hass.config_entries.async_get_entry(other_area.entry_id) is other_area


async def test_reconciler_assigns_registry_metadata_to_managed_al_entities(
    hass: HomeAssistant,
) -> None:
    """Managed AL switch entities should attach to the HA area only."""
    harness = setup_adaptive_lighting_config_entry_harness(hass)
    entry = await harness.async_create_entry(
        name="MA Living Room overhead",
        area_id="living_room",
        role="overhead_lights",
        options={ATTR_LIGHTS: ["light.ceiling"]},
    )
    entity_registry = er.async_get(hass)
    switch_entry = entity_registry.async_get_or_create(
        "switch",
        ADAPTIVE_LIGHTING_DOMAIN,
        "magic_areas_living_room_overhead",
        config_entry=entry,
        suggested_object_id="adaptive_lighting_magic_areas_living_room_overhead",
    )
    desired = managed_adaptive_lighting_config(
        area_id="living_room",
        area_name="Living Room",
        role="overhead_lights",
        light_entity_ids=("light.ceiling",),
    )
    assert desired is not None

    await async_reconcile_managed_adaptive_lighting(
        hass=hass,
        area_id="living_room",
        desired_configs=(desired,),
    )

    updated = entity_registry.async_get(switch_entry.entity_id)
    assert updated is not None
    assert updated.area_id == "living_room"
    assert updated.device_id is None
