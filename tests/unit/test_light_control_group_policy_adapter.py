"""Tests for canonical light control-group policy adapter."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.light_groups import CommandEchoState
from custom_components.magic_areas.core.controls import (
    ControlActionType,
    ControlGroupContext,
    ControlRuntimeEffectType,
)
from custom_components.magic_areas.light_groups import (
    ActOnMode,
    LightPolicySignals,
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
            signals=LightPolicySignals(
                is_primary=True,
                control_state=CommandEchoState(controlling=True, awaiting_echo=False),
            ),
        )
    )
    assert decision.action_type == ControlActionType.DEACTIVATE
    assert len(decision.runtime_effects) == 1
    effect = decision.runtime_effects[0]
    assert effect.effect_type == ControlRuntimeEffectType.SET_STATE
    assert effect.namespace == "command_echo"
    assert effect.key == "state"
    assert isinstance(effect.value, CommandEchoState)
    assert effect.value.controlling is True
    assert effect.value.awaiting_echo is False


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
        signals=LightPolicySignals(
            is_primary=False,
            control_state=CommandEchoState(controlling=True, awaiting_echo=False),
        ),
    )
    decision = policy.evaluate(context)

    assert decision.action_type == ControlActionType.ACTIVATE
    assert len(decision.runtime_effects) == 1
    effect = decision.runtime_effects[0]
    assert isinstance(effect.value, CommandEchoState)
    assert effect.value.awaiting_echo is True


def test_light_policy_adapter_defaults_when_control_state_signal_missing() -> None:
    """Adapter should no-op when primary identity is missing from signals."""
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
        signals=LightPolicySignals.from_signals({}),
    )

    decision = policy.evaluate(context)
    assert decision.action_type == ControlActionType.NOOP
    assert decision.reason == "invalid_light_policy_signals"
    assert len(decision.runtime_effects) == 0


def test_light_policy_adapter_allows_fallback_when_primary_flag_present() -> None:
    """Adapter should still evaluate when is_primary is explicitly provided."""
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
    assert decision.action_type == ControlActionType.DEACTIVATE
    assert len(decision.runtime_effects) == 1
    effect = decision.runtime_effects[0]
    assert isinstance(effect.value, CommandEchoState)
    assert effect.value.controlling is True
    assert effect.value.awaiting_echo is True
