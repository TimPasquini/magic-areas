"""Passive data models used by live simulation tracing and evaluation."""

from __future__ import annotations

from dataclasses import dataclass


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
