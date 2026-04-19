"""Pure meta-area helpers for Magic Areas."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.area_state import (
    AreaStates,
    AreaType,
    MetaAreaType,
)
from custom_components.magic_areas.config_keys.area import CONF_TYPE
from custom_components.magic_areas.core.runtime_model import AreaDescriptor

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.components import MagicAreasRuntimeData


def collect_child_areas(
    hass: HomeAssistant,
    area_id: str,
    slug: str,
    floor_id: str | None,
) -> list[str]:
    """Return child area ids for a meta area by inspecting loaded config entries.

    Iterates all loaded magic_areas config entries, reads their coordinator snapshots,
    and delegates to resolve_child_areas() to apply meta-area matching rules.

    Args:
        hass: Home Assistant instance.
        area_id: ID of the meta area (e.g. "global", "interior", floor ID).
        slug: Slugified name of the meta area.
        floor_id: Floor ID if this is a floor meta area, otherwise None.

    Returns:
        List of child area ids that belong to this meta area.

    """
    entries = hass.config_entries.async_entries("magic_areas")
    descriptors: list[AreaDescriptor] = []

    for entry in entries:
        if entry.state != ConfigEntryState.LOADED:
            continue
        runtime_data: MagicAreasRuntimeData = entry.runtime_data
        coordinator_data = runtime_data.coordinator.data
        if coordinator_data is None:
            continue
        area_config = coordinator_data.area_config
        area_type = area_config.config.get(CONF_TYPE, area_config.id)
        descriptors.append(
            AreaDescriptor(
                id=area_config.id,
                slug=area_config.slug,
                floor_id=area_config.floor_id,
                area_type=str(area_type),
                is_meta=area_type == AreaType.META,
            )
        )

    meta_descriptor = AreaDescriptor(
        id=area_id,
        slug=slug,
        floor_id=floor_id,
        area_type=str(area_id),
        is_meta=True,
    )
    return resolve_child_areas(meta_descriptor, descriptors)


def resolve_child_areas(
    meta_area: AreaDescriptor, areas: Iterable[AreaDescriptor]
) -> list[str]:
    """Return child area ids for a meta area."""
    child_areas: list[str] = []

    for area in areas:
        if area.is_meta:
            continue

        if meta_area.floor_id:
            if meta_area.floor_id == area.floor_id:
                child_areas.append(area.id)
            continue

        if (
            meta_area.area_type == MetaAreaType.GLOBAL
            or area.area_type == meta_area.area_type
        ):
            child_areas.append(area.id)

    return child_areas


def resolve_active_areas(
    child_area_ids: Iterable[str], area_state_map: dict[str, str]
) -> list[str]:
    """Return child area ids that are currently active based on a state map."""
    active_areas: list[str] = []

    for area_id in child_area_ids:
        if area_state_map.get(area_id) == STATE_ON:
            active_areas.append(area_id)

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
