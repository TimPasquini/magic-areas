"""Event handling helpers for Magic Areas light groups."""

from __future__ import annotations

from enum import Enum
from typing import Any

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import entity_registry as entity_registry_module
from homeassistant.helpers.event import EventStateChangedData

from custom_components.magic_areas.area_state import AreaStates
from custom_components.magic_areas.const import DOMAIN
from custom_components.magic_areas.enums import LightGroupCategory
from custom_components.magic_areas.core.light_control import (
    LightAction,
    LightGroupPolicyInput,
    reset_control_state,
    update_primary_control_state,
    update_secondary_control_state,
)


def area_state_changed(
    group: Any,
    area_id: str,
    states_tuple: tuple[list[str], list[str], list[str]],
) -> bool:
    """Handle area state change event for a light group."""
    if area_id != group._area_id:
        group.logger.debug(
            "%s: Area state change event not for us. Skipping. (req: %s/self: %s)",
            group.name,
            area_id,
            group._area_id,
        )
        return False

    automatic_control = group.is_control_enabled()

    if not automatic_control:
        group.logger.debug(
            "%s: Automatic control for light group is disabled, skipping...",
            group.name,
        )
        return False

    group.logger.debug("%s: Light group detected area state change", group.name)

    _new_states, _lost_states, current_states = states_tuple
    group._last_known_area_states = list(current_states)

    if group.category == LightGroupCategory.ALL:
        return state_change_primary(group, states_tuple)

    return state_change_secondary(group, states_tuple)


def state_change_primary(
    group: Any, states_tuple: tuple[list[str], list[str], list[str]]
) -> bool:
    """Handle primary state change."""
    new_states, lost_states, current_states = states_tuple
    context = LightGroupPolicyInput(
        new_states=new_states,
        lost_states=lost_states,
        current_states=current_states,
        control_state=group._control_state,
        is_primary=True,
    )
    decision = group.policy.evaluate_area_state_change(context)
    group.logger.debug("%s: Decision: %s", group.name, decision.reason)
    return _apply_decision(group, decision)


def state_change_secondary(
    group: Any, states_tuple: tuple[list[str], list[str], list[str]]
) -> bool:
    """Handle secondary state change."""
    new_states, lost_states, current_states = states_tuple
    context = LightGroupPolicyInput(
        new_states=new_states,
        lost_states=lost_states,
        current_states=current_states,
        control_state=group._control_state,
        is_primary=False,
    )
    decision = group.policy.evaluate_area_state_change(context)
    group.logger.debug("%s: Decision: %s", group.name, decision.reason)
    return _apply_decision(group, decision)


def is_child_controllable(hass: HomeAssistant, entity_id: str) -> bool:
    """Check if child entity is controllable."""
    entity_object = hass.states.get(entity_id)
    if not entity_object:
        return False
    if "controlling" in entity_object.attributes:
        return entity_object.attributes["controlling"]
    return False


def handle_group_state_change_primary(group: Any) -> None:
    """Handle group state change for primary area state events."""
    controlling = False

    if not group._child_ids:
        return

    for entity_id in group._child_ids:
        if is_child_controllable(group.hass, entity_id):
            controlling = True
            break
    group._set_control_state(
        update_primary_control_state(group._control_state, controlling)
    )
    group.schedule_update_ha_state()


def handle_group_state_change_secondary(group: Any) -> None:
    """Handle group state change for secondary area state events."""
    if group._control_state.controlled:
        group.logger.debug("%s: Group controlled by us.", group.name)
    else:
        group.logger.debug("%s: Group controlled by something else.", group.name)
    group._set_control_state(update_secondary_control_state(group._control_state))


def group_state_changed(group: Any, event: Event[EventStateChangedData]) -> bool:
    """Handle group state change events."""
    if not event.context:
        return False

    current_area_states = group._last_known_area_states

    if not current_area_states or AreaStates.OCCUPIED.value not in current_area_states:
        entity_registry = entity_registry_module.async_get(group.hass)
        presence_entity_id = entity_registry.async_get_entity_id(
            "binary_sensor",
            DOMAIN,
            f"presence_tracking_{group._area_id}_area_state",
        )
        if presence_entity_id:
            state = group.hass.states.get(presence_entity_id)
            if state and "states" in state.attributes:
                current_area_states = [
                    str(s.value) if isinstance(s, Enum) else str(s)
                    for s in state.attributes["states"]
                ]

    if AreaStates.OCCUPIED.value not in current_area_states:
        group._set_control_state(reset_control_state())
        group.logger.debug("%s: Control Reset.", group.name)
    else:
        origin_event = event.context.origin_event

        if group.category == LightGroupCategory.ALL:
            handle_group_state_change_primary(group)
        else:
            if origin_event and origin_event.event_type == "state_changed":
                if (
                    "old_state" not in origin_event.data
                    or not origin_event.data["old_state"]
                    or not origin_event.data["old_state"].state
                    or origin_event.data["old_state"].state not in [STATE_ON, STATE_OFF]
                ):
                    return False
                if (
                    "new_state" not in origin_event.data
                    or not origin_event.data["new_state"]
                    or not origin_event.data["new_state"].state
                    or origin_event.data["new_state"].state not in [STATE_ON, STATE_OFF]
                ):
                    return False

                if (
                    "restored" in origin_event.data["old_state"].attributes
                    and origin_event.data["old_state"].attributes["restored"]
                ):
                    return False

            handle_group_state_change_secondary(group)

    group._attr_extra_state_attributes["controlling"] = group.controlling
    group.schedule_update_ha_state()

    return True


def _apply_decision(group: Any, decision: Any) -> bool:
    if decision.next_control_state is not None:
        group._set_control_state(decision.next_control_state)

    if decision.action == LightAction.TURN_ON:
        return group._turn_on()
    if decision.action == LightAction.TURN_OFF:
        return group._turn_off()
    return False
