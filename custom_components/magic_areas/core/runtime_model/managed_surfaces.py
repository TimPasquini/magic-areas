"""Pure desired managed-surface contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


type ManagedSurfaceOptionValue = str | int | float | bool | None | list[str]


class ManagedSurfaceKind(StrEnum):
    """Kinds of Home Assistant surfaces managed by Magic Areas."""

    CONFIG_ENTRY_HELPER = "config_entry_helper"


@dataclass(frozen=True, slots=True)
class ConfigEntryHelperSurface:
    """Desired state for a config-entry-backed HA helper."""

    unique_id: str
    domain: str
    title: str
    options: dict[str, ManagedSurfaceOptionValue]
    area_id: str | None = None
    device_identifier: tuple[str, str] | None = None
    device_name: str | None = None
    device_class: str | None = None


type ManagedSurface = ConfigEntryHelperSurface


def build_managed_surface_unique_id(
    *,
    entry_id: str,
    area_id: str,
    feature_id: str,
    surface_kind: ManagedSurfaceKind,
    role: str,
) -> str:
    """Build stable ownership ID for a Magic Areas-managed HA surface."""
    return ":".join(
        str(part)
        for part in (
            "magic_areas",
            entry_id,
            area_id,
            feature_id,
            surface_kind,
            role,
        )
    )


__all__ = [
    "ConfigEntryHelperSurface",
    "ManagedSurface",
    "ManagedSurfaceKind",
    "ManagedSurfaceOptionValue",
    "build_managed_surface_unique_id",
]
