"""Shared control-group abstractions for policy-driven automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class ControlActionType(StrEnum):
    """Action types a control group can request."""

    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    NOOP = "noop"


class ControlRuntimeEffectType(StrEnum):
    """Runtime effect types attached to policy decisions."""

    SET_STATE = "set_state"


@dataclass(frozen=True, slots=True)
class ControlAction:
    """Single service action to apply."""

    domain: str
    service: str
    target_entity_ids: tuple[str, ...]
    service_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlGroupDecision:
    """Policy decision result for a control group."""

    action_type: ControlActionType
    actions: tuple[ControlAction, ...] = ()
    reason: str = ""
    runtime_effects: tuple[ControlRuntimeEffect, ...] = ()


@dataclass(frozen=True, slots=True)
class ControlRuntimeEffect:
    """Runtime-side effect applied outside policy evaluation."""

    effect_type: ControlRuntimeEffectType
    namespace: str
    key: str
    value: Any


@dataclass(frozen=True, slots=True)
class ControlGroupDefinition:
    """Declarative control-group definition."""

    group_id: str
    members: tuple[str, ...]
    trigger_states: tuple[str, ...] = ()
    policy_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlGroupContext:
    """Runtime context passed into control-group policies."""

    group_id: str
    current_states: tuple[str, ...]
    new_states: tuple[str, ...] = ()
    lost_states: tuple[str, ...] = ()
    signals: Any = field(default_factory=dict)
    is_enabled: bool = True


class ControlGroupPolicy(Protocol):
    """Policy protocol for control-group decision engines."""

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Return the next decision for the given context."""


def build_noop_decision(reason: str) -> ControlGroupDecision:
    """Create a standard NOOP decision."""
    return ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        actions=(),
        reason=reason,
    )
