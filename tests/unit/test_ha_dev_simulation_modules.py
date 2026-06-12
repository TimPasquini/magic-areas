"""Characterization tests for the modular HA dev simulator."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

# Simulator imports expose websocket-backed types, but these tests never connect.
sys.modules.setdefault("websockets", ModuleType("websockets"))

from scripts import ha_dev_simulate
from scripts.ha_dev_bootstrap import (
    DEV_AREAS,
    DEV_MAGIC_AREAS,
    INITIAL_SERVICE_CALLS,
    DevRoom,
    _cover_room_magic_area,
    _fan_room_magic_area,
    _room_dev_area,
    _room_magic_area,
)
from scripts.ha_dev_simulation.client import get_states
from scripts.ha_dev_simulation import cli
from scripts.ha_dev_simulation.entities import (
    DEFAULT_CYCLE_SECONDS,
    FAN_ROOM_EXPECTED_OPTIONS,
)
from scripts.ha_dev_simulation.expectations import _expected_state_matches
from scripts.ha_dev_simulation.models import ExpectedState, TraceState
from scripts.ha_dev_simulation.preflight import preflight_fan_cover_options
from scripts.ha_dev_simulation.reset import reset_fake_house
from scripts.ha_dev_simulation.timing import SimulationTiming
from scripts.ha_dev_simulation.traces import trace_entities
from scripts.ha_dev_simulation.scenarios import lights


class RecordingClient:
    """Minimal websocket client that records simulator calls."""

    def __init__(self, responses: dict[str, object] | None = None) -> None:
        """Initialize recorded calls and command responses."""
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.responses = responses or {}

    async def call(self, command: str, **payload: object) -> object:
        """Record one command and return its configured response."""
        self.calls.append((command, payload))
        return self.responses.get(command)


def test_parse_args_preserves_defaults_and_repeatable_trace_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The compatibility parser retains defaults and repeatable CLI options."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "ha_dev_simulate",
            "--scenario",
            "control-matrix",
            "--trace-entity",
            "sensor.one",
            "--trace-entity",
            "sensor.two",
            "--no-trace-file",
            "--no-evaluation-file",
        ],
    )

    args = ha_dev_simulate.parse_args()

    assert args.scenario == "control-matrix"
    assert args.cycle_seconds == DEFAULT_CYCLE_SECONDS
    assert args.trace_entity == ["sensor.one", "sensor.two"]
    assert args.no_trace_file is True
    assert args.no_evaluation_file is True


def test_trace_entities_selects_scenario_defaults_and_deduplicates() -> None:
    """Trace selection includes scenario entities and removes duplicates."""
    args = SimpleNamespace(
        scenario="fan-cover-matrix",
        include_bathroom=False,
        trace_entity=[
            "fan.fan_room_exhaust",
            "sensor.custom",
            "sensor.custom",
        ],
    )

    entities = trace_entities(argparse.Namespace(**vars(args)))

    assert "fan.fan_room_exhaust" in entities
    assert "sensor.custom" in entities
    assert entities.count("sensor.custom") == 1


@pytest.mark.asyncio
async def test_get_states_preserves_state_and_area_state_attributes() -> None:
    """State reads retain the compact area-state attribute contract."""
    client = RecordingClient(
        {
            "get_states": [
                {
                    "entity_id": "binary_sensor.room",
                    "state": "on",
                    "attributes": {"states": ["occupied", "bright"]},
                }
            ]
        }
    )

    states = await get_states(client, ["binary_sensor.room", "sensor.missing"])  # type: ignore[arg-type]

    assert states["binary_sensor.room"] == TraceState(
        state="on",
        states_attribute="occupied,bright",
    )
    assert states["sensor.missing"] is None


def test_expected_state_matching_checks_state_and_area_tokens() -> None:
    """Evaluation matching preserves state and area-state assertions."""
    expected = ExpectedState(
        "binary_sensor.room",
        state="on",
        states_contains=("occupied", "bright"),
    )

    assert _expected_state_matches(
        expected,
        TraceState("on", "occupied,bright"),
    ) == (True, "")
    assert _expected_state_matches(
        expected,
        TraceState("on", "occupied,dark"),
    ) == (False, "missing area states=['bright']")


def test_simulation_timing_preserves_real_cycle_calculations() -> None:
    """Minute waits remain two real 30-second cycles with seeded defaults."""
    timing = SimulationTiming(
        cycle_seconds=30.0,
        state_period_cycles=2.0,
        setup_settle_seconds=2.0,
        checkpoint_settle_seconds=5.0,
    )

    assert timing.seeded_minute_seconds == 60.0
    assert timing.configured_minutes_seconds(1.5) == 90.0
    assert timing.configured_minutes_timeout(1.0) == 65.0
    assert timing.configured_seconds_timeout(4.0) == 9.0
    assert timing.runtime_poll_seconds == 0.5


def test_dev_room_properties_drive_area_and_magic_area_plans() -> None:
    """Room-derived entity IDs should remain aligned across bootstrap plans."""
    room = DevRoom(
        name="Test Room",
        slug="test_room",
        dark_entity="binary_sensor.outdoor_bright",
        second_light_slug="sleep_light",
        include_accent=False,
    )

    assert room.occupancy_entity == "binary_sensor.test_room_occupancy"
    assert room.sleep_entity == "binary_sensor.test_room_sleep"
    assert room.accent_entity == ""
    assert room.light_entity == "binary_sensor.test_room_light"
    assert room.illuminance_entity == "sensor.test_room_illuminance"
    assert room.overhead_light == "light.test_room_overhead"
    assert room.second_light == "light.test_room_sleep_light"
    assert room.resolved_dark_entity == "binary_sensor.outdoor_bright"

    area = _room_dev_area(room)
    assert area.entity_ids == (
        room.occupancy_entity,
        room.sleep_entity,
        room.light_entity,
        room.illuminance_entity,
        room.overhead_light,
        room.second_light,
    )

    magic_area = _room_magic_area(room)
    secondary_step = next(
        step for step in magic_area.options_steps if step.step_id == "secondary_states"
    )
    assert secondary_step.user_input["dark_entity"] == room.resolved_dark_entity
    assert secondary_step.user_input["accent_entity"] == ""


def test_bootstrap_builders_feed_exported_fake_house_contracts() -> None:
    """Special rooms and reset calls should be present in exported bootstrap data."""
    assert _fan_room_magic_area() in DEV_MAGIC_AREAS
    assert _cover_room_magic_area() in DEV_MAGIC_AREAS
    assert any(area.name == "Fan Room" for area in DEV_AREAS)
    assert any(area.name == "Cover Room" for area in DEV_AREAS)
    assert INITIAL_SERVICE_CALLS[0]["domain"] == "input_boolean"
    target_entity_ids = {
        target["entity_id"]
        for call in INITIAL_SERVICE_CALLS
        if isinstance((target := call.get("target")), dict)
        and isinstance(target.get("entity_id"), str)
    }
    assert "input_number.fan_room_humidity" in target_entity_ids


@pytest.mark.asyncio
async def test_adaptive_lighting_manual_release_executes_clear_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service-event waiter should execute the real clear-room trigger."""
    actions: list[tuple[str, object]] = []

    class _Timing:
        async def settle_setup(self) -> None:
            return None

        async def settle_checkpoint(self) -> None:
            return None

        async def wait_configured_minutes(self, minutes: float) -> None:
            actions.append(("wait_minutes", minutes))

        def configured_minutes_event_timeout(
            self, minutes: float, *, event_margin_seconds: float
        ) -> float:
            return minutes + event_margin_seconds

    class _Evaluation:
        def __init__(self, *, output_path: Path | None) -> None:
            del output_path

        async def evaluate(self, *_args: object, **_kwargs: object) -> None:
            return None

        def write(self) -> None:
            return None

    async def record_boolean(
        _client: object, entity_id: str, enabled: bool
    ) -> None:
        actions.append((entity_id, enabled))

    async def wait_for_event(
        _args: argparse.Namespace,
        **kwargs: object,
    ) -> dict[str, object]:
        trigger = kwargs["trigger"]
        assert callable(trigger)
        await trigger()
        return {"lights": ["light.adaptive_lighting_room_overhead"]}

    async def no_op(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        "scripts.ha_dev_simulation.scenarios.lights.SimulationTiming.from_args",
        lambda _args: _Timing(),
    )
    monkeypatch.setattr(lights, "ScenarioEvaluation", _Evaluation)
    monkeypatch.setattr(lights, "reset_control_matrix", no_op)
    monkeypatch.setattr(lights, "set_switch", no_op)
    monkeypatch.setattr(lights, "set_input_boolean", record_boolean)
    monkeypatch.setattr(lights, "call_service", no_op)
    monkeypatch.setattr(lights, "set_light", no_op)
    monkeypatch.setattr(lights, "wait_for_service_call_event", wait_for_event)

    args = argparse.Namespace(
        no_evaluation_file=True,
        evaluation_file="unused.json",
    )
    await lights.adaptive_lighting_manual_release(RecordingClient(), args)  # type: ignore[arg-type]

    assert (
        "input_boolean.adaptive_lighting_room_occupancy",
        False,
    ) in actions
    assert ("wait_minutes", 1) in actions


def test_preflight_accepts_matching_seeded_options(tmp_path: Path) -> None:
    """Preflight accepts the seeded Fan Room and Cover Room contracts."""
    from scripts.ha_dev_simulation.entities import COVER_ROOM_EXPECTED_OPTIONS

    storage = tmp_path / "core.config_entries"
    storage.write_text(
        json.dumps(
            {
                "data": {
                    "entries": [
                        {
                            "domain": "magic_areas",
                            "title": "Fan Room",
                            "options": FAN_ROOM_EXPECTED_OPTIONS,
                        },
                        {
                            "domain": "magic_areas",
                            "title": "Cover Room",
                            "options": COVER_ROOM_EXPECTED_OPTIONS,
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    preflight_fan_cover_options(storage)


@pytest.mark.asyncio
async def test_reset_fake_house_includes_setup_room() -> None:
    """Resetting the fake house intentionally restores Setup Room controls."""
    client = RecordingClient()

    await reset_fake_house(client)  # type: ignore[arg-type]

    service_payloads = [
        payload
        for command, payload in client.calls
        if command == "call_service"
    ]
    boolean_targets: list[str] = []
    for payload in service_payloads:
        target = payload.get("target")
        if not isinstance(target, dict):
            continue
        entity_ids = target.get("entity_id")
        if isinstance(entity_ids, list):
            boolean_targets.extend(str(entity_id) for entity_id in entity_ids)
    assert "input_boolean.setup_room_occupancy" in boolean_targets
    assert "input_boolean.setup_room_fan_power" in boolean_targets


def test_main_returns_error_and_prints_actionable_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The compatibility entrypoint preserves nonzero actionable failures."""

    async def fail(_args: argparse.Namespace) -> None:
        raise RuntimeError("expected failure")

    monkeypatch.setattr(cli, "simulate", fail)
    monkeypatch.setattr("sys.argv", ["ha_dev_simulate"])

    assert ha_dev_simulate.main() == 1
    assert "simulation failed: expected failure" in capsys.readouterr().err
