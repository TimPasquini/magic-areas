"""Live fan and cover automation simulation scenario."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.ha_dev_bootstrap import HomeAssistantWs
from scripts.ha_dev_simulation.client import (
    call_service,
    set_input_boolean,
    set_input_number,
    set_input_select,
    set_switch,
    wait_for_state,
)
from scripts.ha_dev_simulation.entities import (
    COVER_ROOM_MANUAL_HOLD_SECONDS,
    FAN_ROOM_CLEAR_TIMEOUT_MINUTES,
    FAN_ROOM_HUMIDITY_HOLD_SECONDS,
)
from scripts.ha_dev_simulation.expectations import ScenarioEvaluation, wait_for_states
from scripts.ha_dev_simulation.reset import ramp_input_number, reset_fake_house
from scripts.ha_dev_simulation.models import ExpectedState
from scripts.ha_dev_simulation.preflight import preflight_fan_cover_options
from scripts.ha_dev_simulation.timing import SimulationTiming


fan_area_state = "binary_sensor.magic_areas_presence_tracking_fan_room_area_state"
cover_area_state = (
    "binary_sensor.magic_areas_presence_tracking_cover_room_area_state"
)
fan_entity = "fan.fan_room_exhaust"
fan_humidity_trend = (
    "binary_sensor.magic_areas_signals_fan_room_trend_fan_controller_humidity"
)
cover_blinds = "cover.cover_room_blinds"
cover_shades = "cover.cover_room_shades"
cover_curtains = "cover.cover_room_curtains"
cover_shutters = "cover.cover_room_shutters"
cover_window = "cover.cover_room_window"
cover_garage = "cover.cover_room_garage"
cover_door = "cover.cover_room_door"
cover_blind_group = "cover.magic_areas_cover_groups_cover_room_cover_group_blind"
cover_shade_group = "cover.magic_areas_cover_groups_cover_room_cover_group_shade"
cover_curtain_group = (
    "cover.magic_areas_cover_groups_cover_room_cover_group_curtain"
)
cover_shutter_group = (
    "cover.magic_areas_cover_groups_cover_room_cover_group_shutter"
)
cover_window_group = "cover.magic_areas_cover_groups_cover_room_cover_group_window"
eligible_covers = (
    cover_blinds,
    cover_shades,
    cover_curtains,
    cover_shutters,
    cover_window,
)
eligible_cover_groups = (
    cover_blind_group,
    cover_shade_group,
    cover_curtain_group,
    cover_shutter_group,
    cover_window_group,
)
excluded_covers = (cover_garage, cover_door)
fan_control = "switch.magic_areas_fan_groups_fan_room_fan_control"
cover_control = "switch.magic_areas_cover_groups_cover_room_cover_control"


async def fan_cover_matrix(client: HomeAssistantWs, args: argparse.Namespace) -> None:
    """Run live fan/cover automation checkpoints in dedicated fake-house rooms."""
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)
    timing = SimulationTiming.from_args(args)
    preflight_fan_cover_options(Path(args.config_entries_file))

    await _run_disabled_and_initial_checks(client, args, timing, evaluation)
    await _run_fan_controller_checks(client, args, timing, evaluation)
    await _run_cover_automation_checks(client, timing, evaluation)
    evaluation.write()


async def _run_disabled_and_initial_checks(
    client: HomeAssistantWs,
    args: argparse.Namespace,
    timing: SimulationTiming,
    evaluation: ScenarioEvaluation,
) -> None:
    """Verify disabled controls and establish active scenario state."""
    await reset_fake_house(client)
    await timing.settle_setup()
    await set_switch(client, [fan_control, cover_control], False)
    await timing.settle_setup()

    print("event: fan and cover controls disabled block automatic action", flush=True)
    await set_input_boolean(client, "input_boolean.fan_room_occupancy", True)
    await set_input_number(client, "input_number.fan_room_humidity", 65)
    await set_input_number(client, "input_number.cover_room_lux", 1200)
    await set_input_boolean(client, "input_boolean.cover_room_occupancy", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="disabled controls do not move fan or covers",
        expectations=(
            ExpectedState(fan_control, state="off"),
            ExpectedState(cover_control, state="off"),
            ExpectedState(fan_area_state, state="on", states_contains=("occupied",)),
            ExpectedState(
                cover_area_state, state="on", states_contains=("occupied", "bright")
            ),
            ExpectedState(fan_entity, state="off"),
            *(ExpectedState(entity_id, state="closed") for entity_id in eligible_covers),
            *(ExpectedState(entity_id, state="closed") for entity_id in excluded_covers),
        ),
    )

    await reset_fake_house(client)
    await timing.settle_setup()
    if args.enable_controls:
        await set_switch(
            client,
            [fan_control, cover_control],
            True,
        )
    await timing.settle_setup()

    print("event: cover room occupied with daylight/lux available", flush=True)
    await set_input_number(client, "input_number.cover_room_lux", 1200)
    await set_input_boolean(client, "input_boolean.cover_room_occupancy", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="daylight occupied opens covers",
        expectations=(
            ExpectedState(
                cover_area_state, state="on", states_contains=("occupied", "bright")
            ),
            *(ExpectedState(entity_id, state="open") for entity_id in eligible_covers),
            *(ExpectedState(entity_id, state="open") for entity_id in eligible_cover_groups),
            *(ExpectedState(entity_id, state="closed") for entity_id in excluded_covers),
        ),
    )

    print("event: fan room occupied with fan idle", flush=True)
    await set_input_boolean(client, "input_boolean.fan_room_occupancy", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="fan room occupied idle",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("occupied",)),
            ExpectedState(fan_entity, state="off"),
        ),
    )


async def _run_fan_controller_checks(
    client: HomeAssistantWs,
    args: argparse.Namespace,
    timing: SimulationTiming,
    evaluation: ScenarioEvaluation,
) -> None:
    """Verify fan signal, suppression, availability, and hold behavior."""
    print("event: fan room humidity rises inside trend hysteresis band", flush=True)
    await ramp_input_number(
        client,
        entity_id="input_number.fan_room_humidity",
        start=55,
        end=59,
        seconds=args.ramp_seconds,
    )
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="humidity trend helper activates fan inside hysteresis band",
        expectations=(
            ExpectedState(fan_humidity_trend, state="on"),
            ExpectedState(fan_area_state, state="on", states_contains=("humid",)),
            ExpectedState(fan_entity, state="on"),
        ),
    )

    print("event: fan room humidity crosses fan threshold", flush=True)
    await set_input_number(client, "input_number.fan_room_humidity", 65)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="humidity fan on",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("humid",)),
            ExpectedState(fan_entity, state="on"),
        ),
    )

    print("event: fan room VOC/odor sensor overlaps humidity", flush=True)
    await set_input_number(client, "input_number.fan_room_voc", 650)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="voc odor overlap keeps fan",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("humid", "odor")),
            ExpectedState(fan_entity, state="on"),
        ),
    )

    print("event: fan room humidity clears while odor remains", flush=True)
    await set_input_number(client, "input_number.fan_room_humidity", 45)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="voc odor keeps shared fan after humidity clears",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("odor",)),
            ExpectedState(fan_entity, state="on"),
        ),
    )

    print("event: fan room VOC sensor becomes unavailable", flush=True)
    await set_input_select(client, "input_select.fan_room_voc_availability", "unavailable")
    await set_input_number(client, "input_number.fan_room_voc", 0)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="voc unavailable holds odor fan until restored",
        expectations=(
            ExpectedState("sensor.fan_room_voc", state="unavailable"),
            ExpectedState(fan_area_state, state="on", states_contains=("odor",)),
            ExpectedState(fan_entity, state="on"),
        ),
    )

    print("event: fan room VOC sensor restores below threshold", flush=True)
    await set_input_select(client, "input_select.fan_room_voc_availability", "available")
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="voc restored clears held odor fan",
        expectations=(
            ExpectedState("sensor.fan_room_voc", state="0.0"),
            ExpectedState(fan_area_state, state="on", states_contains=("occupied",)),
            ExpectedState(fan_entity, state="off"),
        ),
    )

    print("event: fan room VOC clears", flush=True)
    await set_input_number(client, "input_number.fan_room_voc", 0)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="all fan reasons clear",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("occupied",)),
            ExpectedState(fan_entity, state="off"),
        ),
    )

    print("event: fan room sleep suppresses humidity controller", flush=True)
    await set_input_boolean(client, "input_boolean.fan_room_sleep", True)
    await set_input_number(client, "input_number.fan_room_humidity", 65)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="sleep suppresses humidity fan",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("sleep",)),
            ExpectedState(fan_entity, state="off"),
        ),
    )

    print("event: fan room sleep clears and humidity can activate", flush=True)
    await set_input_boolean(client, "input_boolean.fan_room_sleep", False)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="humidity activates after sleep suppression clears",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("humid",)),
            ExpectedState(fan_entity, state="on"),
        ),
    )

    print("event: fan room humidity sensor becomes unavailable", flush=True)
    await set_input_select(
        client,
        "input_select.fan_room_humidity_availability",
        "unavailable",
    )
    await timing.settle_immediate_guard()
    await evaluation.evaluate(
        client,
        checkpoint="humidity unavailable hold keeps fan briefly",
        expectations=(
            ExpectedState("sensor.fan_room_humidity", state="unavailable"),
            ExpectedState(fan_entity, state="on"),
        ),
    )
    await timing.wait_configured_seconds(FAN_ROOM_HUMIDITY_HOLD_SECONDS)
    await evaluation.evaluate(
        client,
        checkpoint="humidity unavailable hold expires and clears fan",
        expectations=(
            ExpectedState("sensor.fan_room_humidity", state="unavailable"),
            ExpectedState(fan_entity, state="off"),
        ),
    )
    await set_input_number(client, "input_number.fan_room_humidity", 45)
    await set_input_select(
        client,
        "input_select.fan_room_humidity_availability",
        "available",
    )
    await timing.settle_checkpoint()

    print("event: fan room humidity post-clear hold", flush=True)
    await set_input_boolean(client, "input_boolean.fan_room_occupancy", True)
    await set_input_number(client, "input_number.fan_room_humidity", 65)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="humidity fan active before post-clear hold",
        expectations=(
            ExpectedState(fan_area_state, state="on", states_contains=("humid",)),
            ExpectedState(fan_entity, state="on"),
        ),
    )
    await set_input_boolean(client, "input_boolean.fan_room_occupancy", False)
    await wait_for_states(
        client,
        (
            ExpectedState(fan_area_state, state="off", states_contains=("clear",)),
            ExpectedState(fan_entity, state="on"),
        ),
        timeout_seconds=timing.configured_minutes_timeout(
            FAN_ROOM_CLEAR_TIMEOUT_MINUTES
        ),
        poll_seconds=timing.runtime_poll_seconds,
    )
    await evaluation.evaluate(
        client,
        checkpoint="humidity post-clear hold keeps fan after room clears",
        expectations=(
            ExpectedState(fan_area_state, state="off", states_contains=("clear",)),
            ExpectedState(fan_entity, state="on"),
        ),
    )
    await timing.wait_configured_seconds(FAN_ROOM_HUMIDITY_HOLD_SECONDS)
    await evaluation.evaluate(
        client,
        checkpoint="humidity post-clear hold expires",
        expectations=(
            ExpectedState(fan_area_state, state="off", states_contains=("clear",)),
            ExpectedState(fan_entity, state="off"),
        ),
    )
    await set_input_number(client, "input_number.fan_room_humidity", 45)
    await timing.settle_checkpoint()


async def _run_cover_automation_checks(
    client: HomeAssistantWs,
    timing: SimulationTiming,
    evaluation: ScenarioEvaluation,
) -> None:
    """Verify cover state automation and scoped manual holds."""
    print("event: cover room accent/media closes covers", flush=True)
    await set_input_boolean(client, "input_boolean.cover_room_accent", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="accent closes covers",
        expectations=(
            ExpectedState(cover_area_state, state="on", states_contains=("accented",)),
            *(ExpectedState(entity_id, state="closed") for entity_id in eligible_covers),
            *(ExpectedState(entity_id, state="closed") for entity_id in eligible_cover_groups),
            *(ExpectedState(entity_id, state="closed") for entity_id in excluded_covers),
        ),
    )

    print("event: cover room accent clears back to daylight", flush=True)
    await set_input_boolean(client, "input_boolean.cover_room_accent", False)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="daylight reopens both cover groups",
        expectations=(
            ExpectedState(
                cover_area_state, state="on", states_contains=("occupied", "bright")
            ),
            *(ExpectedState(entity_id, state="open") for entity_id in eligible_covers),
            *(ExpectedState(entity_id, state="open") for entity_id in eligible_cover_groups),
            *(ExpectedState(entity_id, state="closed") for entity_id in excluded_covers),
        ),
    )

    print("event: cover room sleep/privacy closes covers", flush=True)
    await set_input_boolean(client, "input_boolean.cover_room_sleep", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="sleep closes covers",
        expectations=(
            ExpectedState(cover_area_state, state="on", states_contains=("sleep",)),
            *(ExpectedState(entity_id, state="closed") for entity_id in eligible_covers),
            *(ExpectedState(entity_id, state="closed") for entity_id in eligible_cover_groups),
            *(ExpectedState(entity_id, state="closed") for entity_id in excluded_covers),
        ),
    )

    print("event: cover room sleep clears while room is dark", flush=True)
    await set_input_number(client, "input_number.cover_room_lux", 350)
    await timing.settle_checkpoint()
    await set_input_boolean(client, "input_boolean.cover_room_sleep", False)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="dark occupied does not reopen covers",
        expectations=(
            ExpectedState(
                cover_area_state, state="on", states_contains=("occupied", "dark")
            ),
            *(ExpectedState(entity_id, state="closed") for entity_id in eligible_covers),
            *(ExpectedState(entity_id, state="closed") for entity_id in eligible_cover_groups),
            *(ExpectedState(entity_id, state="closed") for entity_id in excluded_covers),
        ),
    )

    print("event: cover room manual blind close creates scoped hold", flush=True)
    await set_input_number(client, "input_number.cover_room_lux", 1200)
    await timing.settle_checkpoint()
    await wait_for_state(
        client,
        cover_blinds,
        "open",
        timeout_seconds=timing.configured_seconds_timeout(
            COVER_ROOM_MANUAL_HOLD_SECONDS
        ),
    )
    await wait_for_state(
        client,
        cover_shades,
        "open",
        timeout_seconds=timing.configured_seconds_timeout(
            COVER_ROOM_MANUAL_HOLD_SECONDS
        ),
    )
    for entity_id in (cover_curtains, cover_shutters, cover_window):
        await wait_for_state(
            client,
            entity_id,
            "open",
            timeout_seconds=timing.configured_seconds_timeout(
                COVER_ROOM_MANUAL_HOLD_SECONDS
            ),
        )
    await call_service(client, "cover", "close_cover", entity_id=cover_blind_group)
    await timing.settle_immediate_guard()
    await evaluation.evaluate(
        client,
        checkpoint="manual blind close not immediately reversed",
        expectations=(
            ExpectedState(
                cover_area_state, state="on", states_contains=("occupied", "bright")
            ),
            ExpectedState(cover_blinds, state="closed"),
            ExpectedState(cover_shades, state="open"),
            ExpectedState(cover_blind_group, state="closed"),
            ExpectedState(cover_shade_group, state="open"),
            ExpectedState(cover_curtain_group, state="open"),
            ExpectedState(cover_shutter_group, state="open"),
            ExpectedState(cover_window_group, state="open"),
        ),
    )
    print("event: cover room manual blind hold expires and automation reopens", flush=True)
    await timing.wait_configured_seconds(COVER_ROOM_MANUAL_HOLD_SECONDS)
    await wait_for_state(
        client,
        cover_blinds,
        "open",
        timeout_seconds=timing.configured_seconds_timeout(
            COVER_ROOM_MANUAL_HOLD_SECONDS
        ),
    )
    await evaluation.evaluate(
        client,
        checkpoint="manual blind hold expires and reopens",
        expectations=(
            ExpectedState(
                cover_area_state, state="on", states_contains=("occupied", "bright")
            ),
            ExpectedState(cover_blinds, state="open"),
            ExpectedState(cover_shades, state="open"),
            *(ExpectedState(entity_id, state="open") for entity_id in eligible_cover_groups),
        ),
    )

    print("event: cover room simultaneous blind and shade manual holds", flush=True)
    await call_service(
        client,
        "cover",
        "close_cover",
        entity_id=[cover_blind_group, cover_shade_group],
    )
    await timing.settle_immediate_guard()
    await evaluation.evaluate(
        client,
        checkpoint="simultaneous manual holds affect only moved cover groups",
        expectations=(
            ExpectedState(
                cover_area_state, state="on", states_contains=("occupied", "bright")
            ),
            ExpectedState(cover_blinds, state="closed"),
            ExpectedState(cover_shades, state="closed"),
            ExpectedState(cover_curtains, state="open"),
            ExpectedState(cover_shutters, state="open"),
            ExpectedState(cover_window, state="open"),
            ExpectedState(cover_garage, state="closed"),
            ExpectedState(cover_door, state="closed"),
        ),
    )
    await timing.wait_configured_seconds(COVER_ROOM_MANUAL_HOLD_SECONDS)
    await wait_for_state(
        client,
        cover_blinds,
        "open",
        timeout_seconds=timing.configured_seconds_timeout(
            COVER_ROOM_MANUAL_HOLD_SECONDS
        ),
    )
    await wait_for_state(
        client,
        cover_shades,
        "open",
        timeout_seconds=timing.configured_seconds_timeout(
            COVER_ROOM_MANUAL_HOLD_SECONDS
        ),
    )
    await evaluation.evaluate(
        client,
        checkpoint="simultaneous manual holds expire and reopen",
        expectations=(
            *(ExpectedState(entity_id, state="open") for entity_id in eligible_covers),
            *(ExpectedState(entity_id, state="closed") for entity_id in excluded_covers),
        ),
    )
