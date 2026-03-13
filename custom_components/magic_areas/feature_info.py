"""Feature metadata contract (ids, translation keys, icons)."""

from __future__ import annotations

from dataclasses import dataclass, field

from custom_components.magic_areas.enums import MagicAreasFeatures


@dataclass(frozen=True)
class FeatureInfo:
    """Feature metadata for entities."""

    id: MagicAreasFeatures
    translation_keys: dict[str, str | None]
    icons: dict[str, str] = field(default_factory=dict)
