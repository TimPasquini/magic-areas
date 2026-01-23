"""Core area data structures for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AreaDescriptor:
    """Pure area descriptor for HA-free core logic."""

    id: str
    slug: str
    floor_id: str | None
    area_type: str
    is_meta: bool
