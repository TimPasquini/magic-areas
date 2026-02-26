"""Feature access helpers for Magic Areas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.magic_areas.enums import MagicAreasFeatures

if TYPE_CHECKING:  # pragma: no cover
    from custom_components.magic_areas.coordinator import MagicAreasCoordinator


def get_feature_config(
    coordinator: MagicAreasCoordinator, feature: MagicAreasFeatures | None
) -> dict[str, Any]:
    """Return feature config from the coordinator snapshot."""
    if not feature or not coordinator.data:
        return {}

    return coordinator.data.feature_configs.get(feature, {})
