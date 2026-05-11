"""Managed signal-helper planning for light groups."""

from __future__ import annotations

from custom_components.magic_areas.core.runtime_model import SignalHelperSurface
from custom_components.magic_areas.core.runtime_model import trend_signal_surface
from custom_components.magic_areas.light_groups.config import (
    FeatureConfigDict,
    adaptive_require_ambient_rise,
    ambient_rise_min_delta,
    ambient_rise_window_seconds,
    brightness_mode,
    outside_lux_inside_entity,
    LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE,
)

AMBIENT_RISE_SIGNAL_ROLE = "ambient_rise"


def ambient_rise_signal_surface(
    *,
    entry_id: str,
    area_id: str,
    area_name: str,
    feature_config: FeatureConfigDict,
    device_identifier: tuple[str, str] | None = None,
    device_name: str | None = None,
) -> SignalHelperSurface | None:
    """Build the managed Trend helper used as ambient-rise signal evidence."""
    if brightness_mode(feature_config) != LIGHT_GROUP_BRIGHTNESS_MODE_ADAPTIVE:
        return None
    if not adaptive_require_ambient_rise(feature_config):
        return None

    source_entity_id = outside_lux_inside_entity(feature_config)
    if source_entity_id is None:
        return None

    window_seconds = ambient_rise_window_seconds(feature_config)
    min_delta = ambient_rise_min_delta(feature_config)
    if window_seconds <= 0 or min_delta <= 0:
        return None

    return trend_signal_surface(
        entry_id=entry_id,
        area_id=area_id,
        area_name=area_name,
        role=AMBIENT_RISE_SIGNAL_ROLE,
        source_entity_id=source_entity_id,
        min_gradient=min_delta / window_seconds,
        sample_duration=window_seconds,
        max_samples=10,
        min_samples=2,
        device_identifier=device_identifier,
        device_name=device_name,
    )


__all__ = [
    "AMBIENT_RISE_SIGNAL_ROLE",
    "ambient_rise_signal_surface",
]
