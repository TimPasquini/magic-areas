"""Simulation connection, tracing, and scenario dispatch."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from scripts.ha_dev_bootstrap import HomeAssistantWs, wait_for_ha
from scripts.ha_dev_simulation.scenarios.fan_cover import fan_cover_matrix
from scripts.ha_dev_simulation.scenarios.lights import (
    adaptive_lighting_manual_release,
    adaptive_negative_context,
    control_matrix,
    disabled_light_controls,
    manual_override,
    presence_hold,
)
from scripts.ha_dev_simulation.scenarios.living_room import living_room_demo
from scripts.ha_dev_simulation.traces import TraceRecorder, trace_entities
from scripts.ha_dev_token import DEV_HA_LONG_LIVED_TOKEN


async def simulate(args: argparse.Namespace) -> None:
    """Run a HA dev simulation."""
    await wait_for_ha(args.url, DEV_HA_LONG_LIVED_TOKEN, args.wait)
    async with HomeAssistantWs(args.url, DEV_HA_LONG_LIVED_TOKEN) as client:
        output_path = None if args.no_trace_file else Path(args.trace_file)
        recorder = TraceRecorder(
            client=client,
            entity_ids=trace_entities(args),
            output_path=output_path,
            sample_seconds=args.sample_seconds,
        )
        trace_task = asyncio.create_task(recorder.run())
        try:
            if args.scenario == "living-room-demo":
                await living_room_demo(client, args)
            elif args.scenario == "control-matrix":
                await control_matrix(client, args)
            elif args.scenario == "disabled-light-controls":
                await disabled_light_controls(client, args)
            elif args.scenario == "adaptive-negative-context":
                await adaptive_negative_context(client, args)
            elif args.scenario == "manual-override":
                await manual_override(client, args)
            elif args.scenario == "presence-hold":
                await presence_hold(client, args)
            elif args.scenario == "adaptive-lighting-manual-release":
                await adaptive_lighting_manual_release(client, args)
            elif args.scenario == "fan-cover-matrix":
                await fan_cover_matrix(client, args)
            else:  # pragma: no cover - argparse choices guard this path.
                raise RuntimeError(f"Unknown scenario: {args.scenario}")
        finally:
            recorder.stop()
            await trace_task
        if output_path is not None:
            print(f"trace written: {output_path}", flush=True)
