"""Snapshot data models for coordinator-owned ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from custom_components.magic_areas.core.area_config import AreaConfig
from custom_components.magic_areas.core.area_runtime import AreaRuntime
from custom_components.magic_areas.core.entity_ids import EntityReferences


@dataclass(slots=True)
class MagicAreasData:
    """Snapshot of area data used by platforms."""

    entities: dict[str, list[dict[str, str]]]
    magic_entities: dict[str, list[dict[str, str]]]
    presence_sensors: list[str]
    active_areas: list[str]
    child_areas: list[str]
    config: dict[str, Any]
    enabled_features: set[str]
    feature_configs: dict[str, dict[str, Any]]
    entity_references: EntityReferences
    area_config: AreaConfig
    area_runtime: AreaRuntime
    updated_at: datetime
