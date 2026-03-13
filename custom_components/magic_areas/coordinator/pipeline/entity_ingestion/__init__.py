"""Entity loading package public API."""

from custom_components.magic_areas.coordinator.pipeline.entity_ingestion.registry_queries import (
    EntitySnapshot,
    build_entity_dict,
    filter_entity_list,
    group_entities,
    is_magic_area_entity,
    should_exclude_entity,
)
from custom_components.magic_areas.coordinator.pipeline.entity_ingestion.loader import (
    load_area_entities,
    load_meta_area_entities,
)

__all__ = [
    "EntitySnapshot",
    "build_entity_dict",
    "filter_entity_list",
    "group_entities",
    "is_magic_area_entity",
    "load_area_entities",
    "load_meta_area_entities",
    "should_exclude_entity",
]
