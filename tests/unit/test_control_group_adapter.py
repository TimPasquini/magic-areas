"""Tests for shared control-group policy adapter helpers."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

import pytest

from custom_components.magic_areas.core.controls import (
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    evaluate_and_execute_control_group_policy,
    evaluate_and_execute_control_group_policy_sync,
)


@dataclass(slots=True)
class _TestPolicy:
    """Simple test policy that always returns the configured decision."""

    decision: ControlGroupDecision

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        del context
        return self.decision


class _DummyAwaitable:
    """Minimal awaitable for sync adapter guardrail checks."""

    def __await__(self) -> Generator[None]:
        yield
        return None


@pytest.mark.asyncio
async def test_async_adapter_evaluates_and_executes() -> None:
    """Async adapter should evaluate policy and execute resulting decision."""
    decision = ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        reason="test_noop",
    )
    policy = _TestPolicy(decision=decision)
    executed: list[ControlGroupDecision] = []

    async def _execute(d: ControlGroupDecision) -> bool:
        executed.append(d)
        return True

    result = await evaluate_and_execute_control_group_policy(
        policy=policy,
        context=ControlGroupContext(group_id="test_group", current_states=()),
        execute_decision=_execute,
    )

    assert result is decision
    assert executed == [decision]


def test_sync_adapter_evaluates_and_executes() -> None:
    """Sync adapter should evaluate policy and return execution result."""
    decision = ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        reason="test_noop",
    )
    policy = _TestPolicy(decision=decision)

    returned_decision, executed = evaluate_and_execute_control_group_policy_sync(
        policy=policy,
        context=ControlGroupContext(group_id="test_group", current_states=()),
        execute_decision=lambda _: True,
    )

    assert returned_decision is decision
    assert executed is True


def test_sync_adapter_rejects_awaitable_execution_results() -> None:
    """Sync adapter should reject awaitable executor outputs."""
    decision = ControlGroupDecision(
        action_type=ControlActionType.NOOP,
        reason="test_noop",
    )
    policy = _TestPolicy(decision=decision)

    with pytest.raises(TypeError, match="awaitable"):
        evaluate_and_execute_control_group_policy_sync(
            policy=policy,
            context=ControlGroupContext(group_id="test_group", current_states=()),
            execute_decision=lambda _: _DummyAwaitable(),
        )
