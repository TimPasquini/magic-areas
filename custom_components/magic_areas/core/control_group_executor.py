"""Executor for applying control-group decisions via Home Assistant services."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.core.control_group import (
    ControlActionType,
    ControlGroupDecision,
)


async def execute_control_group_decision(
    hass: HomeAssistant,
    decision: ControlGroupDecision,
    *,
    blocking: bool = False,
) -> None:
    """Execute all service actions in a control-group decision."""
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
