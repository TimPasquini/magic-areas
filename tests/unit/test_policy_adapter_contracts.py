"""Cross-feature Layer 3 adapter contract tests."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls.policies.climate import (
    ClimatePolicySignals,
    build_climate_control_group_policy,
)
from custom_components.magic_areas.core.controls import (
    ControlGroupContext,
    ControlGroupDecision,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    FanPolicySignals,
    build_fan_control_group_policy,
)
from custom_components.magic_areas.core.controls.policies.media import (
    MediaPolicySignals,
    build_media_control_group_policy,
)
from custom_components.magic_areas.light_groups import (
    ActOnMode,
    LightPolicySignals,
    build_light_control_group_policy,
)


def test_fan_adapter_returns_canonical_decision() -> None:
    """Fan adapter evaluate path should return ControlGroupDecision."""
    policy = build_fan_control_group_policy({})
    decision = policy.evaluate(
        ControlGroupContext(
            group_id="fan_groups_test",
            current_states=(AreaStates.OCCUPIED,),
            signals=FanPolicySignals(
                sensor_value=100.0,
                fan_group_entity_id="fan.test",
                fan_group_state="off",
            ),
        )
    )

    assert isinstance(decision, ControlGroupDecision)


def test_climate_adapter_returns_canonical_decision() -> None:
    """Climate adapter evaluate path should return ControlGroupDecision."""
    policy = build_climate_control_group_policy({})
    decision = policy.evaluate(
        ControlGroupContext(
            group_id="climate_control_test",
            current_states=(AreaStates.OCCUPIED,),
            new_states=(AreaStates.OCCUPIED,),
            signals=ClimatePolicySignals(
                climate_entity_id="climate.test",
                preset_name=None,
            ),
        )
    )

    assert isinstance(decision, ControlGroupDecision)


def test_media_adapter_returns_canonical_decision() -> None:
    """Media adapter evaluate path should return ControlGroupDecision."""
    policy = build_media_control_group_policy()
    decision = policy.evaluate(
        ControlGroupContext(
            group_id="media_player_groups_test",
            new_states=(AreaStates.CLEAR,),
            current_states=(),
            signals=MediaPolicySignals(media_player_group_id="media_player.test"),
        )
    )

    assert isinstance(decision, ControlGroupDecision)


def test_light_adapter_returns_canonical_decision() -> None:
    """Light adapter evaluate path should return ControlGroupDecision."""
    policy = build_light_control_group_policy(
        assigned_states=[AreaStates.DARK],
        act_on_modes=[ActOnMode.OCCUPANCY_CHANGE, ActOnMode.STATE_CHANGE],
        light_group_entity_id="light.test",
    )
    decision = policy.evaluate(
        ControlGroupContext(
            group_id="light_groups_test",
            new_states=(AreaStates.OCCUPIED, AreaStates.DARK),
            current_states=(AreaStates.OCCUPIED, AreaStates.DARK),
            signals=LightPolicySignals.from_signals({}),
        )
    )

    assert isinstance(decision, ControlGroupDecision)
