"""Light-group identity helpers."""

from __future__ import annotations

from custom_components.magic_areas.core.runtime_model import (
    ManagedSurfaceKind,
    build_managed_surface_unique_id,
)
from custom_components.magic_areas.enums import MagicAreasFeatures

LIGHT_GROUP_ROLE_LABELS: dict[str, str] = {
    "overhead_lights": "ma:overhead",
    "task_lights": "ma:task",
    "sleep_lights": "ma:sleep",
    "accent_lights": "ma:accent",
}


def build_light_group_helper_surface_unique_id(
    *,
    entry_id: str,
    area_id: str,
    category: str,
) -> str:
    """Return the managed helper unique ID for one light role group."""
    return build_managed_surface_unique_id(
        entry_id=entry_id,
        area_id=area_id,
        feature_id=MagicAreasFeatures.LIGHT_GROUPS,
        surface_kind=ManagedSurfaceKind.CONFIG_ENTRY_HELPER,
        role=f"light_group_{category}",
    )


__all__ = ["LIGHT_GROUP_ROLE_LABELS", "build_light_group_helper_surface_unique_id"]
