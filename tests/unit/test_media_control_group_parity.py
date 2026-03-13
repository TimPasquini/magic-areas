"""Parity tests for media state changes -> control-group conversion."""

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls import ControlActionType
from custom_components.magic_areas.core.controls.policies.media import (
    media_state_change_to_control_group,
)


def test_clear_state_maps_to_media_turn_off() -> None:
    """CLEAR should map to media turn_off action."""
    decision = media_state_change_to_control_group(
        [AreaStates.CLEAR], "media_player.room_group"
    )

    assert decision.action_type == ControlActionType.DEACTIVATE
    assert decision.actions[0].service == "turn_off"


def test_non_clear_or_missing_group_is_noop() -> None:
    """Non-clear and missing-group paths should be NOOP."""
    non_clear = media_state_change_to_control_group(
        [AreaStates.OCCUPIED], "media_player.room_group"
    )
    missing_group = media_state_change_to_control_group([AreaStates.CLEAR], None)

    assert non_clear.action_type == ControlActionType.NOOP
    assert missing_group.action_type == ControlActionType.NOOP
