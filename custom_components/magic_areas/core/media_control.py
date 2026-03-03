"""Media control decision helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
)


@dataclass(slots=True)
class MediaControlPolicy(ControlGroupPolicy):
    """Canonical control-group policy adapter for media control."""

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Evaluate media control for a canonical control-group context."""
        media_player_group_id = _as_optional_str(
            context.signals.get("media_player_group_id")
        )
        return media_state_change_to_control_group(
            new_states=context.new_states,
            media_player_group_id=media_player_group_id,
        )


def build_media_control_group_policy() -> MediaControlPolicy:
    """Build canonical media control-group policy adapter."""
    return MediaControlPolicy()


def media_state_change_to_control_group(
    new_states: Sequence[str], media_player_group_id: str | None
) -> ControlGroupDecision:
    """Translate area-state changes into media-group control actions."""
    if AreaStates.CLEAR not in new_states:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason="no_clear_state",
        )

    if not media_player_group_id:
        return ControlGroupDecision(
            action_type=ControlActionType.NOOP,
            reason="media_group_unavailable",
        )

    return ControlGroupDecision(
        action_type=ControlActionType.DEACTIVATE,
        reason="area_clear_turn_off",
        actions=(
            ControlAction(
                domain=MEDIA_PLAYER_DOMAIN,
                service=SERVICE_TURN_OFF,
                target_entity_ids=(media_player_group_id,),
            ),
        ),
    )


def _as_optional_str(value: Any) -> str | None:
    """Normalize optional string signal values."""
    return value if isinstance(value, str) else None
