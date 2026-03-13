"""Tests for canonical control-group policy adapters."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls.policies.climate import (
    ClimatePolicySignals,
    build_climate_control_group_policy,
)
from custom_components.magic_areas.core.controls import (
    ControlActionType,
    ControlGroupContext,
)
from custom_components.magic_areas.core.controls.policies.fan import (
    FanPolicySignals,
    build_fan_control_group_policy,
)
from custom_components.magic_areas.core.controls.policies.media import (
    MediaPolicySignals,
    build_media_control_group_policy,
)
from custom_components.magic_areas.config_keys.area import (
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
    CONF_FAN_GROUPS_REQUIRED_STATE,
    CONF_FAN_GROUPS_SETPOINT,
)


def test_fan_policy_adapter_evaluates_from_canonical_context() -> None:
    """Fan adapter should evaluate context and emit control-group action."""
    policy = build_fan_control_group_policy(
        {
            CONF_FAN_GROUPS_SETPOINT: 25.0,
            CONF_FAN_GROUPS_REQUIRED_STATE: AreaStates.OCCUPIED,
        }
    )
    decision = policy.evaluate(
        ControlGroupContext(
            group_id="fan_groups_kitchen",
            current_states=(AreaStates.OCCUPIED,),
            signals=FanPolicySignals(
                sensor_value=30.0,
                fan_group_entity_id="fan.kitchen_group",
                fan_group_state="off",
            ),
        )
    )

    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].target_entity_ids == ("fan.kitchen_group",)


def test_climate_policy_adapter_evaluates_from_state_transition() -> None:
    """Climate adapter should select and apply configured preset."""
    policy = build_climate_control_group_policy(
        {
            CONF_CLIMATE_CONTROL_PRESET_SLEEP: "sleep_mode",
        }
    )
    decision = policy.evaluate(
        ControlGroupContext(
            group_id="climate_control_bedroom",
            new_states=(AreaStates.SLEEP,),
            current_states=(AreaStates.OCCUPIED, AreaStates.SLEEP),
            signals=ClimatePolicySignals(
                climate_entity_id="climate.bedroom",
                preset_name=None,
            ),
        )
    )

    assert decision.action_type == ControlActionType.ACTIVATE
    assert decision.actions[0].service_data["preset_mode"] == "sleep_mode"


def test_media_policy_adapter_evaluates_from_canonical_context() -> None:
    """Media adapter should turn off media group on CLEAR transitions."""
    policy = build_media_control_group_policy()
    decision = policy.evaluate(
        ControlGroupContext(
            group_id="media_player_groups_living_room",
            new_states=(AreaStates.CLEAR,),
            current_states=(),
            signals=MediaPolicySignals(
                media_player_group_id="media_player.living_room_group"
            ),
        )
    )

    assert decision.action_type == ControlActionType.DEACTIVATE
    assert decision.actions[0].target_entity_ids == (
        "media_player.living_room_group",
    )
