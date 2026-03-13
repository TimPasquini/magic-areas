"""Shared control-group abstractions for policy-driven automation."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from inspect import isawaitable
import logging
from typing import Protocol

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.runtime_model import ControlGroupPolicyId


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
    service_data: dict[str, object] = field(default_factory=dict)


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
    value: object


@dataclass(frozen=True, slots=True)
class ControlGroupDefinition:
    """Declarative control-group definition."""

    group_id: str
    members: tuple[str, ...]
    trigger_states: tuple[str, ...] = ()
    policy_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlGroupContext:
    """Runtime context passed into control-group policies."""

    group_id: str
    current_states: tuple[str, ...]
    new_states: tuple[str, ...] = ()
    lost_states: tuple[str, ...] = ()
    signals: object = field(default_factory=dict)
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


_CUSTOM_CONTROL_GROUP_TEMPLATES: list[dict[str, object]] = [
    {
        "group_id": "control.task",
        "members": [],
        "trigger_states": ["occupied"],
        "policy_id": str(ControlGroupPolicyId.CUSTOM_CONTROL_GROUP),
        "metadata": {"label": "Task"},
    },
    {
        "group_id": "control.reading",
        "members": [],
        "trigger_states": ["occupied"],
        "policy_id": str(ControlGroupPolicyId.CUSTOM_CONTROL_GROUP),
        "metadata": {"label": "Reading"},
    },
    {
        "group_id": "control.media",
        "members": [],
        "trigger_states": ["occupied"],
        "policy_id": str(ControlGroupPolicyId.CUSTOM_CONTROL_GROUP),
        "metadata": {"label": "Media"},
    },
]


def get_custom_control_group_templates() -> list[dict[str, object]]:
    """Return a deep-copied list of starter control-group templates."""
    return deepcopy(_CUSTOM_CONTROL_GROUP_TEMPLATES)


ControlDecisionExecutor = Callable[
    [ControlGroupDecision],
    bool | None | Awaitable[bool | None],
]


async def evaluate_and_execute_control_group_policy(
    *,
    policy: ControlGroupPolicy,
    context: ControlGroupContext,
    execute_decision: ControlDecisionExecutor,
    logger: logging.Logger | None = None,
    actor_name: str | None = None,
) -> ControlGroupDecision:
    """Evaluate a control-group policy and execute the returned decision."""
    decision = policy.evaluate(context)

    if logger:
        name = actor_name or "control_group"
        logger.debug("%s: Decision: %s", name, decision.reason)

    execution_result = execute_decision(decision)
    if isawaitable(execution_result):
        await execution_result

    return decision


def evaluate_and_execute_control_group_policy_sync(
    *,
    policy: ControlGroupPolicy,
    context: ControlGroupContext,
    execute_decision: ControlDecisionExecutor,
    logger: logging.Logger | None = None,
    actor_name: str | None = None,
) -> tuple[ControlGroupDecision, bool | None]:
    """Evaluate and execute a control-group decision synchronously."""
    decision = policy.evaluate(context)

    if logger:
        name = actor_name or "control_group"
        logger.debug("%s: Decision: %s", name, decision.reason)

    execution_result = execute_decision(decision)
    if isawaitable(execution_result):
        msg = "Synchronous adapter received awaitable execution result"
        raise TypeError(msg)

    return decision, execution_result


def execute_control_group_runtime_effects(
    decision: ControlGroupDecision,
    *,
    on_runtime_effect: Callable[[ControlRuntimeEffect], None] | None = None,
) -> None:
    """Apply runtime effects from a control-group decision."""
    if on_runtime_effect is None:
        return
    for effect in decision.runtime_effects:
        on_runtime_effect(effect)


async def execute_control_group_decision(
    hass: HomeAssistant,
    decision: ControlGroupDecision,
    *,
    blocking: bool = False,
    on_runtime_effect: Callable[[ControlRuntimeEffect], None] | None = None,
) -> None:
    """Execute runtime effects and service actions in a control-group decision."""
    execute_control_group_runtime_effects(
        decision,
        on_runtime_effect=on_runtime_effect,
    )

    if decision.action_type == ControlActionType.NOOP:
        return

    for action in decision.actions:
        target: str | list[str]
        if len(action.target_entity_ids) == 1:
            target = action.target_entity_ids[0]
        else:
            target = list(action.target_entity_ids)
        await hass.services.async_call(
            action.domain,
            action.service,
            {
                "entity_id": target,
                **action.service_data,
            },
            blocking=blocking,
        )
