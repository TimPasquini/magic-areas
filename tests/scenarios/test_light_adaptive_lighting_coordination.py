"""Scenario tests for Magic Areas and Adaptive Lighting coordination."""

from homeassistant.core import HomeAssistant
from pytest import MonkeyPatch

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE,
    CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS,
)
from custom_components.magic_areas.core.control_intents import (
    ADAPT_BRIGHTNESS_SWITCH,
    ADAPT_COLOR_SWITCH,
    AdaptiveLightingServiceIntent,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SLEEP_SWITCH,
)
from custom_components.magic_areas.light_groups import (
    CONF_OVERHEAD_LIGHTS,
    LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING,
)
from tests.scenarios.light_scenario_testkit import (
    setup_one_room_advisory_light_scenario,
)
from tests.unit.adaptive_lighting_testkit import (
    setup_adaptive_lighting_harness,
)


def _capture_adaptive_lighting_intents(
    monkeypatch: MonkeyPatch,
) -> list[AdaptiveLightingServiceIntent]:
    """Capture AL coordination intents scheduled by the light-group runtime."""
    captured: list[AdaptiveLightingServiceIntent] = []

    async def _capture(
        _hass: HomeAssistant,
        intents: tuple[AdaptiveLightingServiceIntent, ...],
    ) -> None:
        captured.extend(intents)

    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime."
        "async_execute_adaptive_lighting_intents",
        _capture,
    )
    return captured


async def test_sleep_and_accent_states_coordinate_adaptive_lighting_switches(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Room state transitions should coordinate the paired AL behavior switches."""
    captured_intents = _capture_adaptive_lighting_intents(monkeypatch)
    adaptive_lighting = await setup_adaptive_lighting_harness(
        hass,
        name="Kitchen",
        area_id="kitchen",
        role=CONF_OVERHEAD_LIGHTS,
    )
    scenario = await setup_one_room_advisory_light_scenario(
        hass,
        light_group_config_overrides={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: {
                CONF_OVERHEAD_LIGHTS: adaptive_lighting.switch_entity_ids,
            },
        },
    )
    await scenario.enable_light_control()

    await scenario.emit_area_state_transition(
        new_states=[AreaStates.SLEEP, AreaStates.ACCENT],
        current_states=[AreaStates.OCCUPIED, AreaStates.SLEEP, AreaStates.ACCENT],
        step="sleep and accent active",
    )
    await hass.async_block_till_done()

    assert [
        (intent.service, intent.data.get("entity_id")) for intent in captured_intents
    ] == [
        (
            SERVICE_TURN_ON,
            adaptive_lighting.switch_entity_ids[SLEEP_SWITCH],
        ),
        (
            SERVICE_TURN_OFF,
            adaptive_lighting.switch_entity_ids[ADAPT_BRIGHTNESS_SWITCH],
        ),
        (
            SERVICE_TURN_OFF,
            adaptive_lighting.switch_entity_ids[ADAPT_COLOR_SWITCH],
        ),
    ]


async def test_lost_sleep_and_accent_states_restore_adaptive_lighting_switches(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Clearing sleep/accent should restore the paired AL behavior switches."""
    captured_intents = _capture_adaptive_lighting_intents(monkeypatch)
    adaptive_lighting = await setup_adaptive_lighting_harness(
        hass,
        name="Kitchen",
        area_id="kitchen",
        role=CONF_OVERHEAD_LIGHTS,
    )
    scenario = await setup_one_room_advisory_light_scenario(
        hass,
        light_group_config_overrides={
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE: (
                LIGHT_GROUP_ADAPTIVE_LIGHTING_MODE_ADOPT_EXISTING
            ),
            CONF_LIGHT_GROUP_ADAPTIVE_LIGHTING_SWITCH_SETS: {
                CONF_OVERHEAD_LIGHTS: adaptive_lighting.switch_entity_ids,
            },
        },
    )
    await scenario.enable_light_control()

    await scenario.emit_area_state_transition(
        new_states=[],
        lost_states=[AreaStates.SLEEP, AreaStates.ACCENT],
        current_states=[AreaStates.OCCUPIED],
        step="sleep and accent cleared",
    )
    await hass.async_block_till_done()

    assert [
        (intent.service, intent.data.get("entity_id")) for intent in captured_intents
    ] == [
        (
            SERVICE_TURN_OFF,
            adaptive_lighting.switch_entity_ids[SLEEP_SWITCH],
        ),
        (
            SERVICE_TURN_ON,
            adaptive_lighting.switch_entity_ids[ADAPT_BRIGHTNESS_SWITCH],
        ),
        (
            SERVICE_TURN_ON,
            adaptive_lighting.switch_entity_ids[ADAPT_COLOR_SWITCH],
        ),
    ]
