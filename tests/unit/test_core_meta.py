"""Tests for core meta-area helpers."""

from custom_components.magic_areas.core.area_model import AreaDescriptor
from custom_components.magic_areas.core.meta import (
    build_meta_presence_sensors,
    resolve_active_areas,
    resolve_child_areas,
)
from custom_components.magic_areas.enums import MetaAreaType
from homeassistant.const import STATE_OFF, STATE_ON


def test_resolve_child_areas_global() -> None:
    """Global meta areas include all non-meta areas."""
    meta_area = AreaDescriptor(
        id="meta-global",
        slug="global",
        floor_id=None,
        area_type=MetaAreaType.GLOBAL,
        is_meta=True,
    )
    areas = [
        AreaDescriptor(
            id="kitchen",
            slug="kitchen",
            floor_id="floor_1",
            area_type="interior",
            is_meta=False,
        ),
        AreaDescriptor(
            id="yard",
            slug="yard",
            floor_id=None,
            area_type="exterior",
            is_meta=False,
        ),
        AreaDescriptor(
            id="meta-interior",
            slug="interior",
            floor_id=None,
            area_type="interior",
            is_meta=True,
        ),
    ]

    assert resolve_child_areas(meta_area, areas) == ["kitchen", "yard"]


def test_resolve_child_areas_floor() -> None:
    """Floor meta areas include areas on the same floor only."""
    meta_area = AreaDescriptor(
        id="floor_1",
        slug="floor_1",
        floor_id="floor_1",
        area_type=MetaAreaType.FLOOR,
        is_meta=True,
    )
    areas = [
        AreaDescriptor(
            id="kitchen",
            slug="kitchen",
            floor_id="floor_1",
            area_type="interior",
            is_meta=False,
        ),
        AreaDescriptor(
            id="garage",
            slug="garage",
            floor_id="floor_2",
            area_type="interior",
            is_meta=False,
        ),
    ]

    assert resolve_child_areas(meta_area, areas) == ["kitchen"]


def test_build_meta_presence_sensors() -> None:
    """Meta presence sensors are derived from child slugs."""
    sensors = build_meta_presence_sensors(["kitchen", "yard"])
    assert sensors == [
        "binary_sensor.magic_areas_presence_tracking_kitchen_area_state",
        "binary_sensor.magic_areas_presence_tracking_yard_area_state",
    ]


def test_resolve_active_areas() -> None:
    """Active areas are derived from the state map."""
    state_map = {"kitchen": STATE_ON, "yard": STATE_OFF}
    assert resolve_active_areas(["kitchen", "yard"], state_map) == ["kitchen"]
