"""Aggregate helpers for Magic Areas."""

from __future__ import annotations

from custom_components.magic_areas.core.aggregate_selection import (
    _is_valid_value,
    _min_entities,
    _normalize_allowed_device_classes,
    build_binary_sensor_aggregates,
    build_health_sensor_spec,
    build_sensor_aggregates,
)
from custom_components.magic_areas.core.aggregate_specs import (
    BinarySensorAggregateSpec,
    SensorAggregateSpec,
)

__all__ = [
    "BinarySensorAggregateSpec",
    "SensorAggregateSpec",
    "build_binary_sensor_aggregates",
    "build_health_sensor_spec",
    "build_sensor_aggregates",
    "_is_valid_value",
    "_min_entities",
    "_normalize_allowed_device_classes",
]
