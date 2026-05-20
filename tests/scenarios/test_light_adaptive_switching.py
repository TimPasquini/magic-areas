"""Scenario tests for adaptive bright-transition light behavior."""

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest import MonkeyPatch

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.config_keys.area import (
    CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE,
    CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA,
    CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS,
    CONF_LIGHT_GROUP_BRIGHTNESS_MODE,
    CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS,
    CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS,
    CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY,
    CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN,
)
from tests.helpers import wait_for_state
from tests.scenarios.light_scenario_testkit import (
    OneRoomLightScenario,
    setup_one_room_advisory_light_scenario,
)


def _set_runtime_time(monkeypatch: MonkeyPatch, now: float) -> None:
    """Set light-group runtime monotonic time for deterministic guard checks."""
    monkeypatch.setattr(
        "custom_components.magic_areas.light_groups.runtime.monotonic",
        lambda: now,
    )


async def _setup_adaptive_room(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
    *,
    now: float = 0.0,
    dwell_seconds: int = 0,
    min_on_seconds: int = 0,
    outside_source: str = "sun",
    include_secondary_light_as: str | None = None,
    light_group_config_overrides: dict[str, object] | None = None,
) -> OneRoomLightScenario:
    """Set up one occupied adaptive room with its overhead light already on."""
    _set_runtime_time(monkeypatch, now)
    config_overrides: dict[str, object] = {
            CONF_LIGHT_GROUP_BRIGHTNESS_MODE: "adaptive",
            CONF_LIGHT_GROUP_BRIGHT_DWELL_SECONDS: dwell_seconds,
            CONF_LIGHT_GROUP_BRIGHT_MIN_ON_SECONDS: min_on_seconds,
            CONF_LIGHT_GROUP_OUTSIDE_CONTEXT_SOURCE: outside_source,
    }
    if light_group_config_overrides:
        config_overrides.update(light_group_config_overrides)
    scenario = await setup_one_room_advisory_light_scenario(
        hass,
        include_secondary_light_as=include_secondary_light_as,
        light_group_config_overrides=config_overrides,
    )
    hass.states.async_set("sun.sun", "above_horizon")
    await scenario.enable_light_control()
    await scenario.set_inside_bright(STATE_OFF)
    scenario.occupancy_sensor.turn_on()
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.OCCUPIED],
        current_states=[AreaStates.OCCUPIED],
        step="occupied transition",
    )
    await wait_for_state(hass, scenario.target_light_entity_id, STATE_ON)
    scenario.snapshot("adaptive room ready")
    return scenario


async def test_adaptive_bright_transition_waits_for_dwell(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should not turn lights off before bright dwell is met."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        now=0.0,
        dwell_seconds=60,
    )

    await scenario.set_inside_bright(STATE_ON)
    _set_runtime_time(monkeypatch, 10.0)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition before dwell",
    )

    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace
    assert scenario.adaptive_guards()["bright_dwell_met"] is False


async def test_adaptive_bright_transition_waits_for_min_on(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should not turn lights off before minimum on-time is met."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        now=0.0,
        min_on_seconds=60,
    )

    await scenario.set_inside_bright(STATE_ON)
    _set_runtime_time(monkeypatch, 10.0)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition before min-on",
    )

    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace
    assert scenario.adaptive_guards()["min_on_met"] is False


async def test_adaptive_bright_transition_waits_for_outside_context(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should not turn lights off without allowed outside context."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        outside_source="none",
    )

    await scenario.set_inside_bright(STATE_ON)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition without outside context",
    )

    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace
    assert scenario.adaptive_guards()["outside_context_ok"] is False


async def test_adaptive_bright_transition_uses_outside_lux_contrast(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should allow bright-off when outside lux contrast is strong."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        outside_source="outside_lux",
        light_group_config_overrides={
            CONF_LIGHT_GROUP_OUTSIDE_LUX_ENTITY: "sensor.scenario_outside_lux",
            CONF_LIGHT_GROUP_OUTSIDE_LUX_MIN: 500,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY: "sensor.scenario_inside_lux",
            CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_DELTA: 200,
        },
    )
    hass.states.async_set("sensor.scenario_inside_lux", "400")
    hass.states.async_set("sensor.scenario_outside_lux", "700")
    await scenario.hass.async_block_till_done()

    await scenario.set_inside_bright(STATE_ON)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition with outside lux contrast",
    )

    await wait_for_state(hass, scenario.target_light_entity_id, STATE_OFF)
    scenario.snapshot("assert adaptive outside lux bright-off")
    assert scenario.trace[-1].target_light == STATE_OFF, scenario.trace
    assert scenario.adaptive_guards()["outside_context_ok"] is True


async def test_adaptive_bright_transition_blocks_without_ambient_rise(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should wait when ambient-rise evidence is required but absent."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        now=0.0,
        light_group_config_overrides={
            CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE: True,
            CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS: 120,
            CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA: 50,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY: "sensor.scenario_inside_lux",
        },
    )
    hass.states.async_set("sensor.scenario_inside_lux", "400")
    await scenario.hass.async_block_till_done()

    await scenario.set_inside_bright(STATE_ON)
    _set_runtime_time(monkeypatch, 10.0)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition without ambient rise",
    )

    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace
    assert scenario.adaptive_guards()["ambient_rise_met"] is False


async def test_adaptive_bright_transition_allows_with_ambient_rise(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should allow bright-off when required ambient-rise is present."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        now=0.0,
        light_group_config_overrides={
            CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE: True,
            CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS: 120,
            CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA: 50,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY: "sensor.scenario_inside_lux",
        },
    )
    hass.states.async_set("sensor.scenario_inside_lux", "300")
    await scenario.hass.async_block_till_done()
    await scenario.emit_area_state_transition(
        new_states=[],
        current_states=[AreaStates.OCCUPIED],
        step="ambient baseline sample",
    )

    hass.states.async_set("sensor.scenario_inside_lux", "375")
    await scenario.hass.async_block_till_done()
    await scenario.set_inside_bright(STATE_ON)
    _set_runtime_time(monkeypatch, 30.0)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition with ambient rise",
    )

    await wait_for_state(hass, scenario.target_light_entity_id, STATE_OFF)
    scenario.snapshot("assert adaptive ambient-rise bright-off")
    assert scenario.trace[-1].target_light == STATE_OFF, scenario.trace
    assert scenario.adaptive_guards()["ambient_rise_met"] is True


async def test_adaptive_bright_transition_waits_for_attribution_hold(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should not immediately undo Magic Areas' own light output."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        now=0.0,
        light_group_config_overrides={
            CONF_LIGHT_GROUP_BRIGHT_ATTRIBUTION_HOLD_SECONDS: 60,
        },
    )

    await scenario.set_inside_bright(STATE_ON)
    _set_runtime_time(monkeypatch, 10.0)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition before attribution hold",
    )

    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace
    assert scenario.adaptive_guards()["attribution_hold_met"] is False


async def test_adaptive_ambient_rise_blocks_after_manual_room_light_turn_on(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive ambient rise should not treat manual room-light output as daylight."""
    scenario = await _setup_adaptive_room(
        hass,
        monkeypatch,
        now=0.0,
        include_secondary_light_as="sleep_lights",
        light_group_config_overrides={
            CONF_LIGHT_GROUP_ADAPTIVE_REQUIRE_AMBIENT_RISE: True,
            CONF_LIGHT_GROUP_AMBIENT_RISE_WINDOW_SECONDS: 120,
            CONF_LIGHT_GROUP_AMBIENT_RISE_MIN_DELTA: 50,
            CONF_LIGHT_GROUP_OUTSIDE_LUX_INSIDE_ENTITY: "sensor.scenario_inside_lux",
        },
    )
    hass.states.async_set("sensor.scenario_inside_lux", "400")
    await scenario.hass.async_block_till_done()
    await scenario.emit_area_state_transition(
        new_states=[],
        current_states=[AreaStates.OCCUPIED],
        step="ambient baseline before manual light",
    )

    assert scenario.secondary_light is not None
    scenario.secondary_light.turn_on()
    await scenario.hass.async_block_till_done()
    hass.states.async_set("sensor.scenario_inside_lux", "475")
    await scenario.hass.async_block_till_done()
    await scenario.set_inside_bright(STATE_ON)
    _set_runtime_time(monkeypatch, 30.0)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition after manual light",
    )

    assert scenario.trace[-1].target_light == STATE_ON, scenario.trace
    assert scenario.adaptive_guards()["ambient_rise_met"] is False
    assert scenario.adaptive_guards()["ambient_rise_direct_light_blocked"] is True
    assert (
        scenario.light_group_entity()._attr_extra_state_attributes[
            "last_direct_light_activity_entity_id"
        ]
        == scenario.secondary_light_entity_id
    )


async def test_adaptive_bright_transition_turns_off_when_guards_pass(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """Adaptive mode should turn lights off when bright-off guards pass."""
    scenario = await _setup_adaptive_room(hass, monkeypatch)

    await scenario.set_inside_bright(STATE_ON)
    await scenario.emit_area_state_transition(
        new_states=[AreaStates.BRIGHT],
        current_states=[AreaStates.OCCUPIED, AreaStates.BRIGHT],
        step="bright transition with guards passing",
    )

    await wait_for_state(hass, scenario.target_light_entity_id, STATE_OFF)
    scenario.snapshot("assert adaptive bright-off")
    assert scenario.trace[-1].target_light == STATE_OFF, scenario.trace
    assert scenario.trace[-1].last_policy_reason == "bright_not_assigned"
    assert scenario.adaptive_guards()["bright_dwell_met"] is True
    assert scenario.adaptive_guards()["min_on_met"] is True
    assert scenario.adaptive_guards()["outside_context_ok"] is True
