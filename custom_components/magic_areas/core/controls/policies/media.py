"""Media control decision helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.core.controls.control_group import (
    ControlAction,
    ControlActionType,
    ControlGroupContext,
    ControlGroupDecision,
    ControlGroupPolicy,
)

__all__ = [
    "MediaControlPolicy",
    "MediaPolicySignals",
    "build_media_control_group_policy",
    "evaluate_area_routing",
    "has_valid_notification_states",
    "media_state_change_to_control_group",
    "should_skip_sleep_state",
]


@dataclass(slots=True)
class MediaControlPolicy(ControlGroupPolicy):
    """Canonical control-group policy adapter for media control."""

    def evaluate(self, context: ControlGroupContext) -> ControlGroupDecision:
        """Evaluate media control for a canonical control-group context."""
        signals = MediaPolicySignals.from_signals(context.signals)
        return media_state_change_to_control_group(
            new_states=context.new_states,
            media_player_group_id=signals.media_player_group_id,
        )


def build_media_control_group_policy() -> MediaControlPolicy:
    """Build canonical media control-group policy adapter."""
    return MediaControlPolicy()


@dataclass(frozen=True, slots=True)
class MediaPolicySignals:
    """Typed runtime inputs for media policy adapters."""

    media_player_group_id: str | None

    @classmethod
    def from_signals(cls, signals: object) -> MediaPolicySignals:
        """Parse typed media signals from control-group context."""
        if isinstance(signals, cls):
            return signals
        return cls(media_player_group_id=None)


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


def has_valid_notification_states(
    area_states: list[str], notification_states: list[str]
) -> bool:
    """Return True when area has at least one allowed notification state."""
    if not notification_states:
        return True

    return any(state in area_states for state in notification_states)


def should_skip_sleep_state(
    area_states: list[str], notification_states: list[str]
) -> bool:
    """Return True when area is sleeping and sleep is not allowed."""
    return (
        AreaStates.SLEEP in area_states and AreaStates.SLEEP not in notification_states
    )


def evaluate_area_routing(
    is_occupied: bool,
    area_states: list[str],
    notification_states: list[str],
) -> bool:
    """Return True when area-aware media should route into this area."""
    if not is_occupied:
        return False
    if should_skip_sleep_state(area_states, notification_states):
        return False
    return has_valid_notification_states(area_states, notification_states)
