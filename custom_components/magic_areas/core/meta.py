"""Pure meta-area helpers for Magic Areas."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from homeassistant.const import STATE_ON

from custom_components.magic_areas.enums import AreaStates, MetaAreaType
from custom_components.magic_areas.core.area_model import AreaDescriptor


def resolve_child_areas(
    meta_area: AreaDescriptor, areas: Iterable[AreaDescriptor]
) -> list[str]:
    """Return child area slugs for a meta area."""
    child_areas: list[str] = []

    for area in areas:
        if area.is_meta:
            continue

        if meta_area.floor_id:
            if meta_area.floor_id == area.floor_id:
                child_areas.append(area.slug)
            continue

        if (
            meta_area.area_type == MetaAreaType.GLOBAL
            or area.area_type == meta_area.area_type
        ):
            child_areas.append(area.slug)

    return child_areas


def resolve_active_areas(
    child_slugs: Iterable[str], area_state_map: dict[str, str]
) -> list[str]:
    """Return slugs that are currently active based on a state map."""
    active_areas: list[str] = []

    for slug in child_slugs:
        if area_state_map.get(slug) == STATE_ON:
            active_areas.append(slug)

    return active_areas


def aggregate_secondary_states(
    child_state_lists: list[list[str]],
    mode: str,
    configurable_states: Sequence[str],
) -> list[str]:
    """Aggregate secondary states from child areas.

    Args:
        child_state_lists: List of state lists, one per child area.
        mode: Calculation mode ("any", "all", "majority").
        configurable_states: States to consider for aggregation.

    Returns:
        List of aggregated secondary states.

    """
    states: list[str] = []
    child_area_count = len(child_state_lists)

    if child_area_count == 0:
        if AreaStates.DARK not in states:
            states.append(AreaStates.BRIGHT)
        return states

    all_states: list[str] = []
    for state_list in child_state_lists:
        all_states.extend(state_list)
    state_counter = Counter(all_states)

    for secondary_state in configurable_states:
        if secondary_state not in state_counter:
            continue

        amt_states = state_counter[secondary_state]

        if mode == "any" and amt_states > 0:
            states.append(secondary_state)
        elif mode == "all" and amt_states == child_area_count:
            states.append(secondary_state)
        elif mode == "majority" and amt_states >= (child_area_count / 2):
            states.append(secondary_state)

    if AreaStates.DARK not in states:
        states.append(AreaStates.BRIGHT)

    return states
