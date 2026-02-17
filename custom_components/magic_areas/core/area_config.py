"""Immutable area configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.models import MagicAreasConfigEntry

from custom_components.magic_areas.area_state import (
    AreaType,
    META_AREA_GLOBAL
)
from custom_components.magic_areas.components import (
    MAGIC_AREAS_COMPONENTS,
    MAGIC_AREAS_COMPONENTS_GLOBAL,
    MAGIC_AREAS_COMPONENTS_META,
)


@dataclass(frozen=True, slots=True)
class AreaConfig:
    """Immutable configuration for a Magic Area.

    This dataclass represents the static configuration of an area that
    should never change after initialization. It's frozen to prevent
    accidental mutations.
    """

    # Area identity (required)
    id: str
    name: str
    slug: str
    area_type: str
    config: dict[str, Any]
    hass_config: MagicAreasConfigEntry

    # Optional fields
    icon: str | None = None
    floor_id: str | None = None

    def __hash__(self) -> int:
        """Return hash of config (for use as dict key)."""
        # Note: dict and list items aren't hashable, but this is enough for identity
        return hash((self.id, self.area_type))

    def is_meta(self) -> bool:
        """Return if area is a meta area."""
        return self.area_type == AreaType.META

    def is_interior(self) -> bool:
        """Return if area type is interior."""
        return self.area_type == AreaType.INTERIOR

    def is_exterior(self) -> bool:
        """Return if area type is exterior."""
        return self.area_type == AreaType.EXTERIOR

    def available_platforms(self) -> list[str]:
        """Return available platforms for this area type."""
        if not self.is_meta():
            return MAGIC_AREAS_COMPONENTS
        if self.id == META_AREA_GLOBAL.lower():
            return MAGIC_AREAS_COMPONENTS_GLOBAL
        return MAGIC_AREAS_COMPONENTS_META
