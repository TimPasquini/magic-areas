"""Pure meta-area helpers for Magic Areas."""

from __future__ import annotations

from typing import Iterable

from homeassistant.const import STATE_ON

from custom_components.magic_areas.enums import MetaAreaType
from custom_components.magic_areas.ha_domains import BINARY_SENSOR_DOMAIN
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


def build_meta_presence_sensors(child_slugs: Iterable[str]) -> list[str]:
    """Return presence tracker entity ids for meta areas."""
    return [
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{slug}_area_state"
        for slug in child_slugs
    ]


def resolve_active_areas(
    child_slugs: Iterable[str], area_state_map: dict[str, str]
) -> list[str]:
    """Return slugs that are currently active based on a state map."""
    active_areas: list[str] = []

    for slug in child_slugs:
        if area_state_map.get(slug) == STATE_ON:
            active_areas.append(slug)

    return active_areas
