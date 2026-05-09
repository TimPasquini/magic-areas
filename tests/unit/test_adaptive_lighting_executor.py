"""Tests for executing Adaptive Lighting coordination intents."""

from __future__ import annotations

from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.control_intents import (
    ATTR_LIGHTS,
    adaptive_lighting_accent_adaptation_intents,
    adaptive_lighting_manual_restore_intents,
    adaptive_lighting_sleep_switch_intents,
    async_execute_adaptive_lighting_intents,
)
from tests.unit.adaptive_lighting_testkit import (
    ADAPTIVE_LIGHTING_DOMAIN,
    SERVICE_SET_MANUAL_CONTROL,
    setup_adaptive_lighting_harness,
)


async def test_executor_toggles_sleep_switch(
    hass: HomeAssistant,
) -> None:
    """Executor should apply sleep coordination through the switch domain."""
    harness = await setup_adaptive_lighting_harness(hass)

    await async_execute_adaptive_lighting_intents(
        hass,
        adaptive_lighting_sleep_switch_intents(
            harness.switch_set,
            sleep_active=True,
        ),
    )

    sleep_switch = hass.states.get(harness.switch_set.sleep_switch_entity_id)
    assert sleep_switch is not None
    assert sleep_switch.state == STATE_ON
    assert harness.calls[-1].service == "switch.turn_on"
    assert harness.calls[-1].data == {
        ATTR_ENTITY_ID: harness.switch_set.sleep_switch_entity_id
    }


async def test_executor_pauses_accent_adaptation_switches(
    hass: HomeAssistant,
) -> None:
    """Executor should pause AL brightness/color behavior switches for accent."""
    harness = await setup_adaptive_lighting_harness(hass)

    await async_execute_adaptive_lighting_intents(
        hass,
        adaptive_lighting_accent_adaptation_intents(
            harness.switch_set,
            accent_active=True,
        ),
    )

    adapt_brightness = hass.states.get(
        harness.switch_set.adapt_brightness_switch_entity_id
    )
    adapt_color = hass.states.get(harness.switch_set.adapt_color_switch_entity_id)
    assert adapt_brightness is not None
    assert adapt_color is not None
    assert adapt_brightness.state == STATE_OFF
    assert adapt_color.state == STATE_OFF
    assert [call.service for call in harness.calls[-2:]] == [
        "switch.turn_off",
        "switch.turn_off",
    ]


async def test_executor_clears_manual_control_after_cooldown(
    hass: HomeAssistant,
) -> None:
    """Executor should call AL manual-control restore with documented service data."""
    harness = await setup_adaptive_lighting_harness(hass)

    await async_execute_adaptive_lighting_intents(
        hass,
        adaptive_lighting_manual_restore_intents(
            harness.switch_set,
            light_entity_ids=("light.lamp",),
            cooldown_expired=True,
        ),
    )

    assert harness.calls[-1].service == SERVICE_SET_MANUAL_CONTROL
    assert harness.calls[-1].data == {
        ATTR_ENTITY_ID: harness.switch_set.main_switch_entity_id,
        ATTR_LIGHTS: ("light.lamp",),
        "manual_control": False,
    }


async def test_executor_skips_missing_optional_service(
    hass: HomeAssistant,
) -> None:
    """Executor should fail closed when optional AL services are unavailable."""
    harness = await setup_adaptive_lighting_harness(hass)
    hass.services.async_remove(ADAPTIVE_LIGHTING_DOMAIN, SERVICE_SET_MANUAL_CONTROL)

    await async_execute_adaptive_lighting_intents(
        hass,
        adaptive_lighting_manual_restore_intents(
            harness.switch_set,
            light_entity_ids=("light.lamp",),
            cooldown_expired=True,
        ),
    )

    assert harness.calls == []
