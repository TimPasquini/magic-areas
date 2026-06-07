"""Wall-clock living-room demonstration simulation."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import asyncio
import time

from scripts.ha_dev_bootstrap import HomeAssistantWs
from scripts.ha_dev_simulation.client import set_input_boolean, set_switch
from scripts.ha_dev_simulation.reset import ramp_input_number, reset_fake_house
from scripts.ha_dev_simulation_plan import (
    LivingRoomDemoPlan,
    build_living_room_demo_plan,
)


def _wall_time(timestamp: float) -> str:
    """Format an absolute timestamp for operator-readable output."""
    return time.strftime("%H:%M:%S", time.localtime(timestamp))


def _print_plan(plan: LivingRoomDemoPlan) -> None:
    """Print the deterministic schedule the live runner will execute."""
    print("simulation schedule:", flush=True)
    print(f"  occupancy on: {_wall_time(plan.occupancy_on_at)}", flush=True)
    print(
        "  living-room lux ramp: "
        f"{_wall_time(plan.lux_ramp.start_at)} -> {_wall_time(plan.lux_ramp.end_at)} "
        f"(midpoint {_wall_time(plan.lux_ramp.midpoint_at)})",
        flush=True,
    )
    print(f"  accent on: {_wall_time(plan.accent_on_at)}", flush=True)
    print(
        f"  sleep on, accent off: {_wall_time(plan.sleep_on_accent_off_at)}",
        flush=True,
    )
    print(f"  occupancy off: {_wall_time(plan.occupancy_off_at)}", flush=True)
    print(f"  trace end: {_wall_time(plan.final_done_at)}", flush=True)


async def sleep_until_at(timestamp: float, *, label: str) -> None:
    """Sleep until an absolute wall-clock timestamp."""
    delay = max(0.0, timestamp - time.time())
    print(f"waiting {delay:.2f}s for {label} ({_wall_time(timestamp)})", flush=True)
    await asyncio.sleep(delay)


async def sleep_until_plan_done(plan: LivingRoomDemoPlan, *, label: str) -> None:
    """Sleep until the plan reaches a non-event observation boundary."""
    await sleep_until_at(plan.final_done_at, label=label)


async def living_room_demo(client: HomeAssistantWs, args: argparse.Namespace) -> None:
    """Run a living-room state and lux simulation."""
    await reset_fake_house(client)
    if args.enable_controls:
        await set_switch(
            client,
            [
                "switch.magic_areas_light_groups_living_room_light_control",
                "switch.magic_areas_light_groups_bathroom_light_control",
            ],
            True,
        )

    plan = build_living_room_demo_plan(
        started_at=time.time(),
        cycle_seconds=args.cycle_seconds,
        ramp_seconds=args.ramp_seconds,
        state_period_cycles=args.state_period_cycles,
        final_cycles=args.final_cycles,
        setup_settle_seconds=args.setup_settle_seconds,
    )
    _print_plan(plan)

    await sleep_until_at(plan.occupancy_on_at, label="occupancy on")
    print("event: living room occupied while room is dark", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_occupancy", True)

    await sleep_until_at(
        plan.lux_ramp.start_at,
        label="extended-time / hold observation window",
    )
    print(
        "event: living room lux ramp "
        f"{plan.lux_ramp.start_value:g} -> {plan.lux_ramp.end_value:g} "
        f"over {args.ramp_seconds:.1f}s",
        flush=True,
    )
    await ramp_input_number(
        client,
        entity_id=plan.lux_ramp.entity_id,
        start=plan.lux_ramp.start_value,
        end=plan.lux_ramp.end_value,
        seconds=args.ramp_seconds,
    )

    await sleep_until_at(plan.accent_on_at, label="accent on")
    print("event: living room accent on", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_accent", True)

    await sleep_until_at(plan.sleep_on_accent_off_at, label="sleep on, accent off")
    print("event: living room sleep on, accent off", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_accent", False)
    await set_input_boolean(client, "input_boolean.living_room_sleep", True)

    await sleep_until_at(plan.occupancy_off_at, label="occupancy off")
    print("event: living room occupancy off", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_occupancy", False)

    await sleep_until_plan_done(
        plan,
        label="final clear / extended-timeout observation window",
    )
