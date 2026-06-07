"""Live light-control and control-matrix simulation scenarios."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable, Mapping
from pathlib import Path

from scripts.ha_dev_bootstrap import DEV_ROOMS, HomeAssistantWs
from scripts.ha_dev_simulation.client import (
    call_service,
    set_input_boolean,
    set_input_number,
    set_input_select,
    set_light,
    set_switch,
    wait_for_service_call_event,
    wait_for_state,
)
from scripts.ha_dev_simulation.entities import (
    ADAPTIVE_LIGHTING_ALL_LIGHTS_SLEEP_SWITCH,
    AMBIENT_BRIGHT_THRESHOLD_LUX,
    AMBIENT_DAYLIGHT_LUX,
    AMBIENT_RISE_ROOM_SLUG,
    AMBIENT_RISE_ROOM_SLUGS,
    BRIGHT_OFF_RUNTIME_TIMEOUT_SECONDS,
    CONTROL_MATRIX_ROOM_SLUGS,
    DAYLIGHT_AREA_LIGHT_ROOM_SLUGS,
    DEFAULT_LUX_JITTER,
    MANUAL_DIRECT_LIGHT_ROOM_SLUG,
    SEEDED_CLEAR_TIMEOUT_MINUTES,
    STARTUP_UNAVAILABLE_ROOM_SLUG,
    STARTUP_UNKNOWN_ROOM_SLUG,
    ambient_rise_signal_entity,
)
from scripts.ha_dev_simulation.expectations import ScenarioEvaluation, wait_for_states
from scripts.ha_dev_simulation.reset import (
    jitter_input_number,
    ramp_input_number,
    reset_fake_house,
)
from scripts.ha_dev_simulation.models import ExpectedState
from scripts.ha_dev_simulation.timing import SimulationTiming
from scripts.ha_dev_simulation.traces import room_by_slug, second_power_entity


def _control_matrix_rooms() -> tuple[object, ...]:
    """Return rooms that participate in strict control-matrix assertions."""
    rooms = room_by_slug()
    return tuple(rooms[slug] for slug in CONTROL_MATRIX_ROOM_SLUGS if slug in rooms)


def _daylight_area_light_rooms(rooms: Iterable[object]) -> tuple[object, ...]:
    """Return rooms whose bright/dark state is sourced from fake outdoor daylight."""
    return tuple(
        room
        for room in rooms
        if str(getattr(room, "slug")) in DAYLIGHT_AREA_LIGHT_ROOM_SLUGS
    )


def _non_daylight_area_light_rooms(rooms: Iterable[object]) -> tuple[object, ...]:
    """Return rooms whose bright/dark state is sourced from in-room fake sensors."""
    return tuple(
        room
        for room in rooms
        if str(getattr(room, "slug")) not in DAYLIGHT_AREA_LIGHT_ROOM_SLUGS
    )


def _control_switches(rooms: Iterable[object]) -> list[str]:
    """Return Magic Areas light-control switches for rooms."""
    return [
        f"switch.magic_areas_light_groups_{getattr(room, 'slug')}_light_control"
        for room in rooms
    ]


def _dark_occupied_expectations(rooms: Iterable[object]) -> list[ExpectedState]:
    """Return expected runtime state after rooms become occupied while dark."""
    expectations: list[ExpectedState] = []
    for room in rooms:
        slug = str(getattr(room, "slug"))
        expectations.extend(
            [
                ExpectedState(
                    f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                    state="on",
                    states_contains=("occupied", "dark"),
                ),
                ExpectedState(f"light.{slug}_overhead", state="on"),
                ExpectedState(
                    f"light.magic_areas_native_light_groups_{slug}_overhead_lights",
                    state="on",
                ),
            ]
        )
    return expectations


def _disabled_light_control_expectations(rooms: Iterable[object]) -> list[ExpectedState]:
    """Return expected state when occupancy changes while light control is disabled."""
    expectations: list[ExpectedState] = []
    for room in rooms:
        slug = str(getattr(room, "slug"))
        expectations.extend(
            [
                ExpectedState(
                    f"switch.magic_areas_light_groups_{slug}_light_control",
                    state="off",
                ),
                ExpectedState(
                    f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                    state="on",
                    states_contains=("occupied",),
                ),
                ExpectedState(f"light.{slug}_overhead", state="off"),
                ExpectedState(
                    f"light.magic_areas_native_light_groups_{slug}_overhead_lights",
                    state="off",
                ),
            ]
        )
    return expectations


def _startup_unavailable_expectations(room: object) -> list[ExpectedState]:
    """Return expected state when the in-room bright binary is unavailable."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied",),
        ),
        ExpectedState(f"binary_sensor.{slug}_light", state="unavailable"),
        ExpectedState(f"light.{slug}_overhead", state="on"),
        ExpectedState(
            f"light.magic_areas_native_light_groups_{slug}_overhead_lights",
            state="on",
        ),
    ]


def _startup_unknown_expectations(room: object) -> list[ExpectedState]:
    """Return expected state when the in-room bright binary is unknown."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied",),
        ),
        ExpectedState(f"binary_sensor.{slug}_light", state="unknown"),
        ExpectedState(f"light.{slug}_overhead", state="on"),
        ExpectedState(
            f"light.magic_areas_native_light_groups_{slug}_overhead_lights",
            state="on",
        ),
    ]


def _daylight_occupied_expectations(rooms: Iterable[object]) -> list[ExpectedState]:
    """Return expected state for rooms whose area light sensor is fake daylight."""
    expectations: list[ExpectedState] = []
    for room in rooms:
        slug = str(getattr(room, "slug"))
        mode = str(getattr(room, "brightness_mode"))
        expected_overhead = "on" if mode == "advisory" else "off"
        expectations.append(
            ExpectedState(
                f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                state="on",
                states_contains=("occupied", "bright"),
            )
        )
        if mode != "advisory":
            expectations.extend(
                [
                    ExpectedState(f"light.{slug}_overhead", state=expected_overhead),
                    ExpectedState(
                        f"light.magic_areas_native_light_groups_{slug}_overhead_lights",
                        state=expected_overhead,
                    ),
                ]
            )
    return expectations


def _bright_expectations(rooms: Iterable[object]) -> list[ExpectedState]:
    """Return expected runtime state after fake room lux crosses the bright threshold."""
    expectations: list[ExpectedState] = []
    for room in rooms:
        slug = str(getattr(room, "slug"))
        mode = str(getattr(room, "brightness_mode"))
        expected_overhead = "on" if mode == "advisory" else "off"
        expectations.append(
            ExpectedState(
                f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                state="on",
                states_contains=("occupied", "bright"),
            )
        )
        if mode != "advisory" or slug not in DAYLIGHT_AREA_LIGHT_ROOM_SLUGS:
            expectations.append(
                ExpectedState(f"light.{slug}_overhead", state=expected_overhead)
            )
    return expectations


def _ambient_dark_waiting_expectations(room: object) -> list[ExpectedState]:
    """Return expected state before ambient-rise behavior is simulated."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied", "dark"),
        ),
        ExpectedState(f"light.{slug}_overhead", state="on"),
    ]


def _ma_output_contaminated_initial_rise_expectations(
    room: object,
) -> list[ExpectedState]:
    """Return expected state when MA output contaminates first rise evidence."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied", "bright"),
        ),
        ExpectedState(f"light.{slug}_overhead", state="on"),
    ]


def _manual_direct_light_contamination_expectations(
    room: object,
) -> list[ExpectedState]:
    """Return expected state when manual room light contaminates bright evidence."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied", "bright"),
        ),
        ExpectedState(f"light.{slug}_overhead", state="on"),
    ]


def _ambient_rise_bright_expectations(room: object) -> list[ExpectedState]:
    """Return expected state after additional daylight supplies ambient-rise evidence."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied", "bright"),
        ),
        ExpectedState(ambient_rise_signal_entity(slug), state="on"),
        ExpectedState(f"light.{slug}_overhead", state="off"),
    ]


def _sleep_expectations(rooms: Iterable[object]) -> list[ExpectedState]:
    """Return expected runtime state after sleep mode becomes active."""
    expectations: list[ExpectedState] = []
    for room in rooms:
        slug = str(getattr(room, "slug"))
        second_slug = str(getattr(room, "second_light_slug"))
        expectations.extend(
            [
                ExpectedState(
                    f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                    state="on",
                    states_contains=("occupied", "sleep"),
                ),
                ExpectedState(f"light.{slug}_overhead", state="off"),
                ExpectedState(f"light.{slug}_{second_slug}", state="on"),
                ExpectedState(
                    f"light.magic_areas_native_light_groups_{slug}_sleep_lights",
                    state="on",
                ),
            ]
        )
    return expectations


def _accent_expectations(rooms: Iterable[object]) -> list[ExpectedState]:
    """Return expected runtime state after accent mode becomes active."""
    expectations: list[ExpectedState] = []
    for room in rooms:
        if not bool(getattr(room, "include_accent")):
            continue
        slug = str(getattr(room, "slug"))
        second_slug = str(getattr(room, "second_light_slug"))
        expectations.extend(
            [
                ExpectedState(
                    f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                    state="on",
                    states_contains=("occupied", "accented"),
                ),
                ExpectedState(f"light.{slug}_overhead", state="off"),
                ExpectedState(f"light.{slug}_{second_slug}", state="on"),
                ExpectedState(
                    f"light.magic_areas_native_light_groups_{slug}_accent_lights",
                    state="on",
                ),
            ]
        )
    return expectations


def _clear_expectations(rooms: Iterable[object]) -> list[ExpectedState]:
    """Return expected runtime state after occupancy clears and state timers settle."""
    expectations: list[ExpectedState] = []
    for room in rooms:
        slug = str(getattr(room, "slug"))
        second_slug = str(getattr(room, "second_light_slug"))
        expectations.extend(
            [
                ExpectedState(
                    f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                    state="off",
                    states_contains=("clear",),
                ),
                ExpectedState(f"light.{slug}_overhead", state="off"),
                ExpectedState(f"light.{slug}_{second_slug}", state="off"),
                ExpectedState(
                    f"light.magic_areas_native_light_groups_{slug}_overhead_lights",
                    state="off",
                ),
                ExpectedState(
                    f"light.magic_areas_native_light_groups_{slug}_sleep_lights",
                    state="off",
                ),
                ExpectedState(
                    f"light.magic_areas_native_light_groups_{slug}_all_lights",
                    state="off",
                ),
            ]
        )
    return expectations


async def _adaptive_lighting_sleep_expectations(
    client: HomeAssistantWs,
) -> list[ExpectedState]:
    """Return expectations for real AL sleep switches in the managed test room."""
    states = await client.call("get_states")
    if not isinstance(states, list):
        return []

    adaptive_lighting_room_sleep_switches = sorted(
        str(item.get("entity_id"))
        for item in states
        if isinstance(item, Mapping)
        and isinstance(item.get("entity_id"), str)
        and str(item["entity_id"]).startswith("switch.adaptive_lighting")
        and "_sleep_mode_" in str(item["entity_id"])
        and "adaptive_lighting_room" in str(item["entity_id"])
    )
    return [
        ExpectedState(entity_id, state="on")
        for entity_id in adaptive_lighting_room_sleep_switches
    ]


async def reset_control_matrix(client: HomeAssistantWs) -> None:
    """Reset all fake-house rooms used by the control matrix."""
    rooms = tuple(DEV_ROOMS)
    boolean_entities: list[str] = []
    for room in rooms:
        slug = str(getattr(room, "slug"))
        boolean_entities.extend(
            [
                f"input_boolean.{slug}_occupancy",
                f"input_boolean.{slug}_sleep",
                f"input_boolean.{slug}_accent",
                f"input_boolean.{slug}_overhead_power",
                second_power_entity(room),
            ]
        )
    await set_input_boolean(client, boolean_entities, False)
    await set_input_select(
        client,
        f"input_select.{STARTUP_UNKNOWN_ROOM_SLUG}_light_availability",
        "available",
    )
    await set_input_select(
        client,
        f"input_select.{STARTUP_UNAVAILABLE_ROOM_SLUG}_light_availability",
        "available",
    )
    for room in rooms:
        await set_input_number(client, f"input_number.{getattr(room, 'slug')}_lux", 350)
    await set_input_number(client, "input_number.outdoor_lux", 12000)


async def control_matrix(client: HomeAssistantWs, args: argparse.Namespace) -> None:
    """Run the multi-room control matrix and evaluate expected outcomes."""
    timing = SimulationTiming.from_args(args)
    rooms = _control_matrix_rooms()
    daylight_area_light_rooms = _daylight_area_light_rooms(rooms)
    non_daylight_area_light_rooms = _non_daylight_area_light_rooms(rooms)
    ambient_room = next(
        (room for room in rooms if getattr(room, "slug") == AMBIENT_RISE_ROOM_SLUG),
        None,
    )
    manual_direct_room = next(
        (
            room
            for room in rooms
            if getattr(room, "slug") == MANUAL_DIRECT_LIGHT_ROOM_SLUG
        ),
        None,
    )
    startup_unknown_room = next(
        (room for room in rooms if getattr(room, "slug") == STARTUP_UNKNOWN_ROOM_SLUG),
        None,
    )
    startup_unavailable_room = next(
        (
            room
            for room in rooms
            if getattr(room, "slug") == STARTUP_UNAVAILABLE_ROOM_SLUG
        ),
        None,
    )
    non_ambient_rooms = tuple(
        room for room in rooms if getattr(room, "slug") not in AMBIENT_RISE_ROOM_SLUGS
    )
    standard_dark_rooms = tuple(
        room
        for room in non_daylight_area_light_rooms
        if room not in (startup_unknown_room, startup_unavailable_room)
    )
    non_ambient_sensor_rooms = tuple(
        room
        for room in non_daylight_area_light_rooms
        if getattr(room, "slug") not in AMBIENT_RISE_ROOM_SLUGS
    )
    ambient_rooms = tuple(
        room for room in (ambient_room, manual_direct_room) if room is not None
    )
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)

    if args.enable_controls:
        await set_switch(client, _control_switches(rooms), True)
    await reset_control_matrix(client)
    await timing.wait_configured_minutes(SEEDED_CLEAR_TIMEOUT_MINUTES)
    await wait_for_states(
        client,
        _clear_expectations(rooms),
        timeout_seconds=max(
            timing.configured_minutes_timeout(SEEDED_CLEAR_TIMEOUT_MINUTES),
            30,
        ),
    )
    await timing.settle_setup()

    print("event: control matrix occupied while dark", flush=True)
    if startup_unknown_room is not None:
        await set_input_select(
            client,
            f"input_select.{STARTUP_UNKNOWN_ROOM_SLUG}_light_availability",
            "unknown",
        )
    if startup_unavailable_room is not None:
        await set_input_select(
            client,
            f"input_select.{STARTUP_UNAVAILABLE_ROOM_SLUG}_light_availability",
            "unavailable",
        )
    await set_input_boolean(
        client, [f"input_boolean.{getattr(room, 'slug')}_occupancy" for room in rooms], True
    )
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="dark occupied",
        expectations=(
            *_dark_occupied_expectations(standard_dark_rooms),
            *(
                _startup_unknown_expectations(startup_unknown_room)
                if startup_unknown_room is not None
                else []
            ),
            *(
                _startup_unavailable_expectations(startup_unavailable_room)
                if startup_unavailable_room is not None
                else []
            ),
            *_daylight_occupied_expectations(daylight_area_light_rooms),
        ),
    )

    print("event: control matrix fake lux bright", flush=True)
    if startup_unknown_room is not None:
        await set_input_select(
            client,
            f"input_select.{STARTUP_UNKNOWN_ROOM_SLUG}_light_availability",
            "available",
        )
    if startup_unavailable_room is not None:
        await set_input_select(
            client,
            f"input_select.{STARTUP_UNAVAILABLE_ROOM_SLUG}_light_availability",
            "available",
        )
    for room in non_ambient_sensor_rooms:
        await set_input_number(client, f"input_number.{getattr(room, 'slug')}_lux", 1300)
    await timing.settle_checkpoint()
    await wait_for_states(
        client,
        _bright_expectations(non_ambient_rooms),
        timeout_seconds=timing.configured_seconds_timeout(
            BRIGHT_OFF_RUNTIME_TIMEOUT_SECONDS
        ),
        poll_seconds=timing.runtime_poll_seconds,
    )
    await evaluation.evaluate(
        client,
        checkpoint="bright occupied",
        expectations=_bright_expectations(non_ambient_rooms),
    )
    for ambient_room_item in ambient_rooms:
        await evaluation.evaluate(
            client,
            checkpoint="ambient dark waiting",
            expectations=_ambient_dark_waiting_expectations(ambient_room_item),
        )

    if ambient_room is not None:
        print(
            "event: control matrix adaptive MA-output contaminated initial rise",
            flush=True,
        )
        await set_input_number(
            client,
            f"input_number.{AMBIENT_RISE_ROOM_SLUG}_lux",
            AMBIENT_BRIGHT_THRESHOLD_LUX,
        )
    if manual_direct_room is not None:
        print("event: control matrix adaptive manual light contamination", flush=True)
        await set_input_boolean(
            client,
            second_power_entity(manual_direct_room),
            True,
        )
        await set_input_number(
            client,
            f"input_number.{MANUAL_DIRECT_LIGHT_ROOM_SLUG}_lux",
            AMBIENT_BRIGHT_THRESHOLD_LUX,
        )
    if ambient_rooms:
        await timing.settle_checkpoint()
        if ambient_room is not None:
            await evaluation.evaluate(
                client,
                checkpoint="MA-output contaminated initial rise",
                expectations=_ma_output_contaminated_initial_rise_expectations(
                    ambient_room
                ),
            )
        if manual_direct_room is not None:
            await evaluation.evaluate(
                client,
                checkpoint="manual direct-light contamination bright",
                expectations=_manual_direct_light_contamination_expectations(
                    manual_direct_room
                ),
            )

        direct_light_window = float(
            max(
                getattr(ambient_room_item, "ambient_rise_window_seconds", 60)
                for ambient_room_item in ambient_rooms
            )
        )
        print(
            "event: control matrix adaptive ambient direct-light attribution "
            f"window jitter settle ({direct_light_window:.0f}s)",
            flush=True,
        )
        await asyncio.gather(
            *(
                jitter_input_number(
                    client,
                    entity_id=f"input_number.{getattr(ambient_room_item, 'slug')}_lux",
                    center=AMBIENT_BRIGHT_THRESHOLD_LUX,
                    seconds=direct_light_window,
                    amplitude=DEFAULT_LUX_JITTER,
                )
                for ambient_room_item in ambient_rooms
            )
        )

        print("event: control matrix adaptive ambient daylight ramp", flush=True)
        await asyncio.gather(
            *(
                ramp_input_number(
                    client,
                    entity_id=f"input_number.{getattr(ambient_room_item, 'slug')}_lux",
                    start=AMBIENT_BRIGHT_THRESHOLD_LUX,
                    end=AMBIENT_DAYLIGHT_LUX,
                    seconds=args.ramp_seconds,
                )
                for ambient_room_item in ambient_rooms
            )
        )
        await asyncio.gather(
            *(
                jitter_input_number(
                    client,
                    entity_id=f"input_number.{getattr(ambient_room_item, 'slug')}_lux",
                    center=AMBIENT_DAYLIGHT_LUX,
                    seconds=timing.checkpoint_settle_seconds,
                    amplitude=DEFAULT_LUX_JITTER,
                )
                for ambient_room_item in ambient_rooms
            )
        )
        for ambient_room_item in ambient_rooms:
            await evaluation.evaluate(
                client,
                checkpoint="ambient rise bright",
                expectations=_ambient_rise_bright_expectations(ambient_room_item),
            )

    print("event: control matrix accent active", flush=True)
    await set_input_boolean(
        client, [f"input_boolean.{getattr(room, 'slug')}_accent" for room in rooms], True
    )
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="accent active",
        expectations=_accent_expectations(rooms),
    )

    print("event: control matrix sleep active", flush=True)
    await set_input_boolean(
        client, [f"input_boolean.{getattr(room, 'slug')}_sleep" for room in rooms], True
    )
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="sleep active",
        expectations=(
            *_sleep_expectations(rooms),
            *(await _adaptive_lighting_sleep_expectations(client)),
        ),
    )

    print("event: control matrix clear", flush=True)
    await set_input_boolean(
        client,
        [
            entity_id
            for room in rooms
            for entity_id in (
                f"input_boolean.{getattr(room, 'slug')}_occupancy",
                f"input_boolean.{getattr(room, 'slug')}_sleep",
                f"input_boolean.{getattr(room, 'slug')}_accent",
            )
        ],
        False,
    )
    await timing.wait_configured_minutes(SEEDED_CLEAR_TIMEOUT_MINUTES)
    await evaluation.evaluate(
        client,
        checkpoint="clear settled",
        expectations=_clear_expectations(rooms),
    )

    evaluation.write()


async def disabled_light_controls(
    client: HomeAssistantWs, args: argparse.Namespace
) -> None:
    """Assert disabled Magic Areas light-control switches block light movement."""
    timing = SimulationTiming.from_args(args)
    rooms = _control_matrix_rooms()
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)

    await reset_control_matrix(client)
    await set_switch(client, _control_switches(rooms), False)
    await timing.settle_setup()

    print("event: disabled light controls occupied while dark", flush=True)
    await set_input_boolean(
        client,
        [f"input_boolean.{getattr(room, 'slug')}_occupancy" for room in rooms],
        True,
    )
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="disabled light controls do not turn on lights",
        expectations=_disabled_light_control_expectations(rooms),
    )
    evaluation.write()


async def manual_override(client: HomeAssistantWs, args: argparse.Namespace) -> None:
    """Run a live manual-override and clear/reclaim scenario."""
    timing = SimulationTiming.from_args(args)
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)
    area_state = "binary_sensor.magic_areas_presence_tracking_living_room_area_state"

    await reset_fake_house(client)
    if args.enable_controls:
        await set_switch(
            client,
            "switch.magic_areas_light_groups_living_room_light_control",
            True,
        )
    await timing.settle_setup()

    print("event: manual override occupied while dark", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_occupancy", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="occupied dark controlled",
        expectations=(
            ExpectedState(area_state, state="on", states_contains=("occupied", "dark")),
            ExpectedState("light.living_room_overhead", state="on"),
            ExpectedState(
                "light.magic_areas_native_light_groups_living_room_overhead_lights",
                state="on",
            ),
        ),
    )

    print("event: manual override user turns overhead off", flush=True)
    await set_light(client, "light.living_room_overhead", False)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="manual off held",
        expectations=(
            ExpectedState(area_state, state="on", states_contains=("occupied", "dark")),
            ExpectedState("light.living_room_overhead", state="off"),
            ExpectedState(
                "light.magic_areas_native_light_groups_living_room_overhead_lights",
                state="off",
            ),
        ),
    )

    print("event: manual override bright/dark churn while occupied", flush=True)
    await set_input_number(client, "input_number.living_room_lux", 1300)
    await timing.settle_checkpoint()
    await set_input_number(client, "input_number.living_room_lux", 350)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="manual override blocks automatic reacquire",
        expectations=(
            ExpectedState(area_state, state="on", states_contains=("occupied", "dark")),
            ExpectedState("light.living_room_overhead", state="off"),
            ExpectedState(
                "light.magic_areas_native_light_groups_living_room_overhead_lights",
                state="off",
            ),
        ),
    )

    print("event: manual override clear and settle", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_occupancy", False)
    await timing.wait_configured_minutes(SEEDED_CLEAR_TIMEOUT_MINUTES)
    await evaluation.evaluate(
        client,
        checkpoint="manual override clear resets",
        expectations=(
            ExpectedState(area_state, state="off", states_contains=("clear",)),
            ExpectedState("light.living_room_overhead", state="off"),
            ExpectedState(
                "light.magic_areas_native_light_groups_living_room_overhead_lights",
                state="off",
            ),
        ),
    )

    print("event: manual override reoccupied after clear", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_occupancy", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="reoccupied after clear reacquires",
        expectations=(
            ExpectedState(area_state, state="on", states_contains=("occupied", "dark")),
            ExpectedState("light.living_room_overhead", state="on"),
            ExpectedState(
                "light.magic_areas_native_light_groups_living_room_overhead_lights",
                state="on",
            ),
        ),
    )
    evaluation.write()


async def presence_hold(client: HomeAssistantWs, args: argparse.Namespace) -> None:
    """Run a live presence-hold occupancy scenario."""
    timing = SimulationTiming.from_args(args)
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)
    area_state = "binary_sensor.magic_areas_presence_tracking_living_room_area_state"
    presence_hold_switch = "switch.magic_areas_presence_hold_living_room"

    await reset_fake_house(client)
    await set_switch(client, presence_hold_switch, False)
    if args.enable_controls:
        await set_switch(
            client,
            "switch.magic_areas_light_groups_living_room_light_control",
            True,
        )
    await wait_for_state(
        client,
        area_state,
        "off",
        timeout_seconds=timing.configured_minutes_timeout(SEEDED_CLEAR_TIMEOUT_MINUTES),
    )
    await timing.settle_setup()

    print("event: presence hold on with occupancy input off", flush=True)
    await set_switch(client, presence_hold_switch, True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="presence hold occupies room",
        expectations=(
            ExpectedState("binary_sensor.living_room_occupancy", state="off"),
            ExpectedState(presence_hold_switch, state="on"),
            ExpectedState(area_state, state="on", states_contains=("occupied", "dark")),
            ExpectedState("light.living_room_overhead", state="on"),
            ExpectedState(
                "light.magic_areas_native_light_groups_living_room_overhead_lights",
                state="on",
            ),
        ),
    )

    print("event: presence hold off and clear", flush=True)
    await set_switch(client, presence_hold_switch, False)
    await timing.wait_configured_minutes(SEEDED_CLEAR_TIMEOUT_MINUTES)
    await evaluation.evaluate(
        client,
        checkpoint="presence hold clears room",
        expectations=(
            ExpectedState(presence_hold_switch, state="off"),
            ExpectedState(area_state, state="off", states_contains=("clear",)),
            ExpectedState("light.living_room_overhead", state="off"),
            ExpectedState(
                "light.magic_areas_native_light_groups_living_room_overhead_lights",
                state="off",
            ),
        ),
    )
    evaluation.write()


async def adaptive_lighting_manual_release(
    client: HomeAssistantWs, args: argparse.Namespace
) -> None:
    """Run a live AL manual-control release scenario."""
    timing = SimulationTiming.from_args(args)
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)
    slug = "adaptive_lighting_room"
    area_state = f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state"
    overhead = f"light.{slug}_overhead"
    lamp = f"light.{slug}_lamp"
    control_switch = f"switch.magic_areas_light_groups_{slug}_light_control"
    overhead_group = f"light.magic_areas_native_light_groups_{slug}_overhead_lights"

    await reset_control_matrix(client)
    await set_switch(client, control_switch, True)
    await timing.settle_setup()

    print("event: adaptive lighting manual release occupied while dark", flush=True)
    await set_input_boolean(client, f"input_boolean.{slug}_occupancy", True)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="adaptive lighting room controlled on",
        expectations=(
            ExpectedState(area_state, state="on", states_contains=("occupied", "dark")),
            ExpectedState(overhead, state="on"),
            ExpectedState(overhead_group, state="on"),
        ),
    )

    print("event: adaptive lighting marks room lights manual", flush=True)
    await call_service(
        client,
        "adaptive_lighting",
        "set_manual_control",
        entity_id=ADAPTIVE_LIGHTING_ALL_LIGHTS_SLEEP_SWITCH,
        service_data={
            "lights": [overhead, lamp],
            "manual_control": True,
        },
    )
    await timing.settle_checkpoint()

    print("event: manual off then clear should release AL manual control", flush=True)
    await set_light(client, overhead, False)
    await timing.settle_checkpoint()

    async def clear_room() -> None:
        await set_input_boolean(client, f"input_boolean.{slug}_occupancy", False)
        await timing.wait_configured_minutes(SEEDED_CLEAR_TIMEOUT_MINUTES)

    service_data = await wait_for_service_call_event(
        args,
        domain="adaptive_lighting",
        service="set_manual_control",
        trigger=clear_room,
        expected_lights=(overhead,),
        expected_manual_control=False,
        timeout_seconds=timing.configured_minutes_event_timeout(
            SEEDED_CLEAR_TIMEOUT_MINUTES,
            event_margin_seconds=10,
        ),
    )
    print(
        "event: observed adaptive_lighting.set_manual_control release "
        f"{dict(service_data)}",
        flush=True,
    )
    await evaluation.evaluate(
        client,
        checkpoint="adaptive lighting manual release clear settled",
        expectations=(
            ExpectedState(area_state, state="off", states_contains=("clear",)),
            ExpectedState(overhead, state="off"),
            ExpectedState(overhead_group, state="off"),
        ),
    )
    evaluation.write()


async def adaptive_negative_context(
    client: HomeAssistantWs, args: argparse.Namespace
) -> None:
    """Run adaptive bright-off negative outside-context scenarios."""
    timing = SimulationTiming.from_args(args)
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)
    binary_room = room_by_slug()["adaptive_binary_room"]
    lux_room = room_by_slug()["adaptive_lux_room"]
    rooms = (binary_room, lux_room)

    await reset_control_matrix(client)
    await set_input_number(client, "input_number.outdoor_lux", 100)
    await asyncio.gather(
        *(
            wait_for_state(
                client,
                f"binary_sensor.magic_areas_presence_tracking_{getattr(room, 'slug')}_area_state",
                "off",
                timeout_seconds=timing.configured_minutes_timeout(
                    SEEDED_CLEAR_TIMEOUT_MINUTES
                ),
            )
            for room in rooms
        )
    )
    if args.enable_controls:
        await set_switch(client, _control_switches(rooms), True)
    await timing.settle_setup()

    print("event: adaptive negative context occupied while dark", flush=True)
    await set_input_boolean(
        client,
        [f"input_boolean.{getattr(room, 'slug')}_occupancy" for room in rooms],
        True,
    )
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="adaptive negative occupied dark",
        expectations=_dark_occupied_expectations(rooms),
    )

    print("event: adaptive negative outside not bright / lux below minimum", flush=True)
    for room in rooms:
        await set_input_number(client, f"input_number.{getattr(room, 'slug')}_lux", 1300)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="adaptive negative outside context blocks off",
        expectations=(
            ExpectedState("binary_sensor.outdoor_bright", state="off"),
            ExpectedState("sensor.outdoor_illuminance", state="100.0"),
            ExpectedState(
                "binary_sensor.magic_areas_presence_tracking_adaptive_binary_room_area_state",
                state="on",
                states_contains=("occupied", "bright"),
            ),
            ExpectedState("light.adaptive_binary_room_overhead", state="on"),
            ExpectedState(
                "binary_sensor.magic_areas_presence_tracking_adaptive_lux_room_area_state",
                state="on",
                states_contains=("occupied", "bright"),
            ),
            ExpectedState("light.adaptive_lux_room_overhead", state="on"),
        ),
    )

    print("event: adaptive negative outside lux insufficient contrast", flush=True)
    await set_input_number(client, "input_number.adaptive_lux_room_lux", 350)
    await timing.settle_checkpoint()
    await set_input_number(client, "input_number.outdoor_lux", 1400)
    await set_input_number(client, "input_number.adaptive_lux_room_lux", 1300)
    await timing.settle_checkpoint()
    await evaluation.evaluate(
        client,
        checkpoint="adaptive negative outside lux contrast blocks off",
        expectations=(
            ExpectedState("sensor.outdoor_illuminance", state="1400.0"),
            ExpectedState(
                "binary_sensor.magic_areas_presence_tracking_adaptive_lux_room_area_state",
                state="on",
                states_contains=("occupied", "bright"),
            ),
            ExpectedState("light.adaptive_lux_room_overhead", state="on"),
        ),
    )
    evaluation.write()
