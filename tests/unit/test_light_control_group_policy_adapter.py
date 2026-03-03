"""Tests for canonical light control-group policy adapter."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.command_echo import CommandEchoState
from custom_components.magic_areas.core.control_group import (
    ControlActionType,
    ControlGroupContext,
)
from custom_components.magic_areas.light_groups.policy import (
    ActOnMode,
    build_light_control_group_policy,
)


def test_light_policy_adapter_primary_clear_turns_off() -> None:
    """Primary CLEAR transition should produce a deactivation decision."""
    policy = build_light_control_group_policy(
        assigned_states=[],
        act_on_modes=[],
        light_group_entity_id="light.magic_areas_light_groups_kitchen_all_lights",
    )

    decision = policy.evaluate(
        ControlGroupContext(
            group_id="light.magic_areas_light_groups_kitchen_all_lights",
            new_states=(AreaStates.CLEAR,),
            lost_states=(AreaStates.OCCUPIED,),
            current_states=(AreaStates.CLEAR,),
            signals={
                "is_primary": True,
                "control_state": CommandEchoState(controlling=True, awaiting_echo=False),
            },
        )
    )
    next_state = policy.next_control_state(
        ControlGroupContext(
            group_id="light.magic_areas_light_groups_kitchen_all_lights",
            new_states=(AreaStates.CLEAR,),
            lost_states=(AreaStates.OCCUPIED,),
            current_states=(AreaStates.CLEAR,),
            signals={
                "is_primary": True,
                "control_state": CommandEchoState(controlling=True, awaiting_echo=False),
            },
        )
    )

    assert decision.action_type == ControlActionType.DEACTIVATE
    assert next_state is not None
    assert next_state.controlling is True
    assert next_state.controlled is False


def test_light_policy_adapter_secondary_occupied_dark_turns_on() -> None:
    """Secondary occupied+dark transition should activate assigned light group."""
    policy = build_light_control_group_policy(
        assigned_states=[AreaStates.DARK],
        act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
        light_group_entity_id="light.magic_areas_light_groups_kitchen_overhead_lights",
    )

    context = ControlGroupContext(
        group_id="light.magic_areas_light_groups_kitchen_overhead_lights",
        new_states=(AreaStates.OCCUPIED, AreaStates.DARK),
        lost_states=(),
        current_states=(AreaStates.OCCUPIED, AreaStates.DARK),
        signals={
            "is_primary": False,
            "control_state": CommandEchoState(controlling=True, awaiting_echo=False),
        },
    )
    decision = policy.evaluate(context)
    next_state = policy.next_control_state(context)

    assert decision.action_type == ControlActionType.ACTIVATE
    assert next_state is not None
    assert next_state.controlled is True


def test_light_policy_adapter_defaults_when_control_state_signal_missing() -> None:
    """Adapter should handle missing control_state signal deterministically."""
    policy = build_light_control_group_policy(
        assigned_states=[AreaStates.DARK],
        act_on_modes=[ActOnMode.STATE_CHANGE],
        light_group_entity_id="light.magic_areas_light_groups_kitchen_overhead_lights",
    )

    context = ControlGroupContext(
        group_id="light.magic_areas_light_groups_kitchen_overhead_lights",
        new_states=(AreaStates.BRIGHT,),
        lost_states=(),
        current_states=(AreaStates.OCCUPIED, AreaStates.BRIGHT),
        signals={"is_primary": False},
    )

    decision = policy.evaluate(context)
    next_state = policy.next_control_state(context)

    assert decision.action_type == ControlActionType.DEACTIVATE
    assert next_state is not None
    assert next_state.controlling is True
    assert next_state.controlled is True
