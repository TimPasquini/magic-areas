"""Tests for the mocked Adaptive Lighting harness."""

from __future__ import annotations

from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.core import State

from custom_components.magic_areas.core.control_intents import (
    managed_adaptive_lighting_config,
    managed_adaptive_lighting_options,
)
from tests.unit.adaptive_lighting_testkit import (
    ADAPTIVE_LIGHTING_DOMAIN,
    EVENT_MANUAL_CONTROL,
    SERVICE_APPLY,
    SERVICE_CHANGE_SWITCH_SETTINGS,
    SERVICE_SET_MANUAL_CONTROL,
    setup_adaptive_lighting_config_entry_harness,
    setup_adaptive_lighting_harness,
)

ATTR_LIGHTS = "lights"


def _state(hass: HomeAssistant, entity_id: str) -> State:
    """Return a test state, failing clearly if the harness did not create it."""
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def test_harness_creates_behavior_switches_and_services(
    hass: HomeAssistant,
) -> None:
    """Harness should expose the Adaptive Lighting surfaces MA depends on."""
    harness = await setup_adaptive_lighting_harness(
        hass,
        name="Living Room",
        area_id="living_room",
        role="overhead_lights",
    )
    switch_set = harness.switch_set

    assert switch_set.area_id == "living_room"
    assert switch_set.role == "overhead_lights"
    assert _state(hass, switch_set.main_switch_entity_id).state == STATE_ON
    assert _state(hass, switch_set.sleep_switch_entity_id).state == STATE_OFF
    assert _state(hass, switch_set.adapt_brightness_switch_entity_id).state == STATE_ON
    assert _state(hass, switch_set.adapt_color_switch_entity_id).state == STATE_ON
    assert hass.services.has_service(ADAPTIVE_LIGHTING_DOMAIN, SERVICE_APPLY)
    assert hass.services.has_service(
        ADAPTIVE_LIGHTING_DOMAIN,
        SERVICE_SET_MANUAL_CONTROL,
    )
    assert hass.services.has_service(
        ADAPTIVE_LIGHTING_DOMAIN,
        SERVICE_CHANGE_SWITCH_SETTINGS,
    )


async def test_config_entry_harness_creates_al_like_entry_and_switches(
    hass: HomeAssistant,
) -> None:
    """Tests can create AL-like config entries without importing the integration."""
    harness = setup_adaptive_lighting_config_entry_harness(hass)

    entry = await harness.async_create_entry(
        name="Magic Areas Living Room overhead",
        options={
            ATTR_LIGHTS: ["light.ceiling"],
            "min_brightness": 20,
        },
    )

    assert entry.domain == ADAPTIVE_LIGHTING_DOMAIN
    assert entry.data == {"name": "Magic Areas Living Room overhead"}
    assert entry.options["min_brightness"] == 20
    assert harness.reload_requests == [entry.entry_id]
    assert _state(
        hass, "switch.adaptive_lighting_magic_areas_living_room_overhead"
    ).attributes[ATTR_LIGHTS] == ["light.ceiling"]


async def test_config_entry_harness_updates_options_and_preserves_al_tuning(
    hass: HomeAssistant,
) -> None:
    """Managed AL tests can assert update/reload behavior around options changes."""
    harness = setup_adaptive_lighting_config_entry_harness(hass)
    entry = await harness.async_create_entry(
        name="Magic Areas Living Room overhead",
        options={
            ATTR_LIGHTS: ["light.old_member"],
            "min_brightness": 15,
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

    await harness.async_update_options(
        entry,
        managed_adaptive_lighting_options(entry.options, desired),
    )

    assert harness.reload_requests == [entry.entry_id, entry.entry_id]
    assert entry.options == {
        ATTR_LIGHTS: ["light.ceiling", "light.lamp"],
        "min_brightness": 15,
        "sleep_rgb_or_color_temp": "color_temp",
    }
    assert _state(
        hass, "switch.adaptive_lighting_magic_areas_living_room_overhead"
    ).attributes[ATTR_LIGHTS] == ["light.ceiling", "light.lamp"]


async def test_harness_captures_apply_service_expectation(
    hass: HomeAssistant,
) -> None:
    """Tests can assert Adaptive Lighting apply calls without importing the integration."""
    harness = await setup_adaptive_lighting_harness(hass)
    switch_set = harness.switch_set

    await hass.services.async_call(
        ADAPTIVE_LIGHTING_DOMAIN,
        SERVICE_APPLY,
        {
            ATTR_ENTITY_ID: switch_set.main_switch_entity_id,
            ATTR_LIGHTS: ["light.lamp"],
            "adapt_brightness": True,
            "adapt_color": False,
            "turn_on_lights": False,
        },
        blocking=True,
    )

    assert len(harness.calls) == 1
    assert harness.calls[0].service == SERVICE_APPLY
    assert harness.calls[0].data == {
        ATTR_ENTITY_ID: switch_set.main_switch_entity_id,
        ATTR_LIGHTS: ["light.lamp"],
        "adapt_brightness": True,
        "adapt_color": False,
        "turn_on_lights": False,
    }


async def test_harness_captures_manual_control_reset_expectation(
    hass: HomeAssistant,
) -> None:
    """Tests can assert MA clears AL manual-control state after its cooldown."""
    harness = await setup_adaptive_lighting_harness(hass)

    await hass.services.async_call(
        ADAPTIVE_LIGHTING_DOMAIN,
        SERVICE_SET_MANUAL_CONTROL,
        {
            ATTR_ENTITY_ID: harness.switch_set.main_switch_entity_id,
            ATTR_LIGHTS: ["light.lamp"],
            "manual_control": False,
        },
        blocking=True,
    )

    assert len(harness.calls) == 1
    assert harness.calls[0].service == SERVICE_SET_MANUAL_CONTROL
    assert harness.calls[0].data == {
        ATTR_ENTITY_ID: harness.switch_set.main_switch_entity_id,
        ATTR_LIGHTS: ["light.lamp"],
        "manual_control": False,
    }


async def test_harness_captures_behavior_switch_updates(
    hass: HomeAssistant,
) -> None:
    """Tests can assert MA pauses/resumes AL behavior switches."""
    harness = await setup_adaptive_lighting_harness(hass)

    await hass.services.async_call(
        ADAPTIVE_LIGHTING_DOMAIN,
        SERVICE_CHANGE_SWITCH_SETTINGS,
        {
            "entity_id": harness.switch_set.adapt_brightness_switch_entity_id,
            "adapt_brightness": False,
        },
        blocking=True,
    )

    assert len(harness.calls) == 1
    assert harness.calls[0].service == SERVICE_CHANGE_SWITCH_SETTINGS
    assert harness.calls[0].data == {
        "entity_id": harness.switch_set.adapt_brightness_switch_entity_id,
        "adapt_brightness": False,
    }


async def test_harness_records_manual_control_events(
    hass: HomeAssistant,
) -> None:
    """Tests can simulate Adaptive Lighting claiming manual control of a light."""
    harness = await setup_adaptive_lighting_harness(hass)

    harness.fire_manual_control_event(entity_id="light.lamp")
    await hass.async_block_till_done()

    assert harness.manual_control_events == [
        {
            "entity_id": "light.lamp",
            "switch": harness.switch_set.main_switch_entity_id,
        }
    ]
    assert EVENT_MANUAL_CONTROL == "adaptive_lighting.manual_control"
