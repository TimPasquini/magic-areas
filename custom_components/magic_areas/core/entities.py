"""Pure entity transformation helpers for Magic Areas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from homeassistant.const import ATTR_ENTITY_ID


@dataclass(slots=True)
class EntitySnapshot:
    """Pure entity snapshot for grouping and normalization."""

    entity_id: str
    domain: str
    attributes: Mapping[str, Any] | None = None


def build_entity_dict(
    entity_id: str, attributes: Mapping[str, Any] | None
) -> dict[str, str]:
    """Return entity_id with stringified attributes (excluding entity_id)."""
    entity_dict = {ATTR_ENTITY_ID: entity_id}

    if attributes:
        for attr_key, attr_value in attributes.items():
            if attr_key == ATTR_ENTITY_ID:
                continue
            entity_dict[str(attr_key)] = str(attr_value)

    return entity_dict


def group_entities(entities: list[EntitySnapshot]) -> dict[str, list[dict[str, str]]]:
    """Group entity snapshots by domain with normalized attributes."""
    grouped: dict[str, list[dict[str, str]]] = {}

    for entity in entities:
        grouped.setdefault(entity.domain, []).append(
            build_entity_dict(entity.entity_id, entity.attributes)
        )

    return grouped
