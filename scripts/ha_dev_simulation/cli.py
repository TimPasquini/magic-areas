"""Drive the Magic Areas HA dev fake-house through timed simulation scenarios."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import asyncio
import sys

from scripts.ha_dev_bootstrap import (
    DEFAULT_URL,
)
from scripts.ha_dev_simulation_plan import (
    DEFAULT_SETUP_SETTLE_SECONDS,
)
from scripts.ha_dev_simulation.entities import (
    DEFAULT_CONFIG_ENTRIES_PATH,
    DEFAULT_CYCLE_SECONDS,
    DEFAULT_RAMP_SECONDS,
    DEFAULT_SAMPLE_SECONDS,
    DEFAULT_STATE_PERIOD_CYCLES,
    DEFAULT_TRACE_PATH,
)
from scripts.ha_dev_simulation.runner import simulate


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
            "disabled-light-controls",
            "adaptive-negative-context",
            "manual-override",
            "presence-hold",
            "adaptive-lighting-manual-release",
            "fan-cover-matrix",
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
        "--config-entries-file",
        default=DEFAULT_CONFIG_ENTRIES_PATH,
        help=(
            "Local HA core.config_entries storage path used for scenario preflight. "
            f"Default: {DEFAULT_CONFIG_ENTRIES_PATH}."
        ),
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
