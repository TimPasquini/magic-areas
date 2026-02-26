"""Aggregate spec models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SensorAggregateSpec:
    """Aggregate spec for a sensor device class."""

    device_class: str
    entity_ids: list[str]
    unit_of_measurement: str


@dataclass(slots=True)
class BinarySensorAggregateSpec:
    """Aggregate spec for a binary sensor device class."""

    device_class: str
    entity_ids: list[str]
