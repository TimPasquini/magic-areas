"""Light group control policy for Magic Areas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum, auto

from custom_components.magic_areas.core.state_priority import (
    filter_by_priority,
    LIGHT_PRIORITY_STATES,
)
from custom_components.magic_areas.enums import AreaStates


class LightAction(StrEnum):
    """Light group action to take."""

    TURN_ON = auto()
    TURN_OFF = auto()
    NOOP = auto()


class ActOnMode(StrEnum):
    """When light group should act."""

    OCCUPANCY_CHANGE = "occupancy"  # Act when occupancy changes
    STATE_CHANGE = "state"  # Act when secondary states change


@dataclass(slots=True)
class LightGroupDecision:
    """Light group control decision result."""

    action: LightAction
    reason: str  # For debugging/logging
    should_track_control: bool = False  # Whether to mark as "controlled by MA"


@dataclass(slots=True)
class LightGroupPolicy:
    """Policy for controlling a light group based on area states.

    Attributes:
        assigned_states: States this light group reacts to (e.g., ["sleep", "dark"] for sleep lights)
        act_on_modes: When to act (["occupancy", "state"] or subset)
        use_priority_filtering: Whether to filter by priority states

    """

    assigned_states: Sequence[str]
    act_on_modes: Sequence[str]
    use_priority_filtering: bool = True

    def evaluate(
        self,
        new_states: Sequence[str],
        lost_states: Sequence[str],
        current_states: Sequence[str],
    ) -> LightGroupDecision:
        """Evaluate whether light group should turn on, off, or do nothing.

        Args:
            new_states: States just added
            lost_states: States just lost
            current_states: All currently active states

        Returns:
            LightGroupDecision with action and reason

        Logic:
            1. CLEAR → noop (reset handled separately)
            2. BRIGHT (not assigned to it) → turn off if BRIGHT just added without OCCUPIED
            3. No changes → noop
            4. No assigned states → noop
            5. Not occupied → noop
            6. Filter to valid states (assigned & current)
            7. Apply priority filtering if enabled
            8. Check act-on modes (occupancy vs state change)
            9. If valid states remain → turn on
            10. Otherwise → turn off (with conditions)

        """
        current_state_set = set(current_states)

        # (1) CLEAR state → noop (reset is side effect, handled by caller)
        if AreaStates.CLEAR in new_states:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="area_clear",
            )

        # (2) BRIGHT state special logic
        if (
            AreaStates.BRIGHT in current_state_set
            and AreaStates.BRIGHT not in self.assigned_states
        ):
            # Only turn off if BRIGHT just added AND not occupancy change
            if (
                AreaStates.BRIGHT in new_states
                and AreaStates.OCCUPIED not in new_states
            ):
                return LightGroupDecision(
                    action=LightAction.TURN_OFF,
                    reason="bright_not_assigned",
                    should_track_control=True,
                )
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="bright_active_but_stable",
            )

        # (3) No changes → noop
        if not new_states and not lost_states:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="no_state_changes",
            )

        # (4) No assigned states → noop
        if not self.assigned_states:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="no_assigned_states",
            )

        # (5) Not occupied → noop
        if AreaStates.OCCUPIED not in current_state_set:
            return LightGroupDecision(
                action=LightAction.NOOP,
                reason="not_occupied",
            )

        # (6) Filter to valid states
        valid_states = [
            state for state in self.assigned_states if state in current_state_set
        ]

        # (7) Apply priority filtering
        if self.use_priority_filtering:
            valid_states = filter_by_priority(valid_states, LIGHT_PRIORITY_STATES)

        # (8) Check act-on modes
        if AreaStates.OCCUPIED in new_states:
            # Occupancy change
            if ActOnMode.OCCUPANCY_CHANGE not in self.act_on_modes:
                return LightGroupDecision(
                    action=LightAction.NOOP,
                    reason="occupancy_change_not_configured",
                )
        else:
            # State change (not occupancy)
            if ActOnMode.STATE_CHANGE not in self.act_on_modes:
                return LightGroupDecision(
                    action=LightAction.NOOP,
                    reason="state_change_not_configured",
                )

        # (9) Decision
        if valid_states:
            return LightGroupDecision(
                action=LightAction.TURN_ON,
                reason=f"valid_states_present ({', '.join(valid_states)})",
                should_track_control=True,
            )
        else:
            # Turn off if no valid states remain
            return LightGroupDecision(
                action=LightAction.TURN_OFF,
                reason="no_valid_states",
                should_track_control=False,  # Caller decides based on prior control state
            )


def resolve_light_category_config(
    category: str,
    feature_config: dict,
    light_group_states_map: dict,
    light_group_act_on_map: dict,
    default_act_on: Sequence[str],
) -> tuple[list[str], list[str]]:
    """Resolve assigned states and act-on modes for a light category.

    Args:
        category: Light category (overhead, sleep, accent, task)
        feature_config: Feature configuration dict
        light_group_states_map: Map from category to config key for states
        light_group_act_on_map: Map from category to config key for act-on modes
        default_act_on: Default act-on modes to use

    Returns:
        Tuple of (assigned_states, act_on_modes)

    """
    # No states/act-on if category not in maps
    if category not in light_group_states_map or category not in light_group_act_on_map:
        return [], list(default_act_on)

    # Get config keys for this category
    states_key = light_group_states_map[category]
    act_on_key = light_group_act_on_map[category]

    # Get values from feature config, with defaults
    assigned_states = feature_config.get(states_key, [])
    act_on = feature_config.get(act_on_key, default_act_on)

    return assigned_states, list(act_on)


def build_light_group_policy(
    assigned_states: Sequence[str],
    act_on_modes: Sequence[str],
) -> LightGroupPolicy:
    """Build light group policy from configuration.

    Args:
        assigned_states: States this light group reacts to
        act_on_modes: When to act (occupancy/state change)

    Returns:
        Configured LightGroupPolicy

    """
    return LightGroupPolicy(
        assigned_states=assigned_states,
        act_on_modes=act_on_modes,
        use_priority_filtering=True,
    )
