"""Shared fake-house state and sensor-driving helpers."""

from __future__ import annotations

import asyncio
import math

from scripts.ha_dev_bootstrap import HomeAssistantWs
from scripts.ha_dev_simulation.client import (
    set_input_boolean,
    set_input_number,
    set_input_select,
    set_switch,
)
from scripts.ha_dev_simulation.entities import DEFAULT_LUX_JITTER


async def reset_fake_house(client: HomeAssistantWs) -> None:
    """Reset fake-house controls to a deterministic baseline."""
    await set_input_boolean(
        client,
        [
            "input_boolean.living_room_occupancy",
            "input_boolean.living_room_sleep",
            "input_boolean.living_room_accent",
            "input_boolean.living_room_overhead_power",
            "input_boolean.living_room_lamp_power",
            "input_boolean.bathroom_occupancy",
            "input_boolean.bathroom_sleep",
            "input_boolean.bathroom_overhead_power",
            "input_boolean.bathroom_sleep_light_power",
            "input_boolean.setup_room_occupancy",
            "input_boolean.setup_room_motion",
            "input_boolean.setup_room_sleep",
            "input_boolean.setup_room_accent",
            "input_boolean.setup_room_overhead_power",
            "input_boolean.setup_room_task_power",
            "input_boolean.setup_room_accent_power",
            "input_boolean.setup_room_sleep_light_power",
            "input_boolean.setup_room_fan_power",
            "input_boolean.setup_room_blinds_open",
            "input_boolean.fan_room_occupancy",
            "input_boolean.fan_room_sleep",
            "input_boolean.fan_room_accent",
            "input_boolean.fan_room_exhaust_power",
            "input_boolean.cover_room_occupancy",
            "input_boolean.cover_room_sleep",
            "input_boolean.cover_room_accent",
            "input_boolean.cover_room_blinds_open",
            "input_boolean.cover_room_shades_open",
            "input_boolean.cover_room_curtains_open",
            "input_boolean.cover_room_shutters_open",
            "input_boolean.cover_room_window_open",
            "input_boolean.cover_room_garage_open",
            "input_boolean.cover_room_door_open",
        ],
        False,
    )
    await set_input_number(client, "input_number.living_room_lux", 350)
    await set_input_number(client, "input_number.bathroom_lux", 120)
    await set_input_number(client, "input_number.setup_room_lux", 350)
    await set_input_number(client, "input_number.setup_room_humidity", 45)
    await set_input_number(client, "input_number.fan_room_lux", 350)
    await set_input_number(client, "input_number.fan_room_humidity", 45)
    await set_input_number(client, "input_number.fan_room_voc", 0)
    await set_input_select(client, "input_select.fan_room_humidity_availability", "available")
    await set_input_select(client, "input_select.fan_room_voc_availability", "available")
    await set_input_number(client, "input_number.cover_room_lux", 350)
    await set_input_number(client, "input_number.outdoor_lux", 12000)
    await set_switch(
        client,
        [
            "switch.magic_areas_presence_hold_fan_room",
            "switch.magic_areas_presence_hold_cover_room",
        ],
        False,
    )


async def ramp_input_number(
    client: HomeAssistantWs,
    *,
    entity_id: str,
    start: float,
    end: float,
    seconds: float,
    step_seconds: float = 1.0,
) -> None:
    """Ramp an input_number over a duration."""
    if seconds <= 0:
        await set_input_number(client, entity_id, end)
        return

    steps = max(1, math.ceil(seconds / step_seconds))
    for index in range(steps + 1):
        ratio = index / steps
        value = start + ((end - start) * ratio)
        await set_input_number(client, entity_id, value)
        if index < steps:
            await asyncio.sleep(seconds / steps)


async def jitter_input_number(
    client: HomeAssistantWs,
    *,
    entity_id: str,
    center: float,
    seconds: float,
    amplitude: float = DEFAULT_LUX_JITTER,
    step_seconds: float = 1.0,
) -> None:
    """Emit deterministic tiny steady-state input_number changes."""
    if seconds <= 0:
        await set_input_number(client, entity_id, center)
        return

    offsets = (-1.0, 0.5, -0.5, 1.0, 0.0)
    steps = max(1, math.ceil(seconds / step_seconds))
    for index in range(steps):
        offset = offsets[index % len(offsets)]
        await set_input_number(client, entity_id, center + (offset * amplitude))
        await asyncio.sleep(seconds / steps)
    await set_input_number(client, entity_id, center)
