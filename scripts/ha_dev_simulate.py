#!/usr/bin/env python3
"""Drive the Magic Areas HA dev fake-house through timed simulation scenarios."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from contextlib import suppress
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ha_dev_bootstrap import DEFAULT_URL, DEV_ROOMS, HomeAssistantWs, wait_for_ha
from ha_dev_simulation_plan import (
    DEFAULT_SETUP_SETTLE_SECONDS,
    LivingRoomDemoPlan,
    build_living_room_demo_plan,
)
from ha_dev_token import DEV_HA_LONG_LIVED_TOKEN

DEFAULT_CYCLE_SECONDS = 30.0
DEFAULT_RAMP_SECONDS = 10.0
DEFAULT_SAMPLE_SECONDS = 0.5
DEFAULT_STATE_PERIOD_CYCLES = 2.0
DEFAULT_TRACE_PATH = "dev/ha/runtime/traces/latest.jsonl"
ADAPTIVE_LIGHTING_ALL_LIGHTS_SLEEP_SWITCH = (
    "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
    "adaptive_lighting_sleep_mode_ma_adaptive_lighting_room_all_lights"
)
ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_BRIGHTNESS_SWITCH = (
    "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
    "adaptive_lighting_adapt_brightness_ma_adaptive_lighting_room_all_lights"
)
ADAPTIVE_LIGHTING_ALL_LIGHTS_ADAPT_COLOR_SWITCH = (
    "switch.adaptive_lighting_ma_adaptive_lighting_room_all_lights_"
    "adaptive_lighting_adapt_color_ma_adaptive_lighting_room_all_lights"
)

LIVING_ROOM_TRACE_ENTITIES: tuple[str, ...] = (
    "input_boolean.living_room_occupancy",
    "input_boolean.living_room_sleep",
    "input_boolean.living_room_accent",
    "input_boolean.living_room_overhead_power",
    "input_boolean.living_room_lamp_power",
    "input_number.living_room_lux",
    "input_number.outdoor_lux",
    "binary_sensor.living_room_occupancy",
    "binary_sensor.living_room_sleep",
    "binary_sensor.living_room_accent",
    "binary_sensor.living_room_light",
    "binary_sensor.outdoor_bright",
    "sensor.living_room_illuminance",
    "sensor.outdoor_illuminance",
    "light.living_room_overhead",
    "light.living_room_lamp",
    "light.magic_areas_native_light_groups_living_room_overhead_lights",
    "light.magic_areas_native_light_groups_living_room_sleep_lights",
    "light.magic_areas_native_light_groups_living_room_accent_lights",
    "light.magic_areas_native_light_groups_living_room_all_lights",
    "switch.magic_areas_light_groups_living_room_light_control",
    "switch.magic_areas_presence_hold_living_room",
    "binary_sensor.magic_areas_presence_tracking_living_room_area_state",
    "binary_sensor.magic_areas_threshold_living_room_light",
)

BATHROOM_TRACE_ENTITIES: tuple[str, ...] = (
    "input_boolean.bathroom_occupancy",
    "input_boolean.bathroom_sleep",
    "input_boolean.bathroom_overhead_power",
    "input_boolean.bathroom_sleep_light_power",
    "input_number.bathroom_lux",
    "binary_sensor.bathroom_occupancy",
    "binary_sensor.bathroom_sleep",
    "binary_sensor.bathroom_light",
    "sensor.bathroom_illuminance",
    "light.bathroom_overhead",
    "light.bathroom_sleep_light",
    "light.magic_areas_native_light_groups_bathroom_overhead_lights",
    "light.magic_areas_native_light_groups_bathroom_sleep_lights",
    "light.magic_areas_native_light_groups_bathroom_all_lights",
    "switch.magic_areas_light_groups_bathroom_light_control",
    "switch.magic_areas_presence_hold_bathroom",
    "binary_sensor.magic_areas_presence_tracking_bathroom_area_state",
    "binary_sensor.magic_areas_threshold_bathroom_light",
)

CONTROL_MATRIX_ROOM_SLUGS: tuple[str, ...] = (
    "classic_sun_room",
    "classic_sensor_room",
    "advisory_sun_room",
    "advisory_sensor_room",
    "startup_unknown_room",
    "startup_unavailable_room",
    "adaptive_sun_room",
    "adaptive_binary_room",
    "adaptive_lux_room",
    "adaptive_ambient_room",
    "adaptive_manual_light_room",
    "adaptive_lighting_room",
)

CONTROL_MATRIX_TRACE_SLUGS: tuple[str, ...] = (
    "classic_sun_room",
    "classic_sensor_room",
    "advisory_sun_room",
    "advisory_sensor_room",
    "startup_unknown_room",
    "startup_unavailable_room",
    "adaptive_sun_room",
    "adaptive_binary_room",
    "adaptive_lux_room",
    "adaptive_ambient_room",
    "adaptive_manual_light_room",
    "adaptive_lighting_room",
)

AMBIENT_RISE_ROOM_SLUG = "adaptive_ambient_room"
MANUAL_DIRECT_LIGHT_ROOM_SLUG = "adaptive_manual_light_room"
AMBIENT_RISE_ROOM_SLUGS = frozenset(
    {AMBIENT_RISE_ROOM_SLUG, MANUAL_DIRECT_LIGHT_ROOM_SLUG}
)
STARTUP_UNKNOWN_ROOM_SLUG = "startup_unknown_room"
STARTUP_UNAVAILABLE_ROOM_SLUG = "startup_unavailable_room"
DAYLIGHT_AREA_LIGHT_ROOM_SLUGS = frozenset(
    {"classic_sun_room", "advisory_sun_room"}
)


def _ambient_rise_signal_entity(slug: str) -> str:
    """Return the managed ambient-rise Trend helper entity id for a room slug."""
    return f"binary_sensor.magic_areas_signals_{slug}_trend_ambient_rise"


AMBIENT_RISE_SIGNAL_ENTITY = _ambient_rise_signal_entity(AMBIENT_RISE_ROOM_SLUG)
MANUAL_DIRECT_LIGHT_RISE_SIGNAL_ENTITY = _ambient_rise_signal_entity(
    MANUAL_DIRECT_LIGHT_ROOM_SLUG
)
AMBIENT_BRIGHT_THRESHOLD_LUX = 950
AMBIENT_DAYLIGHT_LUX = 1300
DEFAULT_LUX_JITTER = 1.0


def _room_by_slug() -> dict[str, object]:
    """Return dev rooms keyed by slug."""
    return {room.slug: room for room in DEV_ROOMS}


def _second_power_entity(room: object) -> str:
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
        _second_power_entity(room),
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
    rooms = _room_by_slug()
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


@dataclass(frozen=True, slots=True)
class TraceState:
    """Relevant HA state for trace output."""

    state: str | None
    states_attribute: str | None = None


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """One state transition observed during simulation."""

    elapsed: float
    wall_time: str
    entity_id: str
    old: TraceState | None
    new: TraceState | None


@dataclass(frozen=True, slots=True)
class ExpectedState:
    """Expected state for one entity at a scenario checkpoint."""

    entity_id: str
    state: str | None = None
    states_contains: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CheckpointResult:
    """Evaluation result for one expected state."""

    checkpoint: str
    entity_id: str
    expected: ExpectedState
    actual: TraceState | None
    passed: bool
    detail: str


@dataclass(slots=True)
class ScenarioEvaluation:
    """Collect and report runtime-vs-expected scenario checks."""

    output_path: Path | None
    results: list[CheckpointResult] = field(default_factory=list)

    async def evaluate(
        self,
        client: HomeAssistantWs,
        *,
        checkpoint: str,
        expectations: Iterable[ExpectedState],
    ) -> None:
        """Evaluate one checkpoint against live HA state."""
        expected = tuple(expectations)
        states = await get_states(client, [item.entity_id for item in expected])
        for item in expected:
            actual = states.get(item.entity_id)
            passed, detail = _expected_state_matches(item, actual)
            result = CheckpointResult(
                checkpoint=checkpoint,
                entity_id=item.entity_id,
                expected=item,
                actual=actual,
                passed=passed,
                detail=detail,
            )
            self.results.append(result)
            status = "PASS" if passed else "FAIL"
            actual_state = actual.state if actual else "<missing>"
            print(
                f"[check:{status}] {checkpoint}: {item.entity_id} "
                f"actual={actual_state} {detail}",
                flush=True,
            )

    def write(self) -> None:
        """Write JSON evaluation output and raise on failures."""
        if self.output_path is not None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [asdict(result) for result in self.results]
            self.output_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            print(f"evaluation written: {self.output_path}", flush=True)
        failures = [result for result in self.results if not result.passed]
        if failures:
            summary = "; ".join(
                f"{result.checkpoint}:{result.entity_id} {result.detail}"
                for result in failures[:5]
            )
            raise RuntimeError(f"scenario expectation failures: {summary}")


def _expected_state_matches(
    expected: ExpectedState, actual: TraceState | None
) -> tuple[bool, str]:
    """Return whether an actual state satisfies an expectation."""
    if actual is None:
        return False, "entity missing"
    if expected.state is not None and actual.state != expected.state:
        return False, f"expected state={expected.state}"
    if expected.states_contains:
        state_tokens = {
            token.strip()
            for token in (actual.states_attribute or "").split(",")
            if token.strip()
        }
        missing = [
            token for token in expected.states_contains if token not in state_tokens
        ]
        if missing:
            return False, f"missing area states={missing}"
    return True, ""


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


async def get_states(
    client: HomeAssistantWs,
    entity_ids: Iterable[str],
) -> dict[str, TraceState | None]:
    """Return selected HA states keyed by entity id."""
    wanted = set(entity_ids)
    raw_states = await client.call("get_states")
    state_records = raw_states if isinstance(raw_states, list) else []
    states = {
        item["entity_id"]: TraceState(
            state=str(item.get("state")),
            states_attribute=_format_states_attribute(item.get("attributes", {})),
        )
        for item in state_records
        if isinstance(item, Mapping)
        and isinstance(item.get("entity_id"), str)
        and item["entity_id"] in wanted
    }
    return {entity_id: states.get(entity_id) for entity_id in wanted}


def _format_states_attribute(attributes: object) -> str | None:
    """Return a compact area-state attribute string when present."""
    if not isinstance(attributes, Mapping):
        return None
    states = attributes.get("states") or attributes.get("active_states")
    if isinstance(states, list):
        return ",".join(str(state) for state in states)
    if isinstance(states, str):
        return states
    return None


async def call_service(
    client: HomeAssistantWs,
    domain: str,
    service: str,
    *,
    entity_id: str | list[str],
    service_data: Mapping[str, object] | None = None,
) -> None:
    """Call a HA service."""
    payload: dict[str, object] = {
        "domain": domain,
        "service": service,
        "target": {"entity_id": entity_id},
    }
    if service_data:
        payload["service_data"] = dict(service_data)
    await client.call("call_service", **payload)


async def set_input_number(
    client: HomeAssistantWs,
    entity_id: str,
    value: float,
) -> None:
    """Set an input_number value."""
    await call_service(
        client,
        "input_number",
        "set_value",
        entity_id=entity_id,
        service_data={"value": round(value, 3)},
    )


async def set_input_boolean(
    client: HomeAssistantWs,
    entity_id: str | list[str],
    enabled: bool,
) -> None:
    """Set an input_boolean state."""
    await call_service(
        client,
        "input_boolean",
        "turn_on" if enabled else "turn_off",
        entity_id=entity_id,
    )


async def set_input_select(
    client: HomeAssistantWs,
    entity_id: str,
    option: str,
) -> None:
    """Set an input_select option."""
    await call_service(
        client,
        "input_select",
        "select_option",
        entity_id=entity_id,
        service_data={"option": option},
    )


async def set_switch(
    client: HomeAssistantWs,
    entity_id: str | list[str],
    enabled: bool,
) -> None:
    """Set a switch state."""
    await call_service(
        client,
        "switch",
        "turn_on" if enabled else "turn_off",
        entity_id=entity_id,
    )


async def set_light(
    client: HomeAssistantWs,
    entity_id: str | list[str],
    enabled: bool,
) -> None:
    """Set a light state through HA's light services."""
    await call_service(
        client,
        "light",
        "turn_on" if enabled else "turn_off",
        entity_id=entity_id,
    )


async def wait_for_state(
    client: HomeAssistantWs,
    entity_id: str,
    expected_state: str,
    *,
    timeout_seconds: float,
    poll_seconds: float = 1.0,
) -> None:
    """Wait until one entity reaches an expected state."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        state = (await get_states(client, [entity_id])).get(entity_id)
        if state is not None and state.state == expected_state:
            return
        await asyncio.sleep(poll_seconds)
    state = (await get_states(client, [entity_id])).get(entity_id)
    actual = state.state if state is not None else "<missing>"
    msg = f"{entity_id} did not reach {expected_state}; actual={actual}"
    raise RuntimeError(msg)


async def wait_for_states(
    client: HomeAssistantWs,
    expectations: Iterable[ExpectedState],
    *,
    timeout_seconds: float,
    poll_seconds: float = 1.0,
) -> None:
    """Wait until all expected states are true at the same poll point."""
    expected = tuple(expectations)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        states = await get_states(client, [item.entity_id for item in expected])
        failures = [
            item
            for item in expected
            if not _expected_state_matches(item, states.get(item.entity_id))[0]
        ]
        if not failures:
            return
        await asyncio.sleep(poll_seconds)

    states = await get_states(client, [item.entity_id for item in expected])
    details = []
    for item in expected:
        actual = states.get(item.entity_id)
        passed, detail = _expected_state_matches(item, actual)
        if not passed:
            actual_state = actual.state if actual is not None else "<missing>"
            details.append(f"{item.entity_id} actual={actual_state} {detail}")
    raise RuntimeError("Timed out waiting for states: " + "; ".join(details[:5]))


async def wait_for_service_call_event(
    args: argparse.Namespace,
    *,
    domain: str,
    service: str,
    trigger: Callable[[], object],
    expected_lights: Iterable[str] = (),
    expected_manual_control: bool | None = None,
    timeout_seconds: float = 10.0,
) -> Mapping[str, object]:
    """Run a trigger and wait for a matching HA call_service event."""
    async with HomeAssistantWs(args.url, DEV_HA_LONG_LIVED_TOKEN) as listener:
        await listener.call("subscribe_events", event_type="call_service")
        wait_task = asyncio.create_task(
            _wait_for_matching_service_call_event(
                listener,
                domain=domain,
                service=service,
                expected_lights=tuple(expected_lights),
                expected_manual_control=expected_manual_control,
                timeout_seconds=timeout_seconds,
            )
        )
        try:
            result = trigger()
            if asyncio.iscoroutine(result):
                await result
            return await wait_task
        finally:
            if not wait_task.done():
                wait_task.cancel()
                with suppress(asyncio.CancelledError):
                    await wait_task


async def _wait_for_matching_service_call_event(
    listener: HomeAssistantWs,
    *,
    domain: str,
    service: str,
    expected_lights: tuple[str, ...],
    expected_manual_control: bool | None,
    timeout_seconds: float,
) -> Mapping[str, object]:
    """Wait for one matching call_service event on an existing listener."""
    if listener._ws is None:
        raise RuntimeError("websocket is not connected")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        timeout = max(0.1, deadline - time.monotonic())
        raw = json.loads(await asyncio.wait_for(listener._ws.recv(), timeout=timeout))
        if raw.get("type") != "event":
            continue
        event = raw.get("event")
        if not isinstance(event, Mapping):
            continue
        data = event.get("data")
        if not isinstance(data, Mapping):
            continue
        if data.get("domain") != domain or data.get("service") != service:
            continue
        service_data = data.get("service_data")
        if not isinstance(service_data, Mapping):
            continue
        if expected_manual_control is not None and (
            service_data.get("manual_control") is not expected_manual_control
        ):
            continue
        if expected_lights:
            raw_lights = service_data.get("lights", [])
            lights = set(raw_lights if isinstance(raw_lights, list) else [])
            if not set(expected_lights).issubset(lights):
                continue
        return service_data

    msg = f"Timed out waiting for {domain}.{service} call_service event"
    raise RuntimeError(msg)


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
        ],
        False,
    )
    await set_input_number(client, "input_number.living_room_lux", 350)
    await set_input_number(client, "input_number.bathroom_lux", 120)
    await set_input_number(client, "input_number.outdoor_lux", 12000)


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


def _control_matrix_rooms() -> tuple[object, ...]:
    """Return rooms that participate in strict control-matrix assertions."""
    rooms = _room_by_slug()
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
        expectations.extend(
            [
                ExpectedState(
                    f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                    state="on",
                    states_contains=("occupied", "bright"),
                ),
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
        expectations.extend(
            [
                ExpectedState(
                    f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
                    state="on",
                    states_contains=("occupied", "bright"),
                ),
                ExpectedState(f"light.{slug}_overhead", state=expected_overhead),
            ]
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
    """Return expected state when recent MA output contaminates first rise evidence."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied", "bright"),
        ),
        ExpectedState(_ambient_rise_signal_entity(slug), state="on"),
        ExpectedState(f"light.{slug}_overhead", state="on"),
    ]


def _manual_direct_light_contamination_expectations(
    room: object,
) -> list[ExpectedState]:
    """Return expected state after manual room light output makes the sensor bright."""
    slug = str(getattr(room, "slug"))
    return [
        ExpectedState(
            f"binary_sensor.magic_areas_presence_tracking_{slug}_area_state",
            state="on",
            states_contains=("occupied", "bright"),
        ),
        ExpectedState(f"light.{slug}_overhead", state="on"),
        ExpectedState(_ambient_rise_signal_entity(slug), state="on"),
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
        ExpectedState(_ambient_rise_signal_entity(slug), state="on"),
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
                _second_power_entity(room),
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

    await reset_control_matrix(client)
    await wait_for_states(
        client,
        _clear_expectations(rooms),
        timeout_seconds=(args.cycle_seconds * 2) + args.checkpoint_settle_seconds,
    )
    if args.enable_controls:
        await set_switch(client, _control_switches(rooms), True)
    await asyncio.sleep(args.setup_settle_seconds)

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
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
            _second_power_entity(manual_direct_room),
            True,
        )
        await set_input_number(
            client,
            f"input_number.{MANUAL_DIRECT_LIGHT_ROOM_SLUG}_lux",
            AMBIENT_BRIGHT_THRESHOLD_LUX,
        )
    if ambient_rooms:
        await asyncio.sleep(args.checkpoint_settle_seconds)
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
                    seconds=args.checkpoint_settle_seconds,
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
    await asyncio.sleep(args.checkpoint_settle_seconds)
    await evaluation.evaluate(
        client,
        checkpoint="accent active",
        expectations=_accent_expectations(rooms),
    )

    print("event: control matrix sleep active", flush=True)
    await set_input_boolean(
        client, [f"input_boolean.{getattr(room, 'slug')}_sleep" for room in rooms], True
    )
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep((args.cycle_seconds * 2) + args.checkpoint_settle_seconds)
    await evaluation.evaluate(
        client,
        checkpoint="clear settled",
        expectations=_clear_expectations(rooms),
    )
    evaluation.write()


async def manual_override(client: HomeAssistantWs, args: argparse.Namespace) -> None:
    """Run a live manual-override and clear/reclaim scenario."""
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
    await asyncio.sleep(args.setup_settle_seconds)

    print("event: manual override occupied while dark", flush=True)
    await set_input_boolean(client, "input_boolean.living_room_occupancy", True)
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep(args.checkpoint_settle_seconds)
    await set_input_number(client, "input_number.living_room_lux", 350)
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep((args.cycle_seconds * 2) + args.checkpoint_settle_seconds)
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
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
        timeout_seconds=(args.cycle_seconds * 2) + args.checkpoint_settle_seconds,
    )
    await asyncio.sleep(args.setup_settle_seconds)

    print("event: presence hold on with occupancy input off", flush=True)
    await set_switch(client, presence_hold_switch, True)
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep((args.cycle_seconds * 2) + args.checkpoint_settle_seconds)
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
    await asyncio.sleep(args.setup_settle_seconds)

    print("event: adaptive lighting manual release occupied while dark", flush=True)
    await set_input_boolean(client, f"input_boolean.{slug}_occupancy", True)
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep(args.checkpoint_settle_seconds)

    print("event: manual off then clear should release AL manual control", flush=True)
    await set_light(client, overhead, False)
    await asyncio.sleep(args.checkpoint_settle_seconds)

    async def clear_room() -> None:
        await set_input_boolean(client, f"input_boolean.{slug}_occupancy", False)
        await asyncio.sleep((args.cycle_seconds * 2) + args.checkpoint_settle_seconds)

    service_data = await wait_for_service_call_event(
        args,
        domain="adaptive_lighting",
        service="set_manual_control",
        trigger=clear_room,
        expected_lights=(overhead,),
        expected_manual_control=False,
        timeout_seconds=(args.cycle_seconds * 2) + args.checkpoint_settle_seconds + 10,
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
    evaluation_path = None if args.no_evaluation_file else Path(args.evaluation_file)
    evaluation = ScenarioEvaluation(output_path=evaluation_path)
    binary_room = _room_by_slug()["adaptive_binary_room"]
    lux_room = _room_by_slug()["adaptive_lux_room"]
    rooms = (binary_room, lux_room)

    await reset_control_matrix(client)
    await set_input_number(client, "input_number.outdoor_lux", 100)
    await asyncio.gather(
        *(
            wait_for_state(
                client,
                f"binary_sensor.magic_areas_presence_tracking_{getattr(room, 'slug')}_area_state",
                "off",
                timeout_seconds=(args.cycle_seconds * 2) + args.checkpoint_settle_seconds,
            )
            for room in rooms
        )
    )
    if args.enable_controls:
        await set_switch(client, _control_switches(rooms), True)
    await asyncio.sleep(args.setup_settle_seconds)

    print("event: adaptive negative context occupied while dark", flush=True)
    await set_input_boolean(
        client,
        [f"input_boolean.{getattr(room, 'slug')}_occupancy" for room in rooms],
        True,
    )
    await asyncio.sleep(args.checkpoint_settle_seconds)
    await evaluation.evaluate(
        client,
        checkpoint="adaptive negative occupied dark",
        expectations=_dark_occupied_expectations(rooms),
    )

    print("event: adaptive negative outside not bright / lux below minimum", flush=True)
    for room in rooms:
        await set_input_number(client, f"input_number.{getattr(room, 'slug')}_lux", 1300)
    await asyncio.sleep(args.checkpoint_settle_seconds)
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
    await asyncio.sleep(args.checkpoint_settle_seconds)
    await set_input_number(client, "input_number.outdoor_lux", 1400)
    await set_input_number(client, "input_number.adaptive_lux_room_lux", 1300)
    await asyncio.sleep(args.checkpoint_settle_seconds)
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


def trace_entities(args: argparse.Namespace) -> tuple[str, ...]:
    """Return entity ids to trace for a scenario."""
    entity_ids: list[str] = []
    if args.scenario == "living-room-demo":
        entity_ids.extend(LIVING_ROOM_TRACE_ENTITIES)
    if args.scenario == "control-matrix":
        entity_ids.extend(control_matrix_trace_entities())
    if args.scenario == "adaptive-negative-context":
        entity_ids.extend(control_matrix_trace_entities())
    if args.scenario == "manual-override":
        entity_ids.extend(LIVING_ROOM_TRACE_ENTITIES)
    if args.scenario == "presence-hold":
        entity_ids.extend(LIVING_ROOM_TRACE_ENTITIES)
    if args.scenario == "adaptive-lighting-manual-release":
        entity_ids.extend(control_matrix_trace_entities())
    if args.include_bathroom:
        entity_ids.extend(BATHROOM_TRACE_ENTITIES)
    entity_ids.extend(args.trace_entity)
    return tuple(dict.fromkeys(entity_ids))


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
            elif args.scenario == "adaptive-negative-context":
                await adaptive_negative_context(client, args)
            elif args.scenario == "manual-override":
                await manual_override(client, args)
            elif args.scenario == "presence-hold":
                await presence_hold(client, args)
            elif args.scenario == "adaptive-lighting-manual-release":
                await adaptive_lighting_manual_release(client, args)
            else:  # pragma: no cover - argparse choices guard this path.
                raise RuntimeError(f"Unknown scenario: {args.scenario}")
        finally:
            recorder.stop()
            await trace_task
        if output_path is not None:
            print(f"trace written: {output_path}", flush=True)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="HA websocket URL")
    parser.add_argument(
        "--wait",
        type=int,
        default=120,
        help="Seconds to wait for HA websocket readiness",
    )
    parser.add_argument(
        "--scenario",
        choices=(
            "living-room-demo",
            "control-matrix",
            "adaptive-negative-context",
            "manual-override",
            "presence-hold",
            "adaptive-lighting-manual-release",
        ),
        default="living-room-demo",
        help="Simulation scenario to run",
    )
    parser.add_argument(
        "--cycle-seconds",
        type=float,
        default=DEFAULT_CYCLE_SECONDS,
        help="Base cycle length. Default: 30 seconds.",
    )
    parser.add_argument(
        "--ramp-seconds",
        type=float,
        default=DEFAULT_RAMP_SECONDS,
        help="Ramp duration. Default: 10 seconds.",
    )
    parser.add_argument(
        "--sample-seconds",
        type=float,
        default=DEFAULT_SAMPLE_SECONDS,
        help="Trace polling interval. Default: 0.5 seconds.",
    )
    parser.add_argument(
        "--setup-settle-seconds",
        type=float,
        default=DEFAULT_SETUP_SETTLE_SECONDS,
        help="Seconds to let reset/control setup settle before the first boundary.",
    )
    parser.add_argument(
        "--final-cycles",
        type=float,
        default=DEFAULT_STATE_PERIOD_CYCLES,
        help="Cycles to keep tracing after the final event.",
    )
    parser.add_argument(
        "--state-period-cycles",
        type=float,
        default=DEFAULT_STATE_PERIOD_CYCLES,
        help=(
            "Cycle count to represent seeded one-minute MA state timing "
            "(extended_time/extended_timeout). Default: 2 cycles."
        ),
    )
    parser.add_argument(
        "--enable-controls",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable MA light control switches before running.",
    )
    parser.add_argument(
        "--include-bathroom",
        action="store_true",
        help="Include bathroom entities in the trace.",
    )
    parser.add_argument(
        "--trace-entity",
        action="append",
        default=[],
        help="Additional entity_id to trace; may be passed multiple times.",
    )
    parser.add_argument(
        "--checkpoint-settle-seconds",
        type=float,
        default=5.0,
        help="Seconds to wait before evaluating each live checkpoint.",
    )
    parser.add_argument(
        "--evaluation-file",
        default="dev/ha/runtime/traces/latest-evaluation.json",
        help="JSON evaluation output path.",
    )
    parser.add_argument(
        "--no-evaluation-file",
        action="store_true",
        help="Do not write JSON evaluation output.",
    )
    parser.add_argument(
        "--trace-file",
        default=DEFAULT_TRACE_PATH,
        help="JSONL trace output path.",
    )
    parser.add_argument(
        "--no-trace-file",
        action="store_true",
        help="Only print trace output; do not write JSONL.",
    )
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    try:
        asyncio.run(simulate(parse_args()))
    except KeyboardInterrupt:
        return 130
    except Exception as err:  # noqa: BLE001 - CLI should print actionable failures.
        print(f"simulation failed: {err}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
