"""Unit tests for core.control_group_executor."""

from unittest.mock import AsyncMock

from custom_components.magic_areas.core.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupDecision,
)
from custom_components.magic_areas.core.control_group_executor import (
    execute_control_group_decision,
)


async def test_execute_noop_decision_skips_service_calls() -> None:
    """No-op decisions should not call HA services."""
    hass = AsyncMock()

    await execute_control_group_decision(
        hass,
        ControlGroupDecision(action_type=ControlActionType.NOOP, reason="noop"),
    )

    hass.services.async_call.assert_not_called()


async def test_execute_calls_all_actions() -> None:
    """Executor should call HA services for every action in order."""
    hass = AsyncMock()
    decision = ControlGroupDecision(
        action_type=ControlActionType.ACTIVATE,
        reason="activate",
        actions=(
            ControlAction(
                domain="fan",
                service="turn_on",
                target_entity_ids=("fan.one",),
            ),
            ControlAction(
                domain="climate",
                service="set_preset_mode",
                target_entity_ids=("climate.room",),
                service_data={"preset_mode": "sleep"},
            ),
        ),
    )

    await execute_control_group_decision(hass, decision, blocking=True)

    assert hass.services.async_call.call_count == 2
