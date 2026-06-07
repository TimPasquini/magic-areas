"""Trace entity selection and state-change recording for simulation."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import asyncio
import json
import time
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from pathlib import Path

from scripts.ha_dev_bootstrap import DEV_ROOMS, HomeAssistantWs
from scripts.ha_dev_simulation.client import get_states
from scripts.ha_dev_simulation.entities import (
    ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_BRIGHTNESS_SWITCH,
    ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_COLOR_SWITCH,
    ADAPTIVE_LIGHTING_ALL_LIGHTS_SLEEP_SWITCH,
    AMBIENT_RISE_SIGNAL_ENTITY,
    BATHROOM_TRACE_ENTITIES,
    CONTROL_MATRIX_TRACE_SLUGS,
    FAN_COVER_TRACE_ENTITIES,
    LIVING_ROOM_TRACE_ENTITIES,
    MANUAL_DIRECT_LIGHT_RISE_SIGNAL_ENTITY,
)
from scripts.ha_dev_simulation.models import TraceEvent, TraceState


def room_by_slug() -> dict[str, object]:
    """Return dev rooms keyed by slug."""
    return {room.slug: room for room in DEV_ROOMS}


def second_power_entity(room: object) -> str:
    """Return the backing input_boolean for a room's secondary light."""
    slug = str(getattr(room, "slug"))
    second_slug = str(getattr(room, "second_light_slug"))
    if second_slug == "sleep_light":
        return f"input_boolean.{slug}_sleep_light_power"
    return f"input_boolean.{slug}_lamp_power"


def _room_trace_entities(room: object) -> tuple[str, ...]:
    """Return trace entities for one seeded fake room."""
    slug = str(getattr(room, "slug"))
    return (
        f"input_boolean.{slug}_occupancy",
        f"input_boolean.{slug}_sleep",
        f"input_boolean.{slug}_accent",
        f"input_boolean.{slug}_overhead_power",
        second_power_entity(room),
        f"input_number.{slug}_lux",
        f"binary_sensor.{slug}_occupancy",
        f"binary_sensor.{slug}_sleep",
        f"binary_sensor.{slug}_accent",
        f"binary_sensor.{slug}_light",
        f"sensor.{slug}_illuminance",
        f"light.{slug}_overhead",
        f"light.{slug}_{getattr(room, 'second_light_slug')}",
        f"light.magic_areas_native_light_groups_{slug}_overhead_lights",
        f"light.magic_areas_native_light_groups_{slug}_sleep_lights",
        f"light.magic_areas_native_light_groups_{slug}_accent_lights",
        f"light.magic_areas_native_light_groups_{slug}_all_lights",
        f"switch.magic_areas_light_groups_{slug}_light_control",
        f"switch.magic_areas_presence_hold_{slug}",
        f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
    )


def control_matrix_trace_entities() -> tuple[str, ...]:
    """Return trace entities for the expanded control matrix scenario."""
    rooms = room_by_slug()
    entity_ids: list[str] = [
        "input_number.outdoor_lux",
        "binary_sensor.outdoor_bright",
        "sensor.outdoor_illuminance",
    ]
    for slug in CONTROL_MATRIX_TRACE_SLUGS:
        room = rooms.get(slug)
        if room is not None:
            entity_ids.extend(_room_trace_entities(room))
    entity_ids.extend(
        [
            AMBIENT_RISE_SIGNAL_ENTITY,
            MANUAL_DIRECT_LIGHT_RISE_SIGNAL_ENTITY,
            "switch.adaptive_lighting_magic_areas_adaptive_lighting_room_all_lights",
            "switch.adaptive_lighting_sleep_mode_magic_areas_adaptive_lighting_room_all_lights",
            "switch.adaptive_lighting_adapt_brightness_magic_areas_adaptive_lighting_room_all_lights",
            "switch.adaptive_lighting_adapt_color_magic_areas_adaptive_lighting_room_all_lights",
            ADAPTIVE_LIGHTING_ALL_LIGHTS_SLEEP_SWITCH,
            ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_BRIGHTNESS_SWITCH,
            ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_COLOR_SWITCH,
            "switch.adaptive_lighting_magic_areas_adaptive_lighting_room_overhead",
            "switch.adaptive_lighting_sleep_mode_magic_areas_adaptive_lighting_room_overhead",
            "switch.adaptive_lighting_magic_areas_adaptive_lighting_room_sleep",
            "switch.adaptive_lighting_sleep_mode_magic_areas_adaptive_lighting_room_sleep",
        ]
    )
    return tuple(dict.fromkeys(entity_ids))


def trace_entities(args: argparse.Namespace) -> tuple[str, ...]:
    """Return entity ids to trace for a scenario."""
    entity_ids: list[str] = []
    if args.scenario == "living-room-demo":
        entity_ids.extend(LIVING_ROOM_TRACE_ENTITIES)
    if args.scenario == "control-matrix":
        entity_ids.extend(control_matrix_trace_entities())
    if args.scenario == "disabled-light-controls":
        entity_ids.extend(control_matrix_trace_entities())
    if args.scenario == "adaptive-negative-context":
        entity_ids.extend(control_matrix_trace_entities())
    if args.scenario == "manual-override":
        entity_ids.extend(LIVING_ROOM_TRACE_ENTITIES)
    if args.scenario == "presence-hold":
        entity_ids.extend(LIVING_ROOM_TRACE_ENTITIES)
    if args.scenario == "adaptive-lighting-manual-release":
        entity_ids.extend(control_matrix_trace_entities())
    if args.scenario == "fan-cover-matrix":
        entity_ids.extend(FAN_COVER_TRACE_ENTITIES)
    if args.include_bathroom:
        entity_ids.extend(BATHROOM_TRACE_ENTITIES)
    entity_ids.extend(args.trace_entity)
    return tuple(dict.fromkeys(entity_ids))


@dataclass(slots=True)
class TraceRecorder:
    """Poll HA state and emit compact state-change traces."""

    client: HomeAssistantWs
    entity_ids: tuple[str, ...]
    output_path: Path | None
    sample_seconds: float
    started_at: float = field(default_factory=time.time)
    _last: dict[str, TraceState | None] = field(default_factory=dict)
    _stop: asyncio.Event = field(default_factory=asyncio.Event)

    async def run(self) -> None:
        """Trace state changes until stopped."""
        if self.output_path is not None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text("", encoding="utf-8")

        while not self._stop.is_set():
            await self.sample()
            with suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=self.sample_seconds)

    def stop(self) -> None:
        """Request trace loop shutdown."""
        self._stop.set()

    async def sample(self) -> None:
        """Sample HA states and emit changes."""
        states = await get_states(self.client, self.entity_ids)
        for entity_id in self.entity_ids:
            new = states.get(entity_id)
            old = self._last.get(entity_id)
            if entity_id not in self._last or old != new:
                self._last[entity_id] = new
                self._emit(entity_id=entity_id, old=old, new=new)

    def _emit(
        self,
        *,
        entity_id: str,
        old: TraceState | None,
        new: TraceState | None,
    ) -> None:
        event = TraceEvent(
            elapsed=round(time.time() - self.started_at, 3),
            wall_time=time.strftime("%H:%M:%S"),
            entity_id=entity_id,
            old=old,
            new=new,
        )
        old_state = old.state if old else "<missing>"
        new_state = new.state if new else "<missing>"
        states_attr = (
            f" states={new.states_attribute}" if new and new.states_attribute else ""
        )
        print(
            f"[{event.elapsed:7.3f}s {event.wall_time}] "
            f"{entity_id}: {old_state} -> {new_state}{states_attr}",
            flush=True,
        )
        if self.output_path is not None:
            with self.output_path.open("a", encoding="utf-8") as trace_file:
                trace_file.write(json.dumps(asdict(event), sort_keys=True) + "\n")
