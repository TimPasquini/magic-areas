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
