"""Executor for applying control-group decisions via Home Assistant services."""

from __future__ import annotations

from collections.abc import Callable
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.control_group import (
    ControlActionType,
    ControlGroupDecision,
    ControlRuntimeEffect,
)


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
