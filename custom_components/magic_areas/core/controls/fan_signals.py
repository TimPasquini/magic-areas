"""Managed signal-helper planning for fan controller roles."""

from __future__ import annotations

from homeassistant.components.trend.const import DOMAIN as TREND_DOMAIN

from custom_components.magic_areas.core.controls.policies.fan import (
    FanControllerConfig,
    FanDetectionMode,
)
from custom_components.magic_areas.core.runtime_model import SignalHelperSurface
from custom_components.magic_areas.core.runtime_model import trend_signal_surface

FAN_CONTROLLER_TREND_SIGNAL_ROLE_PREFIX = "fan_controller"


def fan_controller_trend_signal_role(controller_id: str) -> str:
    """Return the managed Trend helper role for one fan controller."""
    return f"{FAN_CONTROLLER_TREND_SIGNAL_ROLE_PREFIX}_{controller_id}"


def fan_controller_trend_signal_surface(
    *,
    entry_id: str,
    area_id: str,
    area_name: str,
    controller: FanControllerConfig,
    device_identifier: tuple[str, str] | None = None,
    device_name: str | None = None,
) -> SignalHelperSurface | None:
    """Build the managed Trend helper used by threshold+trend fan controllers."""
    if controller.detection_mode is not FanDetectionMode.THRESHOLD_TREND:
        return None
    if controller.sensor_entity_id is None:
        return None

    return trend_signal_surface(
        entry_id=entry_id,
        area_id=area_id,
        area_name=area_name,
        role=fan_controller_trend_signal_role(controller.controller_id),
        source_entity_id=controller.sensor_entity_id,
        min_gradient=0.0,
        sample_duration=0,
        max_samples=4,
        min_samples=2,
        device_identifier=device_identifier,
        device_name=device_name,
    )


__all__ = [
    "FAN_CONTROLLER_TREND_SIGNAL_ROLE_PREFIX",
    "TREND_DOMAIN",
    "fan_controller_trend_signal_role",
    "fan_controller_trend_signal_surface",
]
