"""Runtime expectation evaluation for live fake-house scenarios."""
# ruff: noqa: T201

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from scripts.ha_dev_bootstrap import HomeAssistantWs
from scripts.ha_dev_simulation.client import get_states
from scripts.ha_dev_simulation.models import (
    CheckpointResult,
    ExpectedState,
    TraceState,
)


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
