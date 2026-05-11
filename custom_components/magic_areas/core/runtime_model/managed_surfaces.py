"""Pure desired managed-surface contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


type ManagedSurfaceOptionValue = (
    str | int | float | bool | None | list[str] | dict[str, int]
)

MANAGED_SURFACE_UNIQUE_ID_PREFIX = "magic_areas:"


class ManagedSurfaceKind(StrEnum):
    """Kinds of Home Assistant surfaces managed by Magic Areas."""

    CONFIG_ENTRY_HELPER = "config_entry_helper"
    SIGNAL_HELPER = "signal_helper"


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


@dataclass(frozen=True, slots=True)
class LabelSurface:
    """Desired state for one HA label assignment surface."""

    name: str
    entity_ids: tuple[str, ...]
    prune_entity_ids: tuple[str, ...] = ()
    icon: str | None = None
    color: str | None = None
    description: str | None = None


type ManagedSurface = ConfigEntryHelperSurface | LabelSurface


def build_managed_surface_owner_prefix(entry_id: str) -> str:
    """Build the unique-ID prefix for surfaces owned by one Magic Areas entry."""
    return f"{MANAGED_SURFACE_UNIQUE_ID_PREFIX}{entry_id}:"


def is_managed_surface_unique_id(
    unique_id: str | None,
    *,
    owner_entry_id: str | None = None,
) -> bool:
    """Return whether a unique ID belongs to a Magic Areas-managed surface."""
    if unique_id is None:
        return False
    if owner_entry_id is not None:
        return unique_id.startswith(build_managed_surface_owner_prefix(owner_entry_id))
    return unique_id.startswith(MANAGED_SURFACE_UNIQUE_ID_PREFIX)


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
    "LabelSurface",
    "MANAGED_SURFACE_UNIQUE_ID_PREFIX",
    "ManagedSurface",
    "ManagedSurfaceKind",
    "ManagedSurfaceOptionValue",
    "build_managed_surface_owner_prefix",
    "build_managed_surface_unique_id",
    "is_managed_surface_unique_id",
]
